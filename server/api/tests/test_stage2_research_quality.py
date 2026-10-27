"""Stage 2 Research Quality Regression Tests.

Validates:
1. Generic entity-aware relevance boost for multi-entity queries (Maneka Gandhi + Article 21).
2. Unrelated queries do not receive false entity boosts.
3. Missing evidence queries return insufficient_evidence: True cleanly.
4. Valid citations are grounded and verified against evidence ranks.
5. Graph retrieval failures/timeouts fallback gracefully to dense-only retrieval.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import Document
from app.models.chunk import Chunk
from app.models.enums import DocumentStatus, DocumentType
from app.qa.provider import LLMProvider
from app.rag.evidence_fusion import calculate_entity_boost, fuse_and_rank_evidence
from app.rag.pipeline import execute_graphrag_pipeline
from app.rag.query_analysis import analyze_query


class MockLLM(LLMProvider):
    def __init__(self, response_json: dict[str, Any] | None = None) -> None:
        self.response_json = response_json or {
            "answer": "Under Article 21, the procedure established by law must be just, fair, and reasonable [1].",
            "insufficient_evidence": False,
            "citations": [
                {"marker": 1, "evidence_rank": 1},
            ],
        }
        self.calls = 0

    async def generate(
        self,
        system_message: str,
        user_message: str,
        timeout_seconds: float,
        max_output_tokens: int,
    ) -> str:
        self.calls += 1
        return json.dumps(self.response_json)


class FailingGraphClient:
    """Mock Neo4j client that simulates timeout or connection failure."""
    def __init__(self, failure_type: str = "timeout") -> None:
        self.failure_type = failure_type
        self.settings = type("MockSettings", (), {
            "neo4j_database": "neo4j",
            "graph_max_nodes": 30,
            "graph_max_hops": 2,
        })()

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

    async def expand_supported_chunks(self, seed_ids: list[str], max_paths: int) -> list[dict[str, Any]]:
        if self.failure_type == "timeout":
            raise asyncio.TimeoutError("Neo4j expansion timed out after 6.0s")
        raise ConnectionError("Neo4j connection refused")


def test_entity_boost_calculation_generic() -> None:
    """Test generic entity boost logic without hardcoded queries."""
    detected = [
        {"id": "judgment:maneka_gandhi_v_union_of_india", "label": "Judgment", "name": "Maneka Gandhi v. Union of India"},
        {"id": "article:constitution_of_india:21", "label": "Article", "name": "Article 21"},
    ]

    # Chunk from Maneka Gandhi document
    boost_judgment = calculate_entity_boost(
        doc_title="Maneka Gandhi v. Union of India",
        citation_ref="1978 AIR 597",
        hierarchy={"court": "Supreme Court"},
        detected_entities=detected,
    )
    assert boost_judgment >= 1.25

    # Chunk from Constitution Article 21
    boost_article = calculate_entity_boost(
        doc_title="Constitution of India",
        citation_ref="Article 21",
        hierarchy={"part": "III", "article": "21"},
        detected_entities=detected,
    )
    assert boost_article >= 1.15

    # Completely unrelated document chunk (e.g. Income Tax Act)
    boost_unrelated = calculate_entity_boost(
        doc_title="Income Tax Act 1961",
        citation_ref="Section 80C",
        hierarchy={"chapter": "VIA"},
        detected_entities=detected,
    )
    assert boost_unrelated == 1.0


def test_unrelated_query_no_false_boost() -> None:
    """An unrelated query (e.g. CrPC Section 437) does NOT boost Maneka Gandhi chunks."""
    unrelated_entities = [
        {"id": "section:crpc:437", "label": "Section", "name": "Section 437"},
        {"id": "act:crpc", "label": "Act", "name": "Code of Criminal Procedure"},
    ]

    boost_maneka = calculate_entity_boost(
        doc_title="Maneka Gandhi v. Union of India",
        citation_ref="1978 AIR 597",
        hierarchy={},
        detected_entities=unrelated_entities,
    )
    assert boost_maneka == 1.0

    boost_crpc = calculate_entity_boost(
        doc_title="Code of Criminal Procedure, 1973",
        citation_ref="Section 437",
        hierarchy={"section": "437"},
        detected_entities=unrelated_entities,
    )
    assert boost_crpc >= 1.25


@pytest.mark.asyncio
async def test_maneka_gandhi_article_21_fusion_and_ranking(session: AsyncSession) -> None:
    """Test that entity boost lifts Maneka Gandhi into top evidence for the landmark query."""
    doc_const = Document(
        id=uuid4(),
        title="Constitution of India",
        type=DocumentType.CONSTITUTION,
        source="test",
        status=DocumentStatus.READY,
    )
    doc_maneka = Document(
        id=uuid4(),
        title="Maneka Gandhi v. Union of India",
        type=DocumentType.JUDGMENT,
        source="test",
        status=DocumentStatus.READY,
    )
    session.add_all([doc_const, doc_maneka])
    await session.flush()

    chunk_const = Chunk(
        id=uuid4(),
        document_id=doc_const.id,
        chunk_index=0,
        text="No person shall be deprived of his life or personal liberty except according to procedure established by law.",
        char_count=len("No person shall be deprived of his life or personal liberty except according to procedure established by law."),
        citation_ref="Article 21",
        hierarchy={"article": "21"},
    )
    chunk_maneka = Chunk(
        id=uuid4(),
        document_id=doc_maneka.id,
        chunk_index=0,
        text="Procedure under Article 21 must be right, just, fair and reasonable, not arbitrary or fanciful.",
        char_count=len("Procedure under Article 21 must be right, just, fair and reasonable, not arbitrary or fanciful."),
        citation_ref="1978 AIR 597",
        hierarchy={"judgment": "Maneka Gandhi"},
    )
    session.add_all([chunk_const, chunk_maneka])
    await session.commit()

    # Suppose FAISS returned constitution chunk at rank 1 (score 0.72) and maneka at rank 4 (score 0.65)
    dense_candidates = [
        {"chunk_id": str(chunk_const.id), "score": 0.72},
        {"chunk_id": str(uuid4()), "score": 0.70},  # irrelevant filler chunk
        {"chunk_id": str(uuid4()), "score": 0.68},  # irrelevant filler chunk
        {"chunk_id": str(chunk_maneka.id), "score": 0.65},
    ]

    all_chunks = {
        str(chunk_const.id): {
            "document_id": str(doc_const.id),
            "document_title": doc_const.title,
            "document_type": "CONSTITUTION",
            "citation_ref": "Article 21",
            "hierarchy": {"article": "21"},
            "text": chunk_const.text,
        },
        str(chunk_maneka.id): {
            "document_id": str(doc_maneka.id),
            "document_title": doc_maneka.title,
            "document_type": "JUDGMENT",
            "citation_ref": "1978 AIR 597",
            "hierarchy": {},
            "text": chunk_maneka.text,
        },
    }

    qa = analyze_query("How did Maneka Gandhi expand Article 21?")
    fused = fuse_and_rank_evidence(
        dense_candidates=dense_candidates,
        graph_candidate_chunks={},
        all_chunks_by_id=all_chunks,
        strategy="vector_only",
        top_k=5,
        detected_entities=qa.detected_entities,
    )

    # Both chunks must be in top 2 ranks
    top_titles = [item.document_title for item in fused[:2]]
    assert "Maneka Gandhi v. Union of India" in top_titles
    assert "Constitution of India" in top_titles


@pytest.mark.asyncio
async def test_graph_retrieval_failure_fallback(session: AsyncSession) -> None:
    """Test that graph timeout or connection failure falls back gracefully to dense retrieval."""
    doc = Document(
        id=uuid4(),
        title="Constitution of India",
        type=DocumentType.CONSTITUTION,
        source="test",
        status=DocumentStatus.READY,
    )
    session.add(doc)
    await session.flush()

    chunk = Chunk(
        id=uuid4(),
        document_id=doc.id,
        chunk_index=0,
        text="Article 21 guarantees right to life and personal liberty.",
        char_count=len("Article 21 guarantees right to life and personal liberty."),
        citation_ref="Article 21",
        hierarchy={"article": "21"},
    )
    session.add(chunk)
    await session.commit()

    settings = Settings(
        app_env="test",
        session_secret="test-secret-minimum-32-chars-long-1234",
        hybrid_graph_timeout_seconds=0.1,  # short timeout to test fallback
        qa_max_context_chars=24000,
    )

    failing_graph = FailingGraphClient(failure_type="timeout")
    mock_llm = MockLLM()

    # Monkeypatch vector search so test does not require full onnx embedder
    import app.rag.pipeline as p
    orig_embed = p.embed_query_vector
    orig_search = p.search_index_rows
    p.embed_query_vector = lambda *args, **kwargs: (None, None, [0.1] * 768, None)
    p.search_index_rows = lambda *args, **kwargs: [{"chunk_id": str(chunk.id), "score": 0.85, "rank": 1}]

    try:
        res = await execute_graphrag_pipeline(
            session=session,
            graph_client=failing_graph,  # type: ignore
            query="What does Article 21 guarantee?",
            top_k=5,
            strategy="hybrid",
            settings=settings,
            provider=mock_llm,
        )

        assert res["status"] == "answered"
        assert res["retrieval"].fallback == "dense_only"
        assert res["retrieval"].fallback_reason == "neo4j_timeout"
        assert len(res["citations"]) > 0
        assert res["citation_validation"].verified_count >= 1
    finally:
        p.embed_query_vector = orig_embed
        p.search_index_rows = orig_search


@pytest.mark.asyncio
async def test_missing_evidence_clean_response(session: AsyncSession) -> None:
    """Query with no matching evidence returns insufficient_evidence cleanly."""
    settings = Settings(
        app_env="test",
        session_secret="test-secret-minimum-32-chars-long-1234",
        qa_max_context_chars=24000,
    )
    mock_llm = MockLLM(
        response_json={
            "answer": "Insufficient verified evidence in current legal corpus to provide a grounded answer.",
            "insufficient_evidence": True,
            "citations": [],
        }
    )

    import app.rag.pipeline as p
    orig_search = p.search_index_rows
    # Return empty dense hits
    p.search_index_rows = lambda *args, **kwargs: []

    try:
        res = await execute_graphrag_pipeline(
            session=session,
            graph_client=FailingGraphClient(),  # type: ignore
            query="What does Section 9999 of the Fantasy Realm Act provide?",
            top_k=5,
            strategy="hybrid",
            settings=settings,
            provider=mock_llm,
        )

        assert res["insufficient_evidence"] is True
        assert res["status"] == "insufficient_evidence"
        assert len(res["citations"]) == 0
    finally:
        p.search_index_rows = orig_search
