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
from uuid import UUID, uuid4

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
    EvidenceSufficiencyAssessment,
    ResearchMode,
    RetrievalStrategy,
    assess_evidence_sufficiency,
    evaluate_evidence_sufficiency,
    fuse_and_rank_evidence,
)
from app.rag.query_analysis import QueryAnalysisResult, analyze_query
from app.rag.temporal import (
    LegalVersionInfo,
    resolve_legal_version,
)
from app.rag.validation import ValidationReport, validate_response_groundedness
from app.retrieval.evidence import load_chunks_by_ids, search_chunks_by_identifiers
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
    query_id = f"qry_{uuid4().hex[:12]}"

    # ============================================================
    # STEP 1: QUERY ANALYSIS NODE
    # ============================================================
    qa_res: QueryAnalysisResult = analyze_query(query, mode=mode)
    target_depth = graph_depth or qa_res.suggested_graph_depth

    logger.info(
        "retrieval_diagnostics",
        extra={
            "query_id": query_id,
            "stage": "query_analysis",
            "normalized_query": qa_res.normalized_query,
            "retrieval_intent": qa_res.retrieval_intent,
            "complexity": qa_res.query_complexity,
            "detected_entities_count": len(qa_res.detected_entities),
            "entities": [e.get("name") for e in qa_res.detected_entities],
            "subqueries_count": len(qa_res.subqueries),
            "suggested_graph_depth": target_depth,
        },
    )

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
    # STEP 3: VECTOR RETRIEVAL NODE (FAISS Multi-Query Retrieval)
    # ============================================================
    effective_top_k = top_k or settings.retrieval_default_top_k
    effective_top_k = min(effective_top_k, settings.qa_max_evidence)

    dense_hits: list[dict[str, Any]] = []
    query_vector = None
    metadata = None

    try:
        index, metadata, query_vector, encoder = embed_query_vector(
            qa_res.normalized_query, settings, embedder=embedder
        )
        dense_seed_top_k = min(
            settings.retrieval_max_top_k,
            max(effective_top_k * 4, settings.hybrid_dense_seed_top_k, 30),
        )
        main_hits = search_index_rows(index, metadata, query_vector, dense_seed_top_k)

        # Multi-query candidate expansion with Reciprocal Rank Fusion (RRF) calibration
        rrf_k = 60
        rrf_scores: dict[str, float] = {}
        candidate_meta: dict[str, dict[str, Any]] = {}

        for rank, h in enumerate(main_hits, start=1):
            cid = str(h["chunk_id"])
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))
            candidate_meta[cid] = dict(h)

        queries_to_embed: list[str] = []
        if qa_res.subqueries:
            for sq in qa_res.subqueries[:3]:
                if sq and sq.strip() and sq.strip().lower() != qa_res.normalized_query.lower():
                    queries_to_embed.append(sq.strip())
        for ent in qa_res.detected_entities[:3]:
            ename = ent.get("name")
            if ename and len(ename) > 3 and ename.lower() not in [q.lower() for q in queries_to_embed]:
                queries_to_embed.append(ename)

        if queries_to_embed and encoder is not None:
            sub_vecs = encoder.embed(queries_to_embed)
            for i in range(len(queries_to_embed)):
                row_vec = sub_vecs[i : i + 1]
                sub_hits = search_index_rows(index, metadata, row_vec, 25)
                for rank, sh in enumerate(sub_hits, start=1):
                    scid = str(sh["chunk_id"])
                    rrf_scores[scid] = rrf_scores.get(scid, 0.0) + (0.75 / (rrf_k + rank))
                    if scid not in candidate_meta:
                        candidate_meta[scid] = dict(sh)

        # Exact identifier matching alongside semantic retrieval
        identifier_terms = (
            qa_res.candidate_articles
            + qa_res.candidate_sections
            + qa_res.candidate_judgments
            + qa_res.candidate_acts
            + qa_res.candidate_doctrines
        )
        if identifier_terms:
            try:
                exact_hits = await search_chunks_by_identifiers(session, identifier_terms, top_k=15)
                for rank, eh in enumerate(exact_hits, start=1):
                    ecid = str(eh["chunk_id"])
                    rrf_scores[ecid] = rrf_scores.get(ecid, 0.0) + (1.25 / (rrf_k + rank))
                    if ecid not in candidate_meta:
                        candidate_meta[ecid] = dict(eh)
            except Exception as exc:
                logger.debug("Exact identifier retrieval non-fatal error: %s", exc)

        sorted_cids = sorted(rrf_scores.keys(), key=lambda cid: -rrf_scores[cid])
        fused_hits: list[dict[str, Any]] = []
        for rank, cid in enumerate(sorted_cids[:dense_seed_top_k], start=1):
            item = dict(candidate_meta[cid])
            item["rank"] = rank
            fused_hits.append(item)
        dense_hits = fused_hits

    except Exception as exc:
        logger.warning("FAISS vector retrieval failed: %s", exc)
        dense_hits = []

    logger.info(
        "retrieval_diagnostics",
        extra={
            "query_id": query_id,
            "stage": "vector_retrieval",
            "dense_candidates_count": len(dense_hits),
            "dense_scores": [
                {"chunk_id": str(h["chunk_id"]), "score": round(float(h["score"]), 4), "rank": h["rank"]}
                for h in dense_hits[:10]
            ],
        },
    )

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

        graph_timeout = (
            max(settings.hybrid_graph_timeout_seconds, 8.0)
            if settings.app_env == "production"
            else settings.hybrid_graph_timeout_seconds
        )

        try:
            expansion_rows: list[dict[str, Any]] = []
            if seed_chunk_ids:
                expansion_rows = await asyncio.wait_for(
                    graph_client.expand_supported_chunks(
                        seed_chunk_ids, settings.hybrid_max_paths
                    ),
                    timeout=graph_timeout,
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

            graph_traversal_res = await asyncio.wait_for(
                traverse_multi_hop(
                    graph_client,
                    seed_entity_ids=seed_entity_ids,
                    seed_chunk_ids=seed_chunk_ids,
                    max_hops=target_depth,
                    max_nodes=settings.graph_max_nodes,
                    mode=mode,
                ),
                timeout=graph_timeout,
            )

            for scid in graph_traversal_res.get("supporting_chunk_ids", []):
                if scid not in graph_candidate_chunks:
                    actual_hops = graph_traversal_res.get("chunk_hop_distance", {}).get(scid, target_depth)
                    graph_candidate_chunks[scid] = {
                        "graph_score": 0.50,
                        "graph_context": {
                            "hops": actual_hops,
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
            if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
                fallback_reason = "neo4j_timeout"
            elif "Graph" in name or "Service" in name or isinstance(exc, ConnectionError):
                fallback_reason = "neo4j_unavailable"
            else:
                fallback_reason = "neo4j_query_failed"
            logger.warning("Neo4j graph traversal failed (%s): %s", fallback_reason, exc)

    path_count = len(graph_traversal_res.get("paths", []))
    node_count = len(graph_traversal_res.get("nodes", []))
    edge_count = len(graph_traversal_res.get("edges", []))

    logger.info(
        "retrieval_diagnostics",
        extra={
            "query_id": query_id,
            "stage": "graph_expansion",
            "seed_entities": [e["id"] for e in qa_res.detected_entities],
            "seed_chunk_ids_count": len(dense_hits),
            "graph_candidates_count": len(graph_candidate_chunks),
            "nodes_count": node_count,
            "edges_count": edge_count,
            "paths_count": path_count,
            "fallback": fallback,
            "fallback_reason": fallback_reason,
        },
    )

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
        detected_entities=qa_res.detected_entities,
    )

    is_sufficient, insufficiency_reason = evaluate_evidence_sufficiency(
        fused_evidence=fused_evidence,
        detected_entities=qa_res.detected_entities,
        query_text=qa_res.normalized_query,
    )

    logger.info(
        "retrieval_diagnostics",
        extra={
            "query_id": query_id,
            "stage": "evidence_fusion",
            "candidates_dense_count": len(dense_hits),
            "candidates_graph_count": len(graph_candidate_chunks),
            "total_candidates": len(all_needed_chunk_ids),
            "fused_evidence_count": len(fused_evidence),
            "is_sufficient": is_sufficient,
            "insufficiency_reason": insufficiency_reason,
            "selected_evidence": [
                {
                    "chunk_id": str(e.chunk_id),
                    "rank": e.rank,
                    "hybrid_score": round(e.hybrid_score, 4),
                    "title": e.document_title,
                }
                for e in fused_evidence[:5]
            ],
        },
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

    assessment = assess_evidence_sufficiency(
        fused_evidence=fused_evidence,
        detected_entities=qa_res.detected_entities,
        query_text=qa_res.normalized_query,
    )
    is_sufficient = assessment.is_sufficient
    insufficiency_reason = assessment.rejection_reason

    # Case D: No usable evidence retrieved at all or all below minimum relevance threshold
    if not fused_evidence or assessment.state == "NO_EVIDENCE":
        insufficiency_warning = insufficiency_reason or "insufficient_corpus_evidence"
        return {
            "answer": "The system could not retrieve supporting legal material from the indexed corpus matching the requested query. To research this topic, consider querying by specific Act name, section number, or constitutional article.",
            "status": "insufficient_evidence",
            "answer_status": "insufficient_evidence",
            "insufficient_evidence": True,
            "citations": [],
            "evidence": fused_evidence,
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
                grounded=False,
                warnings=[insufficiency_warning],
            ),
            "retrieval": QARetrievalMeta(
                mode=strategy,
                fallback=fallback,
                fallback_reason=fallback_reason,
                warnings=[insufficiency_warning] if insufficiency_reason else [],
                evidence_count=len(fused_evidence),
                evidence_dropped_for_context=0,
            ),
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "llm_called": False,
            "timings_ms": QATimingsMs(retrieval=retrieval_ms, llm=0),
            "disclaimer": "Informational research aid. Not legal advice.",
            "missing_authorities": assessment.missing_authorities,
            "gap_type": assessment.gap_type,
            "notice": "No usable legal evidence retrieved for this query from the indexed corpus.",
        }

    # ============================================================
    # STEP 6: CONTEXT CONSTRUCTION NODE (With Temporal & Fallback Guidance)
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

    # Retrieval-First Fallback Guidance according to Assessment State
    guidance: str | None = None
    if assessment.state == "PARTIAL":
        guidance = (
            f"The retrieved evidence partially covers the legal subjects. "
            f"The following requested authorities could not be verified in the retrieved documents: {', '.join(assessment.missing_authorities)}. "
            f"Provide a clear, well-structured partial answer based ONLY on what the retrieved evidence establishes. "
            f"Explicitly state what the retrieved evidence does not establish and which specific authorities could not be verified. "
            f"Never attach citations to statements that are not directly supported by the retrieved text."
        )
    elif assessment.state == "AUTHORITY_ABSENT":
        guidance = (
            f"The specific legal authority requested ({', '.join(assessment.missing_authorities)}) is absent from the indexed corpus, "
            f"though related background legal fragments were retrieved. "
            f"Provide a responsible general legal explanation to help the user understand the subject without pretending the database supplied the missing authority. "
            f"Clearly distinguish general legal background from claims verified against the retrieved corpus. "
            f"Only cite the retrieved evidence [n] if a statement is directly taken from the retrieved text; DO NOT fabricate citations for absent authorities."
        )

    user_message = build_user_message(
        temporal_prompt_header + qa_res.normalized_query,
        blocks,
        guidance=guidance,
    )

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
    timed_out = False

    for attempt in range(2):
        msg = user_message if attempt == 0 else build_correction_user_message(user_message, last_problem)
        try:
            raw_output = await llm_client.generate(
                system_message=system_message,
                user_message=msg,
                timeout_seconds=settings.llm_timeout_seconds,
                max_output_tokens=settings.llm_max_output_tokens,
            )
        except (TimeoutError, asyncio.TimeoutError) as exc:
            logger.warning("LLM inference timed out (attempt %d): %s", attempt, exc)
            if attempt == 1:
                final_answer = "The legal research synthesis timed out while contacting the language model. Retrieved evidence is preserved below for your review."
                is_insufficient = True
                timed_out = True
                public_citations = []
                break
            continue
        except Exception as exc:
            logger.warning("LLM generation error (attempt %d): %s", attempt, exc)
            if attempt == 1:
                final_answer = (
                    "Insufficient verified evidence in current legal corpus to provide a grounded answer."
                )
                is_insufficient = True
                public_citations = []
                break
            continue

        try:
            parsed = parse_llm_output(raw_output)
            allow_empty = assessment.state in ("AUTHORITY_ABSENT", "NO_EVIDENCE")
            validated = validate_llm_citations(parsed, evidence_count=len(prepared_evidence), allow_empty_citations=allow_empty)
            public_citations = build_public_citations(validated, prepared_evidence)
            final_answer = parsed.answer
            is_insufficient = parsed.insufficient_evidence
            break
        except (LLMOutputParseError, CitationValidationError) as exc:
            last_problem = validation_problem_message(exc)
            if attempt == 1:
                if assessment.state == "AUTHORITY_ABSENT":
                    missing_str = ", ".join(assessment.missing_authorities) if assessment.missing_authorities else "the requested legal authority"
                    final_answer = (
                        f"The requested legal authority ({missing_str}) is not found in the currently indexed Juris AI corpus. "
                        f"Retrieved background legal fragments are preserved below for review."
                    )
                elif assessment.state == "PARTIAL":
                    missing_str = ", ".join(assessment.missing_authorities) if assessment.missing_authorities else "some requested legal authorities"
                    final_answer = (
                        f"The retrieved evidence partially addresses the subject, but does not contain sufficient authority to verify {missing_str}. "
                        f"Best available retrieved legal fragments are preserved below for review."
                    )
                else:
                    final_answer = (
                        "Insufficient verified evidence in current legal corpus to provide a grounded answer."
                    )
                is_insufficient = True
                public_citations = []

    llm_ms = _ms_since(llm_start)

    # Ensure non-empty final answer when fragments are preserved
    if not final_answer or not final_answer.strip():
        if assessment.state == "AUTHORITY_ABSENT":
            missing_str = ", ".join(assessment.missing_authorities) if assessment.missing_authorities else "the requested legal authority"
            final_answer = (
                f"The requested legal authority ({missing_str}) is not present in the indexed Juris AI corpus. "
                f"Retrieved background legal fragments are preserved below for reference."
            )
        elif assessment.state == "PARTIAL":
            missing_str = ", ".join(assessment.missing_authorities) if assessment.missing_authorities else "some requested legal authorities"
            final_answer = (
                f"The retrieved evidence partially addresses the subject, but does not contain sufficient authority to verify {missing_str}. "
                f"Best available retrieved legal fragments are preserved below for review."
            )
        else:
            final_answer = (
                "Insufficient verified evidence in current legal corpus to provide a grounded answer."
            )

    # ============================================================
    # STEP 8: CITATION VERIFICATION & TEMPORAL GROUNDEDNESS VALIDATION NODE
    # ============================================================
    verified_citation_objects: list[VerifiedCitation] = []
    raw_prepared_dicts = [item.model_dump() for item in prepared_evidence]

    for c in public_citations:
        verified_c = verify_citation_grounding(c.marker, c.evidence_rank, raw_prepared_dicts)
        verified_citation_objects.append(verified_c)
        c.verification_status = verified_c.verification_status

    val_report: ValidationReport = validate_response_groundedness(
        answer=final_answer,
        citations=verified_citation_objects,
        query_analysis=qa_res,
        resolved_version=resolved_version,
        insufficient_evidence=is_insufficient,
    )

    # Update verification_status on prepared evidence chunks
    verified_ranks = {c.evidence_rank for c in public_citations if c.verification_status == "VERIFIED"}
    cited_ranks = {c.evidence_rank for c in public_citations}
    for ev in prepared_evidence:
        if ev.rank in verified_ranks:
            ev.verification_status = "VERIFIED"
        elif ev.rank in cited_ranks:
            ev.verification_status = "PARTIALLY_VERIFIED"
        else:
            ev.verification_status = "UNVERIFIED"

    # Determine answer status, notice, and operational state
    missing_authorities = assessment.missing_authorities
    gap_type = assessment.gap_type

    if timed_out:
        answer_status = "technical_timeout"
        status_str = "insufficient_evidence"
        notice = "Research service timed out — please retry."
    elif assessment.state == "STRONG" and not is_insufficient:
        answer_status = "full_answer"
        status_str = "answered"
        notice = None
    elif assessment.state == "STRONG" and is_insufficient:
        if public_citations:
            answer_status = "partial_answer"
            status_str = "answered"
            notice = "Partial answer: The retrieved evidence contains relevant authorities but does not fully resolve all aspects of the query. Showing the best available retrieved information."
        elif final_answer and len(final_answer.strip()) > 30 and not final_answer.startswith("Insufficient verified evidence"):
            answer_status = "general_fallback"
            status_str = "answered"
            notice = "The retrieved evidence does not directly establish the requested rules. A general background explanation is provided below with retrieved fragments preserved for review."
        else:
            answer_status = "insufficient_evidence"
            status_str = "insufficient_evidence"
            notice = "The language model determined that the retrieved evidence was insufficient to answer the query."
    elif assessment.state == "PARTIAL":
        answer_status = "partial_answer"
        status_str = "answered"
        notice = (
            f"Partial answer: Some requested legal authorities ({', '.join(missing_authorities)}) "
            f"could not be verified against the indexed corpus. Showing the best available retrieved information."
        )
    elif assessment.state == "AUTHORITY_ABSENT":
        answer_status = "general_fallback"
        status_str = "answered"
        notice = (
            "Requested information not found in the currently indexed Juris AI corpus. "
            "The explanation below is general background and has not been verified against a matching source in this database. "
            "Absence from the current index does not prove the information does not exist in law or elsewhere."
        )
    else:
        answer_status = "insufficient_evidence"
        status_str = "insufficient_evidence"
        notice = "Insufficient evidence retrieved from the indexed corpus."

    logger.info(
        "retrieval_diagnostics",
        extra={
            "query_id": query_id,
            "stage": "citation_validation",
            "status": status_str,
            "answer_status": answer_status,
            "insufficient_evidence": is_insufficient,
            "citations_count": len(public_citations),
            "verified_count": val_report.verified_count,
            "unverified_count": val_report.unverified_count,
            "grounded": val_report.grounded,
            "warnings": val_report.warnings,
        },
    )

    reasoning_steps.append({
        "step": len(reasoning_steps) + 1,
        "description": (
            f"Citation verification & validation completed: Status={answer_status}, Grounded={val_report.grounded}, "
            f"Verified Citations={val_report.verified_count}/{len(public_citations)}, "
            f"Temporal Alignment={val_report.temporal_valid}."
        ),
        "relationLabel": "VALIDATION_GROUNDING",
    })

    return {
        "answer": final_answer,
        "status": status_str,
        "answer_status": answer_status,
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
        "missing_authorities": missing_authorities,
        "gap_type": gap_type,
        "notice": notice,
    }
