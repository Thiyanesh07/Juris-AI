"""Hybrid dense + graph evidence retrieval (Phase 5)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_data_dir
from app.graph.client import GraphError, Neo4jClient
from app.retrieval.evidence import load_chunks_by_ids
from app.retrieval.index import (
    cosine_for_chunk_ids,
    load_embeddings_matrix,
    search_index_rows,
)
from app.retrieval.service import embed_query_vector

logger = logging.getLogger(__name__)

BridgeKey = tuple[str, str, str]
FallbackReason = Literal["neo4j_unavailable", "neo4j_timeout", "neo4j_query_failed"]


@dataclass
class GraphBridge:
    chunk_id: str
    seed_chunk_id: str
    entity_id: str
    entity_label: str
    entity_name: str
    seed_edge_confidence: float | None
    candidate_edge_confidence: float | None


@dataclass
class CandidateState:
    chunk_id: str
    is_seed: bool = False
    dense_score: float = 0.0
    dense_rank: int | None = None
    dense_matched: bool = False
    bridges: list[GraphBridge] = field(default_factory=list)
    graph_score: float = 0.0
    graph_rank: int | None = None
    normalized_dense: float = 0.0
    hybrid_score: float = 0.0


def clamp_score(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def normalize_dense_score(cosine: float) -> float:
    return clamp_score(cosine, 0.0, 1.0)


def bridge_confidence(
    seed_confidence: float | None,
    candidate_confidence: float | None,
) -> float:
    seed = 1.0 if seed_confidence is None else float(seed_confidence)
    candidate = 1.0 if candidate_confidence is None else float(candidate_confidence)
    return clamp_score(min(seed, candidate), 0.0, 1.0)


def bridge_weight(dense_rank: int, confidence: float) -> float:
    return (1.0 / float(dense_rank)) * 0.5 * confidence


def graph_score_for_bridges(
    bridges: list[GraphBridge],
    seed_rank_by_id: dict[str, int],
) -> float:
    if not bridges:
        return 0.0
    total = 0.0
    seen: set[BridgeKey] = set()
    for bridge in bridges:
        key = (bridge.chunk_id, bridge.seed_chunk_id, bridge.entity_id)
        if key in seen:
            continue
        seen.add(key)
        seed_rank = seed_rank_by_id.get(bridge.seed_chunk_id)
        if seed_rank is None:
            continue
        confidence = bridge_confidence(
            bridge.seed_edge_confidence,
            bridge.candidate_edge_confidence,
        )
        total += bridge_weight(seed_rank, confidence)
    return min(1.0, total)


def hybrid_fusion_score(
    normalized_dense: float,
    graph_score: float,
    *,
    vector_weight: float,
    graph_weight: float,
) -> float:
    return vector_weight * normalized_dense + graph_weight * graph_score


def _optional_confidence(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def classify_graph_expansion_error(exc: BaseException) -> FallbackReason:
    if isinstance(exc, TimeoutError):
        return "neo4j_timeout"
    if isinstance(exc, GraphError):
        return "neo4j_unavailable"
    name = type(exc).__name__
    module = getattr(type(exc), "__module__", "") or ""
    unavailable_names = {
        "ServiceUnavailable",
        "SessionExpired",
        "AuthError",
        "DatabaseUnavailable",
        "ConnectionExpired",
    }
    if name in unavailable_names or (
        "neo4j" in module and "Unavailable" in name
    ):
        return "neo4j_unavailable"
    if isinstance(exc, ConnectionError):
        return "neo4j_unavailable"
    return "neo4j_query_failed"


def _parse_bridge_row(row: dict[str, Any]) -> GraphBridge | None:
    try:
        chunk_id = str(row["chunk_id"])
        seed_chunk_id = str(row["seed_chunk_id"])
        entity_id = str(row["entity_id"])
        entity_label = str(row.get("entity_label") or "Concept")
        entity_name = str(row.get("entity_name") or "")
    except (KeyError, TypeError):
        return None
    if not chunk_id or not seed_chunk_id or not entity_id:
        return None
    return GraphBridge(
        chunk_id=chunk_id,
        seed_chunk_id=seed_chunk_id,
        entity_id=entity_id,
        entity_label=entity_label,
        entity_name=entity_name,
        seed_edge_confidence=_optional_confidence(row.get("seed_edge_confidence")),
        candidate_edge_confidence=_optional_confidence(
            row.get("candidate_edge_confidence")
        ),
    )


def _dedupe_bridges(bridges: list[GraphBridge]) -> list[GraphBridge]:
    seen: set[BridgeKey] = set()
    unique: list[GraphBridge] = []
    for bridge in bridges:
        key = (bridge.chunk_id, bridge.seed_chunk_id, bridge.entity_id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(bridge)
    return unique


def _build_graph_context(
    bridges: list[GraphBridge],
    seed_chunk_ids: list[str],
) -> dict[str, Any] | None:
    if not bridges:
        return None
    entities_map: dict[str, dict[str, str]] = {}
    for bridge in bridges:
        entities_map[bridge.entity_id] = {
            "id": bridge.entity_id,
            "label": bridge.entity_label,
            "name": bridge.entity_name,
        }
    entities = sorted(
        entities_map.values(),
        key=lambda item: (item["label"], item["name"], item["id"]),
    )
    return {
        "hops": 2,
        "seed_chunk_ids": sorted(seed_chunk_ids),
        "entities": entities,
    }


def _candidate_sort_key(candidate: CandidateState) -> tuple[Any, ...]:
    return (
        -candidate.hybrid_score,
        -candidate.normalized_dense,
        -candidate.graph_score,
        candidate.chunk_id,
    )


async def hybrid_retrieve(
    session: AsyncSession,
    graph_client: Neo4jClient,
    query: str,
    top_k: int,
    settings: Settings,
    embedder: Any | None = None,
) -> dict[str, Any]:
    if not 1 <= top_k <= settings.retrieval_max_top_k:
        raise ValueError(f"top_k must be between 1 and {settings.retrieval_max_top_k}")

    index, metadata, query_vector, _encoder = embed_query_vector(
        query, settings, embedder=embedder
    )
    dense_seed_top_k = min(
        settings.retrieval_max_top_k,
        max(top_k, settings.hybrid_dense_seed_top_k),
    )
    seed_hits = search_index_rows(index, metadata, query_vector, dense_seed_top_k)
    warnings: list[str] = []
    fallback: Literal["dense_only"] | None = None
    fallback_reason: FallbackReason | None = None

    if not seed_hits:
        return _empty_response(query, settings)

    seed_rank_by_id = {hit["chunk_id"]: int(hit["rank"]) for hit in seed_hits}
    candidates: dict[str, CandidateState] = {}
    for hit in seed_hits:
        chunk_id = hit["chunk_id"]
        candidates[chunk_id] = CandidateState(
            chunk_id=chunk_id,
            is_seed=True,
            dense_score=float(hit["score"]),
            dense_rank=int(hit["rank"]),
            dense_matched=True,
            normalized_dense=normalize_dense_score(float(hit["score"])),
        )

    graph_rows: list[dict[str, Any]] = []
    if settings.graph_max_hops >= 2:
        try:
            graph_rows = await asyncio.wait_for(
                graph_client.expand_supported_chunks(
                    list(seed_rank_by_id.keys()),
                    settings.hybrid_max_paths,
                ),
                timeout=settings.hybrid_graph_timeout_seconds,
            )
            graph_rows = graph_rows[: settings.hybrid_max_paths]
        except Exception as exc:
            fallback = "dense_only"
            fallback_reason = classify_graph_expansion_error(exc)
            logger.exception("Neo4j hybrid expansion failed (%s)", fallback_reason)
            graph_rows = []

    if graph_rows and fallback is None:
        parsed_bridges = [
            bridge for row in graph_rows if (bridge := _parse_bridge_row(row)) is not None
        ]
        deduped = _dedupe_bridges(parsed_bridges)
        graph_only_ids = sorted(
            {
                bridge.chunk_id
                for bridge in deduped
                if bridge.chunk_id not in candidates
            }
        )
        allowed_graph_ids = set(
            graph_only_ids[: settings.hybrid_max_graph_candidates]
        )
        for bridge in deduped:
            if bridge.chunk_id not in allowed_graph_ids and bridge.chunk_id not in candidates:
                continue
            state = candidates.get(bridge.chunk_id)
            if state is None:
                state = CandidateState(chunk_id=bridge.chunk_id)
                candidates[bridge.chunk_id] = state
            state.bridges.append(bridge)

    backfill_ids = [
        chunk_id
        for chunk_id, state in candidates.items()
        if not state.is_seed
    ]
    backfill_scores: dict[str, float] = {}
    if backfill_ids:
        embeddings = load_embeddings_matrix(get_data_dir(), settings.vector_index_name)
        backfill_scores = cosine_for_chunk_ids(
            query_vector,
            backfill_ids,
            metadata=metadata,
            embeddings=embeddings,
        )
    for chunk_id, state in candidates.items():
        if state.is_seed:
            continue
        # Graph-only candidates may reuse the query vector for cosine, but they
        # are not FAISS seeds: dense_rank stays None and dense_matched is false.
        state.dense_matched = False
        state.dense_rank = None
        if chunk_id in backfill_scores:
            state.dense_score = backfill_scores[chunk_id]
            state.normalized_dense = normalize_dense_score(state.dense_score)
        else:
            state.dense_score = 0.0
            state.normalized_dense = 0.0

    for state in candidates.values():
        if fallback is not None:
            state.bridges = []
        state.graph_score = graph_score_for_bridges(state.bridges, seed_rank_by_id)

    graph_ranked = sorted(
        [state for state in candidates.values() if state.graph_score > 0],
        key=lambda item: (-item.graph_score, item.chunk_id),
    )
    for rank, state in enumerate(graph_ranked, start=1):
        state.graph_rank = rank

    vector_weight = settings.hybrid_vector_weight
    graph_weight = settings.hybrid_graph_weight
    for state in candidates.values():
        state.hybrid_score = hybrid_fusion_score(
            state.normalized_dense,
            state.graph_score,
            vector_weight=vector_weight,
            graph_weight=graph_weight,
        )

    ordered = sorted(candidates.values(), key=_candidate_sort_key)
    chunk_ids = [state.chunk_id for state in ordered]
    evidence_by_id = await load_chunks_by_ids(session, chunk_ids)

    results: list[dict[str, Any]] = []
    for state in ordered:
        row = evidence_by_id.get(state.chunk_id)
        if row is None:
            warnings.append(f"omitted_missing_chunk:{state.chunk_id}")
            continue
        sources: list[str] = []
        if state.is_seed:
            sources.append("dense")
        if state.bridges and fallback is None:
            sources.append("graph")
        graph_context = (
            _build_graph_context(
                state.bridges,
                sorted({bridge.seed_chunk_id for bridge in state.bridges}),
            )
            if state.bridges and fallback is None
            else None
        )
        results.append(
            {
                **row,
                "dense_score": state.dense_score,
                "graph_score": state.graph_score,
                "hybrid_score": state.hybrid_score,
                "dense_rank": state.dense_rank,
                "graph_rank": state.graph_rank,
                "dense_matched": state.dense_matched,
                "evidence_sources": sources,
                "graph_context": graph_context,
            }
        )
        if len(results) >= top_k:
            break

    for rank, item in enumerate(results, start=1):
        item["rank"] = rank

    return {
        "query": query.strip(),
        "mode": "hybrid",
        "fallback": fallback,
        "fallback_reason": fallback_reason,
        "weights": {"vector": vector_weight, "graph": graph_weight},
        "score_type": (
            "hybrid = vector_weight * clamp(cosine, 0, 1) + graph_weight * graph_support"
        ),
        "warnings": warnings,
        "results": results,
    }


def _empty_response(query: str, settings: Settings) -> dict[str, Any]:
    return {
        "query": query.strip(),
        "mode": "hybrid",
        "fallback": None,
        "fallback_reason": None,
        "weights": {
            "vector": settings.hybrid_vector_weight,
            "graph": settings.hybrid_graph_weight,
        },
        "score_type": (
            "hybrid = vector_weight * clamp(cosine, 0, 1) + graph_weight * graph_support"
        ),
        "warnings": [],
        "results": [],
    }


__all__ = [
    "bridge_confidence",
    "bridge_weight",
    "clamp_score",
    "classify_graph_expansion_error",
    "graph_score_for_bridges",
    "hybrid_fusion_score",
    "hybrid_retrieve",
    "normalize_dense_score",
]
