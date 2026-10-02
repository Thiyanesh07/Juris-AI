"""Phase 14 Integration & Unit tests for GraphRAG Pipeline and Endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.graph.client import GraphError
from app.models import Document
from app.models.chunk import Chunk
from app.models.enums import DocumentType
from app.qa.provider import LLMProvider
from app.qa.service import ask_legal_question
from app.retrieval.index import save_index
from tests.test_retrieval import (
    TEST_MODEL,
    TEST_POOLING,
    FakeEmbedder,
    _configure_settings,
    _records,
)


def _valid_llm_json(answer: str = "According to [1], Article 21 protects life and personal liberty.") -> str:
    return json.dumps(
        {
            "answer": answer,
            "insufficient_evidence": False,
            "citations": [{"marker": 1, "evidence_rank": 1}],
        }
    )


class MockLLMProvider(LLMProvider):
    def __init__(self, answer_text: str | None = None) -> None:
        if answer_text and answer_text.startswith("{"):
            self.answer_text = answer_text
        elif answer_text:
            self.answer_text = _valid_llm_json(answer_text)
        else:
            self.answer_text = _valid_llm_json()
        self.calls = 0

    async def generate(
        self,
        system_message: str,
        user_message: str,
        timeout_seconds: float,
        max_output_tokens: int,
    ) -> str:
        self.calls += 1
        return self.answer_text


class MockFailingLLMProvider(LLMProvider):
    async def generate(
        self,
        system_message: str,
        user_message: str,
        timeout_seconds: float,
        max_output_tokens: int,
    ) -> str:
        return "INVALID_FORMAT_NO_JSON"


class MockNeo4jClient:
    def __init__(self, rows: list[dict[str, Any]] | None = None, error: Exception | None = None):
        self.rows = rows or []
        self.error = error
        self.settings = type("SettingsMock", (), {"neo4j_database": "neo4j", "graph_max_nodes": 30})()

    async def _driver_for_use(self) -> Any:
        return self

    def session(self, **kwargs: Any) -> Any:
        class DummySession:
            async def __aenter__(self) -> DummySession:
                return self

            async def __aexit__(self, *args: Any) -> None:
                pass

            async def run(self, *args: Any, **kwargs: Any) -> Any:
                class DummyResult:
                    def __aiter__(self) -> DummyResult:
                        return self

                    async def __anext__(self) -> Any:
                        raise StopAsyncIteration

                return DummyResult()

        return DummySession()

    async def expand_supported_chunks(self, seed_ids: list[str], max_paths: int) -> list[dict]:
        if self.error:
            raise self.error
        return self.rows

    async def close(self) -> None:
        pass


async def _seed_db(session: AsyncSession) -> None:
    doc = Document(title="Constitution of India", type=DocumentType.CONSTITUTION, source="test")
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
    import numpy as np

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
def p14_settings(tmp_path: Path) -> Settings:
    settings = get_settings()
    snapshot = settings.model_dump()
    _configure_settings(settings, tmp_path)
    _save_index(tmp_path)
    yield settings
    for key, value in snapshot.items():
        object.__setattr__(settings, key, value)


async def test_vector_only_query_works(
    session: AsyncSession,
    p14_settings: Settings,
) -> None:
    await _seed_db(session)
    res = await ask_legal_question(
        session,
        MockNeo4jClient(),
        "What does Article 21 protect?",
        5,
        p14_settings,
        retrieval_strategy="vector_only",
        provider=MockLLMProvider(),
        embedder=FakeEmbedder(),
    )
    assert res.status == "answered"
    assert res.answer is not None
    assert len(res.evidence) >= 1
    assert res.retrieval.mode == "vector_only"


async def test_graph_only_query_works(
    session: AsyncSession,
    p14_settings: Settings,
) -> None:
    await _seed_db(session)
    graph_mock = MockNeo4jClient([
        {
            "chunk_id": "00000000-0000-0000-0000-000000000002",
            "seed_chunk_id": "00000000-0000-0000-0000-000000000001",
            "entity_id": "article:constitution_of_india:21",
            "entity_label": "Article",
            "entity_name": "Article 21",
            "seed_edge_confidence": 1.0,
            "candidate_edge_confidence": 1.0,
        }
    ])
    res = await ask_legal_question(
        session,
        graph_mock,
        "What does Article 21 protect?",
        5,
        p14_settings,
        retrieval_strategy="graph_only",
        provider=MockLLMProvider(),
        embedder=FakeEmbedder(),
    )
    assert res.status == "answered"
    assert len(res.evidence) >= 1


async def test_hybrid_query_works(
    session: AsyncSession,
    p14_settings: Settings,
) -> None:
    await _seed_db(session)
    res = await ask_legal_question(
        session,
        MockNeo4jClient(),
        "What does Article 21 protect?",
        5,
        p14_settings,
        mode="CONSTITUTIONAL",
        retrieval_strategy="hybrid",
        provider=MockLLMProvider(),
        embedder=FakeEmbedder(),
    )
    assert res.status == "answered"
    assert res.graph is not None
    assert len(res.reasoning_steps) >= 4
    assert res.query_analysis is not None


async def test_citation_maps_to_real_chunk(
    session: AsyncSession,
    p14_settings: Settings,
) -> None:
    await _seed_db(session)
    res = await ask_legal_question(
        session,
        MockNeo4jClient(),
        "What does Article 21 protect?",
        5,
        p14_settings,
        provider=MockLLMProvider("Under [1], Article 21 protects life and personal liberty."),
        embedder=FakeEmbedder(),
    )
    assert res.status == "answered"
    assert len(res.citations) == 1
    cit = res.citations[0]
    assert cit.marker == 1
    assert cit.chunk_id == res.evidence[0].chunk_id


async def test_neo4j_failure_handled_gracefully(
    session: AsyncSession,
    p14_settings: Settings,
) -> None:
    await _seed_db(session)
    failing_graph = MockNeo4jClient(error=GraphError("Neo4j offline"))
    res = await ask_legal_question(
        session,
        failing_graph,
        "What does Article 21 protect?",
        5,
        p14_settings,
        provider=MockLLMProvider(),
        embedder=FakeEmbedder(),
    )
    assert res.status == "answered"
    assert res.retrieval.fallback == "dense_only"
    assert res.retrieval.fallback_reason == "neo4j_unavailable"


async def test_llm_failure_handled_gracefully(
    session: AsyncSession,
    p14_settings: Settings,
) -> None:
    await _seed_db(session)
    res = await ask_legal_question(
        session,
        MockNeo4jClient(),
        "What does Article 21 protect?",
        5,
        p14_settings,
        provider=MockFailingLLMProvider(),
        embedder=FakeEmbedder(),
    )
    assert res.status == "insufficient_evidence"
    assert res.insufficient_evidence is True
    assert res.citations == []
