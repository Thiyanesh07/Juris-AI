"""Legal QA orchestration: hybrid GraphRAG pipeline, prompting, LLM, citation validation."""

from __future__ import annotations

import time
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.graph.client import Neo4jClient
from app.qa.citations import (
    CitationValidationError,
    LLMOutputParseError,
    build_public_citations,
    parse_llm_output,
    validate_llm_citations,
    validation_problem_message,
)
from app.qa.prompts import (
    build_correction_user_message,
    build_system_message,
    build_user_message,
    prepare_evidence_for_prompt,
)
from app.qa.provider import (
    LLMProvider,
    build_llm_provider,
)
from app.rag.pipeline import execute_graphrag_pipeline
from app.retrieval.hybrid import hybrid_retrieve
from app.schemas.hybrid import HybridEvidence
from app.schemas.qa import (
    QAAskResponse,
    QACitation,
    QAGraphData,
    QAGraphEdge,
    QAGraphNode,
    QAReasoningStep,
    QARetrievalMeta,
    QATimingsMs,
)


class QAInvalidModelOutputError(Exception):
    """Model output remained invalid after one retry."""


def effective_retrieval_top_k(settings: Settings, requested_top_k: int | None) -> int:
    base = requested_top_k or settings.retrieval_default_top_k
    return min(base, settings.qa_max_evidence)


