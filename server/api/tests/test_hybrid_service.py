"""Service-level hybrid retrieval tests with mocked graph and fake embeddings."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.graph.client import GraphError
from app.models import Document
from app.models.chunk import Chunk
from app.models.enums import DocumentType
from app.retrieval.hybrid import hybrid_retrieve
from app.retrieval.index import save_index
from tests.test_retrieval import (
    TEST_MODEL,
    TEST_POOLING,
    FakeEmbedder,
    _configure_settings,
    _records,
)


class FakeGraphClient:
    def __init__(self, rows: list[dict[str, Any]] | None = None, *, error: Exception | None = None):
        self.rows = rows or []
        self.error = error
        self.calls = 0

    async def expand_supported_chunks(self, seed_ids: list[str], max_paths: int) -> list[dict]:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.rows


async def _seed_db(session: AsyncSession) -> None:
    doc = Document(title="Constitution", type=DocumentType.CONSTITUTION, source="test")
    session.add(doc)
    await session.flush()
    for record in _records():
        session.add(
            Chunk(
                id=UUID(record["chunk_id"]),
                document_id=doc.id,
                chunk_index=record["chunk_index"],
                text=record["text"],
                char_count=len(record["text"]),
                hierarchy=record["hierarchy"],
                citation_ref=record["citation_ref"],
                page_start=record["page_start"],
                page_end=record["page_end"],
            )
        )
    await session.commit()


def _save_index(tmp_path: Path) -> None:
    save_index(
        data_dir=tmp_path,
        index_name="test",
        vectors=np.eye(2, dtype=np.float32),
        chunk_records=_records(),
        model_name=TEST_MODEL,
        pooling_method=TEST_POOLING,
        max_tokens=32,
    )


@pytest.fixture
def hybrid_settings(tmp_path: Path) -> Settings:
    settings = get_settings()
    snapshot = settings.model_dump()
    _configure_settings(settings, tmp_path)
    _save_index(tmp_path)
    yield settings
    for key, value in snapshot.items():
        object.__setattr__(settings, key, value)


async def test_dense_seed_graph_chunk_path(
    session: AsyncSession,
    hybrid_settings: Settings,
) -> None:
    await _seed_db(session)
    graph = FakeGraphClient(
        [
            {
                "chunk_id": "00000000-0000-0000-0000-000000000002",
                "seed_chunk_id": "00000000-0000-0000-0000-000000000001",
                "entity_id": "entity-1",
                "entity_label": "Concept",
                "entity_name": "Equality",
                "seed_edge_confidence": 1.0,
                "candidate_edge_confidence": 1.0,
            }
        ]
    )
    result = await hybrid_retrieve(
        session,
        graph,
        "equality",
        5,
        hybrid_settings,
        embedder=FakeEmbedder(),
    )
    assert graph.calls == 1
    assert len(result["results"]) >= 1
    graph_hits = [row for row in result["results"] if "graph" in row["evidence_sources"]]
    assert graph_hits
    assert graph_hits[0]["graph_context"] is not None


async def test_duplicate_paths_deduped(
    session: AsyncSession,
    hybrid_settings: Settings,
) -> None:
    await _seed_db(session)
    row = {
        "chunk_id": "00000000-0000-0000-0000-000000000002",
        "seed_chunk_id": "00000000-0000-0000-0000-000000000001",
        "entity_id": "entity-1",
        "entity_label": "Concept",
        "entity_name": "Equality",
        "seed_edge_confidence": 1.0,
        "candidate_edge_confidence": 1.0,
    }
    graph = FakeGraphClient([row, row])
    result = await hybrid_retrieve(
        session, graph, "equality", 5, hybrid_settings, embedder=FakeEmbedder()
    )
    target = next(
        item
        for item in result["results"]
        if item["chunk_id"] == "00000000-0000-0000-0000-000000000002"
    )
    assert target["graph_score"] == pytest.approx(0.5, abs=1e-6)


async def test_entity_once_in_graph_context(
    session: AsyncSession,
    hybrid_settings: Settings,
) -> None:
    await _seed_db(session)
    graph = FakeGraphClient(
        [
            {
                "chunk_id": "00000000-0000-0000-0000-000000000002",
                "seed_chunk_id": "00000000-0000-0000-0000-000000000001",
                "entity_id": "entity-1",
                "entity_label": "Concept",
                "entity_name": "Equality",
                "seed_edge_confidence": 1.0,
                "candidate_edge_confidence": 1.0,
            },
            {
                "chunk_id": "00000000-0000-0000-0000-000000000002",
                "seed_chunk_id": "00000000-0000-0000-0000-000000000001",
                "entity_id": "entity-1",
                "entity_label": "Concept",
                "entity_name": "Equality",
                "seed_edge_confidence": 1.0,
                "candidate_edge_confidence": 1.0,
            },
        ]
    )
    result = await hybrid_retrieve(
        session, graph, "equality", 5, hybrid_settings, embedder=FakeEmbedder()
    )
    hit = next(
        item
        for item in result["results"]
        if item["chunk_id"] == "00000000-0000-0000-0000-000000000002"
    )
    assert len(hit["graph_context"]["entities"]) == 1


async def test_empty_dense_skips_neo4j(
    session: AsyncSession,
    hybrid_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.retrieval.hybrid.search_index_rows",
        lambda *_args, **_kwargs: [],
    )
    graph = FakeGraphClient()
    result = await hybrid_retrieve(
        session,
        graph,
        "equality",
        5,
        hybrid_settings,
        embedder=FakeEmbedder(),
    )
    assert result["results"] == []
    assert graph.calls == 0


async def test_empty_graph_returns_dense(
    session: AsyncSession,
    hybrid_settings: Settings,
) -> None:
    await _seed_db(session)
    graph = FakeGraphClient([])
    result = await hybrid_retrieve(
        session, graph, "equality", 5, hybrid_settings, embedder=FakeEmbedder()
    )
    assert result["fallback"] is None
    assert any("dense" in row["evidence_sources"] for row in result["results"])
    assert all(row["graph_score"] == 0 for row in result["results"])


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (GraphError("down"), "neo4j_unavailable"),
        (RuntimeError("boom"), "neo4j_query_failed"),
    ],
)
async def test_neo4j_failures_dense_fallback(
    session: AsyncSession,
    hybrid_settings: Settings,
    error: Exception,
    reason: str,
) -> None:
    await _seed_db(session)
    graph = FakeGraphClient(error=error)
    result = await hybrid_retrieve(
        session, graph, "equality", 5, hybrid_settings, embedder=FakeEmbedder()
    )
    assert result["fallback"] == "dense_only"
    assert result["fallback_reason"] == reason
    assert result["results"]
    assert all(row["graph_score"] == 0 for row in result["results"])


async def test_neo4j_timeout_dense_fallback(
    session: AsyncSession,
    hybrid_settings: Settings,
) -> None:
    await _seed_db(session)

    class SlowGraph(FakeGraphClient):
        async def expand_supported_chunks(self, seed_ids: list[str], max_paths: int) -> list[dict]:
            import asyncio

            await asyncio.sleep(5)
            return []

    object.__setattr__(hybrid_settings, "hybrid_graph_timeout_seconds", 0.01)
    result = await hybrid_retrieve(
        session,
        SlowGraph(),
        "equality",
        5,
        hybrid_settings,
        embedder=FakeEmbedder(),
    )
    assert result["fallback_reason"] == "neo4j_timeout"


async def test_malformed_graph_rows_retained_valid(
    session: AsyncSession,
    hybrid_settings: Settings,
) -> None:
    await _seed_db(session)
    graph = FakeGraphClient(
        [
            {"bad": "row"},
            {
                "chunk_id": "00000000-0000-0000-0000-000000000002",
                "seed_chunk_id": "00000000-0000-0000-0000-000000000001",
                "entity_id": "entity-1",
                "entity_label": "Concept",
                "entity_name": "Equality",
                "seed_edge_confidence": 1.0,
                "candidate_edge_confidence": 1.0,
            },
        ]
    )
    result = await hybrid_retrieve(
        session, graph, "equality", 5, hybrid_settings, embedder=FakeEmbedder()
    )
    assert any(
        item["chunk_id"] == "00000000-0000-0000-0000-000000000002" for item in result["results"]
    )


async def test_missing_postgres_chunk_warning(
    session: AsyncSession,
    hybrid_settings: Settings,
) -> None:
    graph = FakeGraphClient(
        [
            {
                "chunk_id": "00000000-0000-0000-0000-000000000002",
                "seed_chunk_id": "00000000-0000-0000-0000-000000000001",
                "entity_id": "entity-1",
                "entity_label": "Concept",
                "entity_name": "Equality",
                "seed_edge_confidence": 1.0,
                "candidate_edge_confidence": 1.0,
            }
        ]
    )
    result = await hybrid_retrieve(
        session, graph, "equality", 5, hybrid_settings, embedder=FakeEmbedder()
    )
    assert any(w.startswith("omitted_missing_chunk:") for w in result["warnings"])


async def test_single_postgres_batch_query(
    session: AsyncSession,
    hybrid_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _seed_db(session)
    calls = 0
    from app.retrieval import evidence as evidence_module

    real_loader = evidence_module.load_chunks_by_ids

    async def counted_loader(*args, **kwargs):
        nonlocal calls
        calls += 1
        return await real_loader(*args, **kwargs)

    monkeypatch.setattr("app.retrieval.hybrid.load_chunks_by_ids", counted_loader)
    graph = FakeGraphClient([])
    await hybrid_retrieve(session, graph, "equality", 5, hybrid_settings, embedder=FakeEmbedder())
    assert calls == 1


async def test_graph_max_hops_lt_two_skips_graph(
    session: AsyncSession,
    hybrid_settings: Settings,
) -> None:
    await _seed_db(session)
    object.__setattr__(hybrid_settings, "graph_max_hops", 1)
    graph = FakeGraphClient(
        [
            {
                "chunk_id": "00000000-0000-0000-0000-000000000002",
                "seed_chunk_id": "00000000-0000-0000-0000-000000000001",
                "entity_id": "entity-1",
                "entity_label": "Concept",
                "entity_name": "Equality",
                "seed_edge_confidence": 1.0,
                "candidate_edge_confidence": 1.0,
            }
        ]
    )
    result = await hybrid_retrieve(
        session, graph, "equality", 5, hybrid_settings, embedder=FakeEmbedder()
    )
    assert graph.calls == 0
    assert all(row["graph_score"] == 0 for row in result["results"])


async def test_final_results_respect_top_k(
    session: AsyncSession,
    hybrid_settings: Settings,
) -> None:
    await _seed_db(session)
    result = await hybrid_retrieve(
        session, FakeGraphClient([]), "equality", 1, hybrid_settings, embedder=FakeEmbedder()
    )
    assert len(result["results"]) == 1


async def test_seeds_survive_graph_candidate_cap(
    session: AsyncSession,
    hybrid_settings: Settings,
) -> None:
    await _seed_db(session)
    object.__setattr__(hybrid_settings, "hybrid_max_graph_candidates", 1)
    rows = [
        {
            "chunk_id": f"00000000-0000-0000-0000-00000000{idx:04d}",
            "seed_chunk_id": "00000000-0000-0000-0000-000000000001",
            "entity_id": f"entity-{idx}",
            "entity_label": "Concept",
            "entity_name": f"E{idx}",
            "seed_edge_confidence": 1.0,
            "candidate_edge_confidence": 1.0,
        }
        for idx in range(2, 30)
    ]
    result = await hybrid_retrieve(
        session,
        FakeGraphClient(rows),
        "equality",
        25,
        hybrid_settings,
        embedder=FakeEmbedder(),
    )
    seed_ids = {row["chunk_id"] for row in result["results"] if "dense" in row["evidence_sources"]}
    assert "00000000-0000-0000-0000-000000000001" in seed_ids
    graph_only = [
        row
        for row in result["results"]
        if "graph" in row["evidence_sources"] and "dense" not in row["evidence_sources"]
    ]
    assert len(graph_only) <= 1


def _bridge_row(
    chunk_id: str,
    *,
    seed: str = "00000000-0000-0000-0000-000000000001",
    entity: str = "entity-1",
) -> dict[str, Any]:
    return {
        "chunk_id": chunk_id,
        "seed_chunk_id": seed,
        "entity_id": entity,
        "entity_label": "Concept",
        "entity_name": "Equality",
        "seed_edge_confidence": 1.0,
        "candidate_edge_confidence": 1.0,
    }


async def test_single_query_embedding_is_reused(
    session: AsyncSession,
    hybrid_settings: Settings,
) -> None:
    await _seed_db(session)

    class CountingEmbedder(FakeEmbedder):
        def __init__(self) -> None:
            self.calls = 0

        def embed(self, texts: list[str]) -> Any:
            self.calls += 1
            return super().embed(texts)

    embedder = CountingEmbedder()
    await hybrid_retrieve(
        session,
        FakeGraphClient([_bridge_row("00000000-0000-0000-0000-000000000002")]),
        "equality",
        5,
        hybrid_settings,
        embedder=embedder,
    )
    assert embedder.calls == 1


async def test_empty_dense_skips_postgres(
    session: AsyncSession,
    hybrid_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.retrieval.hybrid.search_index_rows",
        lambda *_args, **_kwargs: [],
    )
    calls = 0

    async def counted_loader(*_args: Any, **_kwargs: Any) -> dict:
        nonlocal calls
        calls += 1
        return {}

    monkeypatch.setattr("app.retrieval.hybrid.load_chunks_by_ids", counted_loader)
    result = await hybrid_retrieve(
        session,
        FakeGraphClient(),
        "equality",
        5,
        hybrid_settings,
        embedder=FakeEmbedder(),
    )
    assert result["results"] == []
    assert calls == 0


async def test_graph_only_backfill_is_not_a_dense_match(
    session: AsyncSession,
    hybrid_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _seed_db(session)
    monkeypatch.setattr(
        "app.retrieval.hybrid.search_index_rows",
        lambda *_args, **_kwargs: [
            {
                "rank": 1,
                "score": 1.0,
                "chunk_id": "00000000-0000-0000-0000-000000000001",
                "faiss_row": 0,
            }
        ],
    )
    result = await hybrid_retrieve(
        session,
        FakeGraphClient([_bridge_row("00000000-0000-0000-0000-000000000002")]),
        "equality",
        5,
        hybrid_settings,
        embedder=FakeEmbedder(),
    )
    graph_only = next(
        item
        for item in result["results"]
        if item["chunk_id"] == "00000000-0000-0000-0000-000000000002"
    )
    assert graph_only["dense_rank"] is None
    assert graph_only["dense_matched"] is False
    assert graph_only["evidence_sources"] == ["graph"]
    assert graph_only["dense_score"] == pytest.approx(0.0, abs=1e-6)
    seed = next(
        item
        for item in result["results"]
        if item["chunk_id"] == "00000000-0000-0000-0000-000000000001"
    )
    assert seed["dense_matched"] is True
    assert seed["dense_rank"] == 1


async def test_graph_candidate_missing_faiss_embedding(
    session: AsyncSession,
    hybrid_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _seed_db(session)
    monkeypatch.setattr(
        "app.retrieval.hybrid.search_index_rows",
        lambda *_args, **_kwargs: [
            {
                "rank": 1,
                "score": 1.0,
                "chunk_id": "00000000-0000-0000-0000-000000000001",
                "faiss_row": 0,
            }
        ],
    )
    missing = "00000000-0000-0000-0000-000000000099"
    result = await hybrid_retrieve(
        session,
        FakeGraphClient([_bridge_row(missing)]),
        "equality",
        5,
        hybrid_settings,
        embedder=FakeEmbedder(),
    )
    assert any(w == f"omitted_missing_chunk:{missing}" for w in result["warnings"])
    assert all(item["chunk_id"] != missing for item in result["results"])


async def test_overlap_merges_dense_and_graph_sources(
    session: AsyncSession,
    hybrid_settings: Settings,
) -> None:
    await _seed_db(session)
    result = await hybrid_retrieve(
        session,
        FakeGraphClient([_bridge_row("00000000-0000-0000-0000-000000000002")]),
        "equality",
        5,
        hybrid_settings,
        embedder=FakeEmbedder(),
    )
    overlap = next(
        item
        for item in result["results"]
        if item["chunk_id"] == "00000000-0000-0000-0000-000000000002"
    )
    assert overlap["evidence_sources"] == ["dense", "graph"]
    assert overlap["dense_rank"] == 2
    assert overlap["graph_score"] == pytest.approx(0.5, abs=1e-6)


async def test_seed_top_k_sizing_rule(
    session: AsyncSession,
    hybrid_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _seed_db(session)
    captured: dict[str, int] = {}
    from app.retrieval.index import search_index_rows as real_search

    def capture_search(index: Any, metadata: dict, query_vector: Any, top_k: int) -> list:
        captured["top_k"] = top_k
        return real_search(index, metadata, query_vector, top_k)

    monkeypatch.setattr("app.retrieval.hybrid.search_index_rows", capture_search)
    await hybrid_retrieve(
        session, FakeGraphClient([]), "equality", 1, hybrid_settings, embedder=FakeEmbedder()
    )
    assert captured["top_k"] == min(
        hybrid_settings.retrieval_max_top_k,
        max(1, hybrid_settings.hybrid_dense_seed_top_k),
    )


async def test_path_cap_applied_to_graph_rows(
    session: AsyncSession,
    hybrid_settings: Settings,
) -> None:
    await _seed_db(session)
    object.__setattr__(hybrid_settings, "hybrid_max_paths", 1)
    rows = [
        _bridge_row(
            "00000000-0000-0000-0000-000000000002",
            entity=f"entity-{idx}",
        )
        for idx in range(5)
    ]
    graph = FakeGraphClient(rows)
    result = await hybrid_retrieve(
        session, graph, "equality", 5, hybrid_settings, embedder=FakeEmbedder()
    )
    assert graph.calls == 1
    overlap = next(
        item
        for item in result["results"]
        if item["chunk_id"] == "00000000-0000-0000-0000-000000000002"
    )
    assert overlap["graph_score"] == pytest.approx(0.5, abs=1e-6)


async def test_neo4j_service_unavailable_is_classified(
    session: AsyncSession,
    hybrid_settings: Settings,
) -> None:
    await _seed_db(session)

    class ServiceUnavailable(Exception):
        pass

    ServiceUnavailable.__module__ = "neo4j.exceptions"
    graph = FakeGraphClient(error=ServiceUnavailable("offline"))
    result = await hybrid_retrieve(
        session, graph, "equality", 5, hybrid_settings, embedder=FakeEmbedder()
    )
    assert result["fallback"] == "dense_only"
    assert result["fallback_reason"] == "neo4j_unavailable"
