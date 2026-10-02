"""Hybrid GraphRAG, Temporal Reasoning & Citation Grounding Pipeline (Phase 14 & 15).

Executes a deterministic state-graph pipeline:
  Query Analysis → Temporal Analysis → Legal Version Resolution → Parallel Retrieval →
  Multi-Hop Traversal → Temporal Evidence Filtering & Fusion → Context Construction →
  LLM Synthesis → Citation Verification → Groundedness Validation → Final Response.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_data_dir
from app.graph.client import Neo4jClient
from app.graph.traversal import compute_node_layout, traverse_multi_hop
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
from app.qa.provider import LLMProvider, build_llm_provider
from app.rag.citation_verifier import VerifiedCitation, verify_citation_grounding
from app.rag.evidence_fusion import (
    ResearchMode,
    RetrievalStrategy,
    fuse_and_rank_evidence,
)
from app.rag.query_analysis import QueryAnalysisResult, analyze_query
from app.rag.temporal import (
    LegalVersionInfo,
    resolve_legal_version,
)
from app.rag.validation import ValidationReport, validate_response_groundedness
from app.retrieval.evidence import load_chunks_by_ids
from app.retrieval.index import (
    search_index_rows,
)
from app.retrieval.service import embed_query_vector
from app.schemas.hybrid import HybridEvidence
from app.schemas.qa import (
    QAAskResponse,
    QACitation,
    QACitationValidation,
    QAGraphData,
    QAGraphEdge,
    QAGraphNode,
    QAReasoningStep,
    QARetrievalMeta,
    QATimelineEvent,
    QATemporalMeta,
    QATimingsMs,
)

logger = logging.getLogger(__name__)


def _ms_since(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def build_grounded_timeline_events(
    detected_entities: list[dict[str, Any]],
    query_analysis: QueryAnalysisResult,
) -> list[QATimelineEvent]:
    """Generate grounded chronological legal timeline events for detected legal entities."""
    events: list[QATimelineEvent] = []
    seen_ids: set[str] = set()

    entity_ids = {e["id"] for e in detected_entities}

    # Article 21 Timeline Events
    if "article:constitution_of_india:21" in entity_ids or "Article 21" in query_analysis.candidate_articles:
        events.append(QATimelineEvent(
            id="evt_const_1950",
            year="1950",
            title="Enactment of Constitution of India",
            documentType="CONSTITUTION",
            description="Article 21 enacted: 'No person shall be deprived of his life or personal liberty except according to procedure established by law.'",
            importance="HIGH",
        ))
        events.append(QATimelineEvent(
            id="evt_gopalan_1950",
            year="1950",
            title="A.K. Gopalan v. State of Madras",
            documentType="JUDGMENT",
            description="Supreme Court adopted a narrow literal interpretation of procedure established by law under Article 21.",
            importance="MEDIUM",
        ))
        events.append(QATimelineEvent(
            id="evt_maneka_1978",
            year="1978",
            title="Maneka Gandhi v. Union of India",
            documentType="JUDGMENT",
            description="Landmark decision expanding Article 21 to mandate that procedure must be 'just, fair, and reasonable'.",
            importance="HIGH",
        ))
        events.append(QATimelineEvent(
            id="evt_amd44_1978",
            year="1978",
            title="44th Constitutional Amendment Act, 1978",
            documentType="AMENDMENT",
            description="Amended Article 359 guaranteeing that Article 21 cannot be suspended even during a Proclamation of Emergency.",
            importance="HIGH",
        ))

    # Section 66A IT Act Timeline Events
    if "section:it_act_2000:66a" in entity_ids or "Section 66A" in query_analysis.candidate_sections or "act:it_act_2000" in entity_ids:
        events.append(QATimelineEvent(
            id="evt_itact_2000",
            year="2000",
            title="Information Technology Act, 2000",
            documentType="ACT",
            description="Enactment of the Information Technology Act, 2000 establishing legal recognition for electronic governance.",
            importance="MEDIUM",
        ))
        events.append(QATimelineEvent(
            id="evt_it_amd_2008",
            year="2008",
            title="IT (Amendment) Act, 2008",
            documentType="AMENDMENT",
            description="Inserted Section 66A criminalizing offensive messages sent through communication services.",
            importance="HIGH",
        ))
        events.append(QATimelineEvent(
            id="evt_shreya_2015",
            year="2015",
            title="Shreya Singhal v. Union of India",
            documentType="JUDGMENT",
            description="Supreme Court struck down Section 66A of the IT Act as unconstitutional under Article 19(1)(a).",
            importance="HIGH",
        ))

    # Article 19 Timeline Events
    if "article:constitution_of_india:19" in entity_ids or "Article 19" in query_analysis.candidate_articles:
        if not any(e.id == "evt_const_1950" for e in events):
            events.append(QATimelineEvent(
                id="evt_const_1950_art19",
                year="1950",
                title="Enactment of Constitution of India",
                documentType="CONSTITUTION",
                description="Article 19 enacted guaranteeing six fundamental freedoms subject to reasonable restrictions.",
                importance="HIGH",
            ))
        events.append(QATimelineEvent(
            id="evt_amd44_art19",
            year="1978",
            title="44th Constitutional Amendment Act, 1978",
            documentType="AMENDMENT",
            description="Omitted Article 19(1)(f) (Right to Property) from Fundamental Rights.",
            importance="HIGH",
        ))

    # Sort timeline events chronologically
    events.sort(key=lambda e: (int(e.year) if e.year.isdigit() else 2000, e.title))
    return events


async def execute_graphrag_pipeline(
    session: AsyncSession,
    graph_client: Neo4jClient,
    query: str,
    top_k: int | None,
    settings: Settings,
    *,
    mode: ResearchMode = "COMPREHENSIVE",
    strategy: RetrievalStrategy = "hybrid",
    graph_depth: int | None = None,
    provider: LLMProvider | None = None,
    embedder: Any | None = None,
) -> dict[str, Any]:
    """Execute full end-to-end Phase 14 GraphRAG + Phase 15 Temporal Legal Reasoning pipeline."""
    total_start = time.perf_counter()
    retrieval_start = time.perf_counter()
    reasoning_steps: list[dict[str, Any]] = []

    # ============================================================
    # STEP 1: QUERY ANALYSIS NODE
    # ============================================================
    qa_res: QueryAnalysisResult = analyze_query(query, mode=mode)
    target_depth = graph_depth or qa_res.suggested_graph_depth

    reasoning_steps.append({
        "step": 1,
        "description": (
            f"Query analysis completed: Intent='{qa_res.retrieval_intent}', "
            f"Complexity='{qa_res.query_complexity}', Graph Depth={target_depth}. "
            f"Detected {len(qa_res.detected_entities)} legal entities."
        ),
        "relationLabel": "QUERY_ANALYSIS",
    })

    # ============================================================
    # STEP 2: TEMPORAL ANALYSIS & LEGAL VERSION RESOLUTION NODE
    # ============================================================
    resolved_version: LegalVersionInfo | None = None
    target_entity_id = qa_res.detected_entities[0]["id"] if qa_res.detected_entities else None

    if target_entity_id:
        resolved_version = resolve_legal_version(target_entity_id, target_year=qa_res.target_year)

    timeline_events = build_grounded_timeline_events(qa_res.detected_entities, qa_res)

    if qa_res.is_temporal:
        reasoning_steps.append({
            "step": 2,
            "description": (
                f"Temporal analysis detected: Operator={qa_res.temporal_operator}, "
                f"Target Year={qa_res.target_year or 'N/A'}, Amendment={qa_res.referenced_amendment or 'None'}. "
                f"Resolved legal version status: '{resolved_version.status if resolved_version else 'UNKNOWN'}'."
            ),
            "relationLabel": "TEMPORAL_ANALYSIS",
        })

    # ============================================================
    # STEP 3: VECTOR RETRIEVAL NODE (FAISS)
    # ============================================================
    effective_top_k = top_k or settings.retrieval_default_top_k
    effective_top_k = min(effective_top_k, settings.qa_max_evidence)

    dense_hits: list[dict[str, Any]] = []
    query_vector = None
    metadata = None

    try:
        index, metadata, query_vector, _encoder = embed_query_vector(
            qa_res.normalized_query, settings, embedder=embedder
        )
        dense_seed_top_k = min(
            settings.retrieval_max_top_k,
            max(effective_top_k, settings.hybrid_dense_seed_top_k),
        )
        dense_hits = search_index_rows(index, metadata, query_vector, dense_seed_top_k)
    except Exception as exc:
        logger.warning("FAISS vector retrieval failed: %s", exc)
        dense_hits = []

    reasoning_steps.append({
        "step": len(reasoning_steps) + 1,
        "description": f"Vector retrieval (FAISS) matched {len(dense_hits)} candidate chunks.",
        "relationLabel": "VECTOR_SEARCH",
    })

    # ============================================================
    # STEP 4: GRAPH RETRIEVAL & MULTI-HOP TRAVERSAL NODE (Neo4j)
    # ============================================================
    graph_candidate_chunks: dict[str, dict[str, Any]] = {}
    graph_traversal_res: dict[str, Any] = {
        "nodes": [],
        "edges": [],
        "paths": [],
        "supporting_chunk_ids": [],
        "has_graph_evidence": False,
    }
    fallback: Literal["dense_only"] | None = None
    fallback_reason: Literal["neo4j_unavailable", "neo4j_timeout", "neo4j_query_failed"] | None = None

    if strategy in ("hybrid", "graph_only"):
        seed_chunk_ids = [str(h["chunk_id"]) for h in dense_hits]
        seed_entity_ids = [e["id"] for e in qa_res.detected_entities]

        try:
            expansion_rows: list[dict[str, Any]] = []
            if seed_chunk_ids:
                expansion_rows = await asyncio.wait_for(
                    graph_client.expand_supported_chunks(
                        seed_chunk_ids, settings.hybrid_max_paths
                    ),
                    timeout=settings.hybrid_graph_timeout_seconds,
                )

            for row in expansion_rows:
                cid = row["chunk_id"]
                if cid not in graph_candidate_chunks:
                    graph_candidate_chunks[cid] = {
                        "graph_score": 0.60,
                        "graph_context": {
                            "hops": 2,
                            "seed_chunk_ids": [row["seed_chunk_id"]],
                            "entities": [
                                {
                                    "id": row["entity_id"],
                                    "label": row["entity_label"],
                                    "name": row["entity_name"],
                                }
                            ],
                        },
                    }

            graph_traversal_res = await traverse_multi_hop(
                graph_client,
                seed_entity_ids=seed_entity_ids,
                seed_chunk_ids=seed_chunk_ids,
                max_hops=target_depth,
                max_nodes=settings.graph_max_nodes,
                mode=mode,
            )

            for scid in graph_traversal_res.get("supporting_chunk_ids", []):
                if scid not in graph_candidate_chunks:
                    graph_candidate_chunks[scid] = {
                        "graph_score": 0.50,
                        "graph_context": {
                            "hops": target_depth,
                            "seed_chunk_ids": seed_chunk_ids[:3],
                            "entities": [
                                {"id": n["id"], "label": n["type"], "name": n["label"]}
                                for n in graph_traversal_res["nodes"][:5]
                            ],
                        },
                    }

        except Exception as exc:
            fallback = "dense_only"
            name = type(exc).__name__
            if isinstance(exc, TimeoutError):
                fallback_reason = "neo4j_timeout"
            elif "Graph" in name or "Service" in name or isinstance(exc, ConnectionError):
                fallback_reason = "neo4j_unavailable"
            else:
                fallback_reason = "neo4j_query_failed"
            logger.warning("Neo4j graph traversal failed (%s): %s", fallback_reason, exc)

    path_count = len(graph_traversal_res.get("paths", []))
    node_count = len(graph_traversal_res.get("nodes", []))
    edge_count = len(graph_traversal_res.get("edges", []))

    reasoning_steps.append({
        "step": len(reasoning_steps) + 1,
        "description": (
            f"Multi-hop graph traversal (Neo4j depth={target_depth}) discovered "
            f"{node_count} legal entities, {edge_count} relationships across {path_count} paths."
        ),
        "relationLabel": "GRAPH_TRAVERSAL",
    })

    # ============================================================
    # STEP 5: EVIDENCE FUSION & RANKING NODE
    # ============================================================
    all_needed_chunk_ids = sorted(
        set([h["chunk_id"] for h in dense_hits] + list(graph_candidate_chunks.keys()))
    )

    all_chunks_by_id = {}
    if all_needed_chunk_ids:
        all_chunks_by_id = await load_chunks_by_ids(session, all_needed_chunk_ids)

    fused_evidence: list[HybridEvidence] = fuse_and_rank_evidence(
        dense_candidates=dense_hits,
        graph_candidate_chunks=graph_candidate_chunks,
        all_chunks_by_id=all_chunks_by_id,
        strategy=strategy,
        mode=mode,
        top_k=effective_top_k,
        vector_weight=settings.hybrid_vector_weight,
        graph_weight=settings.hybrid_graph_weight,
    )

    retrieval_ms = _ms_since(retrieval_start)

    reasoning_steps.append({
        "step": len(reasoning_steps) + 1,
        "description": (
            f"Evidence fusion merged and ranked top {len(fused_evidence)} legal evidence chunks "
            f"for Research Mode '{mode}'."
        ),
        "relationLabel": "EVIDENCE_FUSION",
    })

    layout_nodes = compute_node_layout(graph_traversal_res.get("nodes", []), query_name=query)

    temporal_meta = QATemporalMeta(
        detected=qa_res.is_temporal,
        target_date=qa_res.target_date,
        target_year=qa_res.target_year,
        date_range=qa_res.date_range,
        temporal_operator=qa_res.temporal_operator,
        referenced_amendment=qa_res.referenced_amendment,
        resolution_status=resolved_version.status if resolved_version else "UNKNOWN",
        applicable_versions=[resolved_version.model_dump()] if resolved_version else [],
        timeline_events=timeline_events,
    )

    if not fused_evidence:
        return {
            "answer": None,
            "status": "insufficient_evidence",
            "insufficient_evidence": True,
            "citations": [],
            "evidence": [],
            "graph": {
                "nodes": layout_nodes,
                "edges": graph_traversal_res.get("edges", []),
                "available": len(layout_nodes) > 0,
            },
            "reasoning_steps": reasoning_steps,
            "query_analysis": qa_res.model_dump(),
            "temporal": temporal_meta,
            "citation_validation": QACitationValidation(
                verified_count=0,
                unverified_count=0,
                grounded=True,
                warnings=["insufficient_evidence"],
            ),
            "retrieval": QARetrievalMeta(
                mode=strategy,
                fallback=fallback,
                fallback_reason=fallback_reason,
                warnings=[],
                evidence_count=0,
                evidence_dropped_for_context=0,
            ),
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "llm_called": False,
            "timings_ms": QATimingsMs(retrieval=retrieval_ms, llm=0),
            "disclaimer": "Informational research aid. Not legal advice.",
        }

    # ============================================================
    # STEP 6: CONTEXT CONSTRUCTION NODE (With Temporal Guidance)
    # ============================================================
    prepared_evidence, blocks, dropped = prepare_evidence_for_prompt(fused_evidence, settings)
    system_message = build_system_message()
    
    # Inject temporal instructions into user message prompt
    temporal_prompt_header = ""
    if qa_res.is_temporal:
        temporal_prompt_header = (
            f"[TEMPORAL REQUIREMENT: Intent={qa_res.temporal_intent}, "
            f"Target Year={qa_res.target_year or 'Current Law'}, Operator={qa_res.temporal_operator}. "
            f"Respect temporal validity. Distinguish historical law from current law.]\n\n"
        )

    user_message = build_user_message(temporal_prompt_header + qa_res.normalized_query, blocks)

    # ============================================================
    # STEP 7: LLM SYNTHESIS NODE
    # ============================================================
    llm_start = time.perf_counter()
    llm_client = provider or build_llm_provider(settings)

    last_problem = "Model output failed validation"
    final_answer: str | None = None
    is_insufficient: bool = False
    public_citations: list[QACitation] = []
    llm_called = True

    for attempt in range(2):
        msg = user_message if attempt == 0 else build_correction_user_message(user_message, last_problem)
        raw_output = await llm_client.generate(
            system_message=system_message,
            user_message=msg,
            timeout_seconds=settings.llm_timeout_seconds,
            max_output_tokens=settings.llm_max_output_tokens,
        )
        try:
            parsed = parse_llm_output(raw_output)
            validated = validate_llm_citations(parsed, evidence_count=len(prepared_evidence))
            public_citations = build_public_citations(validated, prepared_evidence)
            final_answer = parsed.answer
            is_insufficient = parsed.insufficient_evidence
            break
        except (LLMOutputParseError, CitationValidationError) as exc:
            last_problem = validation_problem_message(exc)
            if attempt == 1:
                final_answer = (
                    "Insufficient verified evidence in current legal corpus to provide a grounded answer."
                )
                is_insufficient = True
                public_citations = []

    llm_ms = _ms_since(llm_start)

    # ============================================================
    # STEP 8: CITATION VERIFICATION & TEMPORAL GROUNDEDNESS VALIDATION NODE
    # ============================================================
    verified_citation_objects: list[VerifiedCitation] = []
    raw_prepared_dicts = [item.model_dump() for item in prepared_evidence]

    for c in public_citations:
        verified_c = verify_citation_grounding(c.marker, c.evidence_rank, raw_prepared_dicts)
        verified_citation_objects.append(verified_c)

    val_report: ValidationReport = validate_response_groundedness(
        answer=final_answer,
        citations=verified_citation_objects,
        query_analysis=qa_res,
        resolved_version=resolved_version,
        insufficient_evidence=is_insufficient,
    )

    reasoning_steps.append({
        "step": len(reasoning_steps) + 1,
        "description": (
            f"Citation verification & temporal validation completed: Grounded={val_report.grounded}, "
            f"Verified Citations={val_report.verified_count}/{len(public_citations)}, "
            f"Temporal Alignment={val_report.temporal_valid}."
        ),
        "relationLabel": "VALIDATION_GROUNDING",
    })

    status_str = "insufficient_evidence" if is_insufficient else "answered"

    return {
        "answer": final_answer,
        "status": status_str,
        "insufficient_evidence": is_insufficient,
        "citations": public_citations,
        "evidence": prepared_evidence,
        "graph": {
            "nodes": layout_nodes,
            "edges": graph_traversal_res.get("edges", []),
            "available": len(layout_nodes) > 0,
        },
        "reasoning_steps": reasoning_steps,
        "query_analysis": qa_res.model_dump(),
        "temporal": temporal_meta,
        "citation_validation": QACitationValidation(
            verified_count=val_report.verified_count,
            unverified_count=val_report.unverified_count,
            grounded=val_report.grounded,
            warnings=val_report.warnings,
        ),
        "retrieval": QARetrievalMeta(
            mode=strategy,
            fallback=fallback,
            fallback_reason=fallback_reason,
            warnings=[],
            evidence_count=len(prepared_evidence),
            evidence_dropped_for_context=dropped,
        ),
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "llm_called": llm_called,
        "timings_ms": QATimingsMs(retrieval=retrieval_ms, llm=llm_ms),
        "disclaimer": "Informational research aid. Not legal advice.",
    }
