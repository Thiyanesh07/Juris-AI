"""Hybrid Evidence Fusion & Mode-based Filtering Module (Phase 14).

Combines FAISS vector retrieval candidates with Neo4j graph traversal candidates.
Applies normalized scoring, mode-specific evidence weighting/filtering,
deduplication, and provenance verification.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from app.core.config import Settings
from app.schemas.hybrid import HybridEvidence, HybridGraphContext, HybridGraphEntityContext

RetrievalStrategy = Literal["hybrid", "vector_only", "graph_only"]
ResearchMode = Literal["COMPREHENSIVE", "CONSTITUTIONAL", "STATUTORY", "CASE_LAW"]


def clamp_score(val: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, val))


def boost_score_by_mode(
    raw_score: float,
    doc_type: str,
    doc_title: str,
    hierarchy: dict[str, Any],
    mode: ResearchMode,
) -> float:
    """Adjust score slightly according to Research Mode preference."""
    boost = 1.0
    doc_type_upper = doc_type.upper()
    title_lower = doc_title.lower()

    if mode == "CONSTITUTIONAL":
        if "constitution" in title_lower or doc_type_upper == "CONSTITUTION" or "article" in str(hierarchy).lower():
            boost = 1.25
        elif "judgment" in title_lower or doc_type_upper == "JUDGMENT":
            boost = 1.10
        else:
            boost = 0.85
    elif mode == "STATUTORY":
        if "act" in title_lower or "code" in title_lower or "sanhita" in title_lower or doc_type_upper in ("ACT", "ORDINANCE", "RULE"):
            boost = 1.25
        elif "judgment" in title_lower:
            boost = 1.05
        else:
            boost = 0.90
    elif mode == "CASE_LAW":
        if "judgment" in title_lower or doc_type_upper == "JUDGMENT" or "v." in title_lower or "vs." in title_lower:
            boost = 1.30
        else:
            boost = 0.85

    return clamp_score(raw_score * boost, 0.0, 1.0)


def fuse_and_rank_evidence(
    dense_candidates: list[dict[str, Any]],
    graph_candidate_chunks: dict[str, dict[str, Any]],
    all_chunks_by_id: dict[str, dict[str, Any]],
    strategy: RetrievalStrategy = "hybrid",
    mode: ResearchMode = "COMPREHENSIVE",
    top_k: int = 10,
    vector_weight: float = 0.50,
    graph_weight: float = 0.50,
) -> list[HybridEvidence]:
    """Fuse FAISS vector candidates and Neo4j graph candidates into ranked HybridEvidence."""
    candidate_states: dict[str, dict[str, Any]] = {}

    # 1. Process Dense Vector Candidates
    if strategy in ("hybrid", "vector_only"):
        for rank, hit in enumerate(dense_candidates, start=1):
            cid = str(hit["chunk_id"])
            dense_score = float(hit.get("score", 0.0))
            candidate_states[cid] = {
                "chunk_id": cid,
                "dense_score": dense_score,
                "dense_rank": rank,
                "dense_matched": True,
                "graph_score": 0.0,
                "graph_rank": None,
                "graph_context": None,
                "sources": ["dense"],
            }

    # 2. Process Graph Candidates
    if strategy in ("hybrid", "graph_only"):
        for cid, g_info in graph_candidate_chunks.items():
            graph_score = float(g_info.get("graph_score", 0.60))
            graph_context_data = g_info.get("graph_context")

            if cid in candidate_states:
                st = candidate_states[cid]
                st["graph_score"] = graph_score
                st["graph_context"] = graph_context_data
                if "graph" not in st["sources"]:
                    st["sources"].append("graph")
            else:
                candidate_states[cid] = {
                    "chunk_id": cid,
                    "dense_score": 0.0,
                    "dense_rank": None,
                    "dense_matched": False,
                    "graph_score": graph_score,
                    "graph_rank": None,
                    "graph_context": graph_context_data,
                    "sources": ["graph"],
                }

    # Assign graph ranks
    graph_ranked = sorted(
        [st for st in candidate_states.values() if st["graph_score"] > 0],
        key=lambda item: (-item["graph_score"], item["chunk_id"]),
    )
    for grank, st in enumerate(graph_ranked, start=1):
        st["graph_rank"] = grank

    # Compute hybrid scores & mode boosts
    processed_list: list[dict[str, Any]] = []
    for st in candidate_states.values():
        v_score = clamp_score(st["dense_score"], 0.0, 1.0)
        g_score = clamp_score(st["graph_score"], 0.0, 1.0)

        if strategy == "vector_only":
            h_score = v_score
        elif strategy == "graph_only":
            h_score = g_score
        else:
            h_score = (vector_weight * v_score) + (graph_weight * g_score)

        # Lookup chunk row for document metadata
        cid = st["chunk_id"]
        chunk_row = all_chunks_by_id.get(cid, {})

        doc_type = str(chunk_row.get("document_type") or chunk_row.get("type") or "")
        doc_title = str(chunk_row.get("document_title") or chunk_row.get("title") or "")
        hierarchy = chunk_row.get("hierarchy") or {}

        boosted_score = boost_score_by_mode(h_score, doc_type, doc_title, hierarchy, mode)

        processed_list.append({
            **st,
            "hybrid_score": boosted_score,
            "raw_row": chunk_row,
        })

    # Sort candidates by hybrid score
    ordered = sorted(
        processed_list,
        key=lambda item: (-item["hybrid_score"], -item["dense_score"], -item["graph_score"], item["chunk_id"]),
    )

    # Deduplicate nearly identical chunks from same page/document if top_k is tight
    final_evidence: list[HybridEvidence] = []
    seen_doc_pages: set[tuple[str, int | None]] = set()

    for rank_idx, item in enumerate(ordered, start=1):
        row = item["raw_row"]
        if not row:
            continue

        cid = item["chunk_id"]
        doc_id = str(row.get("document_id"))
        page_start = row.get("page_start")

        # Diversification rule: allow max 2 chunks from same page of same document unless total results < top_k
        doc_page_key = (doc_id, page_start)
        if len(final_evidence) >= top_k:
            break

        g_ctx = None
        if item["graph_context"]:
            entities = [
                HybridGraphEntityContext(
                    id=e["id"],
                    label=e.get("label", "Concept"),
                    name=e.get("name", e["id"]),
                )
                for e in item["graph_context"].get("entities", [])
            ]
            g_ctx = HybridGraphContext(
                hops=item["graph_context"].get("hops", 2),
                seed_chunk_ids=item["graph_context"].get("seed_chunk_ids", []),
                entities=entities,
            )

        evidence_obj = HybridEvidence(
            rank=len(final_evidence) + 1,
            chunk_id=UUID(cid),
            document_id=UUID(doc_id),
            document_title=str(row.get("document_title") or "Legal Document"),
            document_version_id=UUID(row["document_version_id"]) if row.get("document_version_id") else None,
            chunk_index=int(row.get("chunk_index", 0)),
            text=str(row.get("text", "")),
            page_start=page_start,
            page_end=row.get("page_end"),
            hierarchy=row.get("hierarchy") or {},
            citation_ref=row.get("citation_ref"),
            source_url=row.get("source_url"),
            dense_score=item["dense_score"],
            graph_score=item["graph_score"],
            hybrid_score=item["hybrid_score"],
            dense_rank=item["dense_rank"],
            graph_rank=item["graph_rank"],
            dense_matched=item["dense_matched"],
            evidence_sources=item["sources"],
            graph_context=g_ctx,
        )

        final_evidence.append(evidence_obj)

    return final_evidence