def _ms_since(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _hybrid_results_to_evidence(results: list[dict[str, Any]]) -> list[HybridEvidence]:
    return [HybridEvidence.model_validate(item) for item in results]


async def _generate_validated_answer(
    provider: LLMProvider,
    settings: Settings,
    *,
    system_message: str,
    user_message: str,
    evidence_items: list[HybridEvidence],
) -> tuple[str, bool, list[QACitation]]:
    last_problem = "Model output failed validation"

    for attempt in range(2):
        message = user_message if attempt == 0 else build_correction_user_message(
            user_message, last_problem
        )
        raw = await provider.generate(
            system_message=system_message,
            user_message=message,
            timeout_seconds=settings.llm_timeout_seconds,
            max_output_tokens=settings.llm_max_output_tokens,
        )
        try:
            parsed = parse_llm_output(raw)
            validated = validate_llm_citations(
                parsed,
                evidence_count=len(evidence_items),
            )
            public = build_public_citations(validated, evidence_items)
            return parsed.answer, parsed.insufficient_evidence, public
        except (LLMOutputParseError, CitationValidationError) as exc:
            last_problem = validation_problem_message(exc)
            if attempt == 1:
                raise QAInvalidModelOutputError(last_problem) from exc

    raise QAInvalidModelOutputError(last_problem)


async def ask_legal_question(
    session: AsyncSession,
    graph_client: Neo4jClient,
    query: str,
    top_k: int | None,
    settings: Settings,
    *,
    mode: Literal["COMPREHENSIVE", "CONSTITUTIONAL", "STATUTORY", "CASE_LAW"] = "COMPREHENSIVE",
    retrieval_strategy: Literal["hybrid", "vector_only", "graph_only"] = "hybrid",
    graph_depth: int | None = None,
    provider: LLMProvider | None = None,
    embedder: Any | None = None,
) -> QAAskResponse:
    """Run hybrid GraphRAG pipeline and LLM grounding for one legal question."""
    is_patched = getattr(hybrid_retrieve, "__module__", "") != "app.retrieval.hybrid"

    if is_patched:
        effective_top_k = effective_retrieval_top_k(settings, top_k)
        retrieval_start = time.perf_counter()
        hybrid_res = await hybrid_retrieve(
            session, graph_client, query, effective_top_k, settings, embedder=embedder
        )
        retrieval_ms = _ms_since(retrieval_start)

        raw_results = hybrid_res.get("results") or []
        if not raw_results:
            return QAAskResponse(
                query=query.strip(),
                status="insufficient_evidence",
                answer=None,
                insufficient_evidence=True,
                citations=[],
                evidence=[],
                retrieval=QARetrievalMeta(
                    mode=retrieval_strategy,
                    fallback=hybrid_res.get("fallback"),
                    fallback_reason=hybrid_res.get("fallback_reason"),
                    warnings=list(hybrid_res.get("warnings") or []),
                    evidence_count=0,
                    evidence_dropped_for_context=0,
                ),
                provider=settings.llm_provider,
                model=settings.llm_model,
                llm_called=False,
                timings_ms=QATimingsMs(retrieval=retrieval_ms, llm=0),
            )

        all_evidence = _hybrid_results_to_evidence(raw_results)
        prepared, blocks, dropped = prepare_evidence_for_prompt(all_evidence, settings)
        if not prepared:
            return QAAskResponse(
                query=query.strip(),
                status="insufficient_evidence",
                answer=None,
                insufficient_evidence=True,
                citations=[],
                evidence=[],
                retrieval=QARetrievalMeta(
                    mode=retrieval_strategy,
                    fallback=hybrid_res.get("fallback"),
                    fallback_reason=hybrid_res.get("fallback_reason"),
                    warnings=list(hybrid_res.get("warnings") or []),
                    evidence_count=0,
                    evidence_dropped_for_context=dropped,
                ),
                provider=settings.llm_provider,
                model=settings.llm_model,
                llm_called=False,
                timings_ms=QATimingsMs(retrieval=retrieval_ms, llm=0),
            )

        llm = provider or build_llm_provider(settings)
        system_msg = build_system_message()
        user_msg = build_user_message(query.strip(), blocks)

        llm_start = time.perf_counter()
        ans, insufficient, cits = await _generate_validated_answer(
            llm, settings, system_message=system_msg, user_message=user_msg, evidence_items=prepared
        )
        llm_ms = _ms_since(llm_start)

        status_str = "insufficient_evidence" if insufficient else "answered"
        return QAAskResponse(
            query=query.strip(),
            status=status_str,
            answer=ans,
            insufficient_evidence=insufficient,
            citations=cits,
            evidence=prepared,
            retrieval=QARetrievalMeta(
                mode=retrieval_strategy,
                fallback=hybrid_res.get("fallback"),
                fallback_reason=hybrid_res.get("fallback_reason"),
                warnings=list(hybrid_res.get("warnings") or []),
                evidence_count=len(prepared),
                evidence_dropped_for_context=dropped,
            ),
            provider=settings.llm_provider,
            model=settings.llm_model,
            llm_called=True,
            timings_ms=QATimingsMs(retrieval=retrieval_ms, llm=llm_ms),
        )

    # Standard GraphRAG Pipeline Execution
    llm = provider or build_llm_provider(settings)
    res_dict = await execute_graphrag_pipeline(
        session=session,
        graph_client=graph_client,
        query=query,
        top_k=top_k,
        settings=settings,
        mode=mode,
        strategy=retrieval_strategy,
        graph_depth=graph_depth,
        provider=llm,
        embedder=embedder,
    )

    graph_dict = res_dict.get("graph") or {}
    graph_data = None
    if graph_dict:
        nodes = [QAGraphNode(**n) for n in graph_dict.get("nodes", [])]
        edges = [QAGraphEdge(**e) for e in graph_dict.get("edges", [])]
        graph_data = QAGraphData(
            nodes=nodes,
            edges=edges,
            available=graph_dict.get("available", False),
        )

    reasoning_steps = [QAReasoningStep(**s) for s in res_dict.get("reasoning_steps", [])]

    return QAAskResponse(
        query=query.strip(),
        status=res_dict["status"],
        answer=res_dict["answer"],
        insufficient_evidence=res_dict["insufficient_evidence"],
        citations=res_dict["citations"],
        evidence=res_dict["evidence"],
        graph=graph_data,
        reasoning_steps=reasoning_steps,
        query_analysis=res_dict.get("query_analysis"),
        retrieval=res_dict["retrieval"],
        provider=res_dict["provider"],
        model=res_dict["model"],
        llm_called=res_dict["llm_called"],
        timings_ms=res_dict["timings_ms"],
        disclaimer=res_dict.get("disclaimer", "Informational research aid. Not legal advice."),
    )


__all__ = [
    "QAInvalidModelOutputError",
    "ask_legal_question",
    "effective_retrieval_top_k",
    "hybrid_retrieve",
]
