"""Regression tests for Phase 4 Step 6: Retrieval Eligibility & Post-FAISS Cleanup.

Covers:
1. READY documents remain retrievable in dense and hybrid retrieval.
2. FAILED, PROCESSING, DISABLED, and missing documents are strictly excluded.
3. Downstream stage failure (Stage 6, 7, 8) prunes document vectors from FAISS.
4. Cleanup failure preserves the original pipeline exception and does not mark document READY.
5. Unrelated document vectors remain intact when another document's vectors are pruned.
6. Empty eligible results are handled cleanly without exceptions.
7. End-to-end ingestion and retrieval behavior remains unchanged for successful READY documents.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.graph.client import Neo4jClient
from app.ingestion.pipeline import IngestionError, run_pipeline
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.enums import (
    DocumentStatus,
    DocumentType,
    ProcessingJobStage,
    ProcessingJobStatus,
)
from app.models.processing_job import ProcessingJob
from app.retrieval.hybrid import hybrid_retrieve
from app.retrieval.index import (
    load_index,
    remove_document_from_index,
    save_index,
    update_index_incremental,
)
from app.retrieval.service import retrieve, retrieve_ready_chunks
from tests.helpers import make_minimal_legal_pdf


# ── Test Doubles ───────────────────────────────────────────────────────────────


class DeterministicEmbedder:
    """Test double: Generates deterministic 2D L2-normalized embeddings for fast isolated testing."""

    pooling_method = "attention_mask_mean_pooling"
    normalization = "l2"

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors: list[list[float]] = []
        for text in texts:
            if "equality" in text.lower() or "article 14" in text.lower():
                vectors.append([1.0, 0.0])
            elif "life" in text.lower() or "article 21" in text.lower():
                vectors.append([0.0, 1.0])
            else:
                vectors.append([0.70710678, 0.70710678])
        return np.asarray(vectors, dtype=np.float32)


class MockNeo4jClient(Neo4jClient):
    """Test double: Simulates Neo4j client without network connections."""

    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows or []
        self.calls = 0

    async def expand_supported_chunks(self, seed_ids: list[str], max_paths: int) -> list[dict[str, Any]]:
        self.calls += 1
        return self.rows

    async def replace_document_graph(self, payload: dict[str, Any]) -> None:
        self.calls += 1

    async def close(self) -> None:
        pass


@pytest.fixture
def isolated_settings(tmp_path: Path) -> Settings:
    settings = get_settings()
    snapshot = settings.model_dump()
    object.__setattr__(settings, "data_dir", str(tmp_path))
    object.__setattr__(settings, "vector_index_name", "test_chunks")
    object.__setattr__(settings, "embedding_model_name", "test-model")
    yield settings
    for key, value in snapshot.items():
        object.__setattr__(settings, key, value)


# ── Test 1: READY document remains retrievable ─────────────────────────────────


async def test_ready_document_remains_retrievable(
    session: AsyncSession,
    isolated_settings: Settings,
    tmp_path: Path,
) -> None:
    embedder = DeterministicEmbedder()
    doc = Document(
        title="Valid Act",
        type=DocumentType.ACT,
        source="test",
        status=DocumentStatus.READY,
    )
    session.add(doc)
    await session.flush()

    chunk_id = uuid4()
    chunk = Chunk(
        id=chunk_id,
        document_id=doc.id,
        chunk_index=0,
        text="All citizens have equality before the law under Article 14.",
        char_count=57,
        hierarchy={"act": "Valid Act"},
        citation_ref="Section 14",
    )
    session.add(chunk)
    await session.commit()

    chunk_record = {
        "chunk_id": str(chunk_id),
        "document_id": str(doc.id),
        "document_version_id": None,
        "chunk_index": 0,
        "text": chunk.text,
        "page_start": 1,
        "page_end": 1,
        "hierarchy": chunk.hierarchy,
        "citation_ref": chunk.citation_ref,
        "document_title": doc.title,
    }
    vectors = embedder.embed([chunk.text])
    save_index(
        data_dir=tmp_path,
        index_name=isolated_settings.vector_index_name,
        vectors=vectors,
        chunk_records=[chunk_record],
        model_name=isolated_settings.embedding_model_name,
        pooling_method=embedder.pooling_method,
        max_tokens=isolated_settings.embedding_max_tokens,
    )

    # 1. Test retrieve_ready_chunks
    dense_results = await retrieve_ready_chunks(
        session,
        "equality",
        5,
        isolated_settings,
        embedder=embedder,
    )
    assert len(dense_results) == 1
    assert dense_results[0]["chunk_id"] == str(chunk_id)
    assert dense_results[0]["rank"] == 1
    assert dense_results[0]["score"] == pytest.approx(1.0, abs=1e-5)

    # 2. Test hybrid_retrieve
    graph_client = MockNeo4jClient()
    hybrid_res = await hybrid_retrieve(
        session,
        graph_client,
        "equality",
        5,
        isolated_settings,
        embedder=embedder,
    )
    assert len(hybrid_res["results"]) == 1
    assert hybrid_res["results"][0]["chunk_id"] == str(chunk_id)
    assert hybrid_res["results"][0]["rank"] == 1


# ── Test 2: FAILED, PROCESSING, DISABLED, and missing documents excluded ───────


async def test_non_ready_and_missing_documents_excluded_from_dense_retrieval(
    session: AsyncSession,
    isolated_settings: Settings,
    tmp_path: Path,
) -> None:
    embedder = DeterministicEmbedder()

    # Create documents in non-READY statuses
    doc_failed = Document(title="Failed Doc", type=DocumentType.ACT, source="test", status=DocumentStatus.FAILED)
    doc_proc = Document(title="Proc Doc", type=DocumentType.ACT, source="test", status=DocumentStatus.PROCESSING)
    doc_dis = Document(title="Dis Doc", type=DocumentType.ACT, source="test", status=DocumentStatus.DISABLED)
    session.add_all([doc_failed, doc_proc, doc_dis])
    await session.flush()

    missing_doc_id = uuid4()  # Does NOT exist in PostgreSQL

    chunks_data = [
        (doc_failed.id, uuid4(), "equality failed doc chunk"),
        (doc_proc.id, uuid4(), "equality processing doc chunk"),
        (doc_dis.id, uuid4(), "equality disabled doc chunk"),
        (missing_doc_id, uuid4(), "equality missing doc chunk"),
    ]

    for d_id, ch_id, txt in chunks_data:
        if d_id != missing_doc_id:
            session.add(
                Chunk(
                    id=ch_id,
                    document_id=d_id,
                    chunk_index=0,
                    text=txt,
                    char_count=len(txt),
                    hierarchy={},
                    citation_ref="None",
                )
            )
    await session.commit()

    chunk_records = [
        {
            "chunk_id": str(ch_id),
            "document_id": str(d_id),
            "document_version_id": None,
            "chunk_index": 0,
            "text": txt,
            "page_start": 1,
            "page_end": 1,
            "hierarchy": {},
            "citation_ref": "None",
            "document_title": "Doc",
        }
        for d_id, ch_id, txt in chunks_data
    ]
    vectors = embedder.embed([r["text"] for r in chunk_records])
    save_index(
        data_dir=tmp_path,
        index_name=isolated_settings.vector_index_name,
        vectors=vectors,
        chunk_records=chunk_records,
        model_name=isolated_settings.embedding_model_name,
        pooling_method=embedder.pooling_method,
        max_tokens=isolated_settings.embedding_max_tokens,
    )

    # 1. retrieve_ready_chunks MUST return 0 results
    dense_results = await retrieve_ready_chunks(
        session,
        "equality",
        10,
        isolated_settings,
        embedder=embedder,
    )
    assert dense_results == []

    # 2. hybrid_retrieve MUST return 0 results
    graph_client = MockNeo4jClient()
    hybrid_res = await hybrid_retrieve(
        session,
        graph_client,
        "equality",
        10,
        isolated_settings,
        embedder=embedder,
    )
    assert hybrid_res["results"] == []

    # 3. retrieve with explicit empty eligible_document_ids MUST return 0 results
    filtered_retrieve = retrieve(
        "equality",
        10,
        isolated_settings,
        embedder=embedder,
        eligible_document_ids=set(),
    )
    assert filtered_retrieve == []


# ── Test 3: Downstream stage failure removes vectors on cleanup success ────────


async def test_downstream_stage_failure_removes_vectors_on_cleanup_success(
    session: AsyncSession,
    isolated_settings: Settings,
    tmp_path: Path,
) -> None:
    embedder = DeterministicEmbedder()
    pdf_bytes = make_minimal_legal_pdf()

    doc = Document(
        title="Failing Document",
        type=DocumentType.ACT,
        source="test",
        status=DocumentStatus.REGISTERED,
    )
    session.add(doc)
    await session.commit()

    # Simulate Stage 8 (Graph Population) failure after Stage 5 (FAISS) succeeded
    failing_graph = MockNeo4jClient()
    failing_graph.replace_document_graph = AsyncMock(side_effect=RuntimeError("Neo4j disk full"))

    with pytest.raises(IngestionError) as exc_info:
        await run_pipeline(
            db=session,
            document_id=doc.id,
            pdf_bytes=pdf_bytes,
            settings=isolated_settings,
            embedder=embedder,
            graph_client=failing_graph,
        )

    assert exc_info.value.stage == ProcessingJobStage.GRAPH_POPULATION
    assert "Neo4j disk full" in str(exc_info.value)

    # Verify PostgreSQL state: document status is FAILED and job is FAILED
    await session.refresh(doc)
    assert doc.status == DocumentStatus.FAILED

    job_graph = (
        await session.execute(
            select(ProcessingJob).where(
                ProcessingJob.document_id == doc.id,
                ProcessingJob.stage == ProcessingJobStage.GRAPH_POPULATION,
            )
        )
    ).scalar_one()
    assert job_graph.status == ProcessingJobStatus.FAILED

    # Verify FAISS cleanup: vectors were pruned from index
    index_path = tmp_path / "indexes" / isolated_settings.vector_index_name / "index.faiss"
    if index_path.exists():
        index, meta = load_index(tmp_path, isolated_settings.vector_index_name)
        doc_ids_in_index = {c["document_id"] for c in meta.get("chunks", [])}
        assert str(doc.id) not in doc_ids_in_index


# ── Test 4: Cleanup failure preserves original error and does not mark READY ───


async def test_cleanup_failure_preserves_original_exception_and_does_not_mark_ready(
    session: AsyncSession,
    isolated_settings: Settings,
    tmp_path: Path,
) -> None:
    embedder = DeterministicEmbedder()
    pdf_bytes = make_minimal_legal_pdf()

    doc = Document(
        title="Double Failing Document",
        type=DocumentType.ACT,
        source="test",
        status=DocumentStatus.REGISTERED,
    )
    session.add(doc)
    await session.commit()

    failing_graph = MockNeo4jClient()
    failing_graph.replace_document_graph = AsyncMock(side_effect=RuntimeError("Original graph failure"))

    # Mock cleanup to fail
    with patch(
        "app.ingestion.pipeline.remove_document_from_index",
        AsyncMock(side_effect=IOError("Corrupt disk during cleanup")),
    ):
        with pytest.raises(IngestionError) as exc_info:
            await run_pipeline(
                db=session,
                document_id=doc.id,
                pdf_bytes=pdf_bytes,
                settings=isolated_settings,
                embedder=embedder,
                graph_client=failing_graph,
            )

    # 1. Primary IngestionError is NOT masked
    assert exc_info.value.stage == ProcessingJobStage.GRAPH_POPULATION
    assert "Original graph failure" in str(exc_info.value)

    # 2. Document is strictly FAILED in PostgreSQL, NEVER READY
    await session.refresh(doc)
    assert doc.status == DocumentStatus.FAILED

    # 3. Defensive eligibility check protects retrieval even if vectors remain in FAISS
    results = await retrieve_ready_chunks(
        session,
        "equality",
        10,
        isolated_settings,
        embedder=embedder,
    )
    assert str(doc.id) not in {r["document_id"] for r in results}


# ── Test 5: Unrelated document vectors remain intact during cleanup ───────────


async def test_unrelated_document_vectors_remain_intact(
    session: AsyncSession,
    isolated_settings: Settings,
    tmp_path: Path,
) -> None:
    embedder = DeterministicEmbedder()

    doc_a_id = uuid4()
    doc_b_id = uuid4()

    chunk_a_id = uuid4()
    chunk_b_id = uuid4()

    records = [
        {
            "chunk_id": str(chunk_a_id),
            "document_id": str(doc_a_id),
            "document_version_id": None,
            "chunk_index": 0,
            "text": "citizens equality act",
            "page_start": 1,
            "page_end": 1,
            "hierarchy": {},
            "citation_ref": "Doc A",
            "document_title": "Doc A",
        },
        {
            "chunk_id": str(chunk_b_id),
            "document_id": str(doc_b_id),
            "document_version_id": None,
            "chunk_index": 0,
            "text": "unrelated life act",
            "page_start": 1,
            "page_end": 1,
            "hierarchy": {},
            "citation_ref": "Doc B",
            "document_title": "Doc B",
        },
    ]

    vectors = embedder.embed([r["text"] for r in records])
    save_index(
        data_dir=tmp_path,
        index_name=isolated_settings.vector_index_name,
        vectors=vectors,
        chunk_records=records,
        model_name=isolated_settings.embedding_model_name,
        pooling_method=embedder.pooling_method,
        max_tokens=isolated_settings.embedding_max_tokens,
    )

    # Remove Doc B from index
    removed = await remove_document_from_index(
        data_dir=tmp_path,
        index_name=isolated_settings.vector_index_name,
        document_id=str(doc_b_id),
    )
    assert removed is True

    # Verify index contains ONLY Doc A, with valid FAISS vector count and metadata mapping
    index, metadata = load_index(tmp_path, isolated_settings.vector_index_name)
    assert index.ntotal == 1
    assert len(metadata["chunks"]) == 1
    assert metadata["chunks"][0]["document_id"] == str(doc_a_id)
    assert metadata["chunks"][0]["chunk_id"] == str(chunk_a_id)

    # Calling remove again is safely idempotent and returns False
    second_removal = await remove_document_from_index(
        data_dir=tmp_path,
        index_name=isolated_settings.vector_index_name,
        document_id=str(doc_b_id),
    )
    assert second_removal is False


# ── Test 6: Empty eligible results are handled without exception ───────────────


async def test_empty_eligible_results_handled_without_exception(
    session: AsyncSession,
    isolated_settings: Settings,
    tmp_path: Path,
) -> None:
    embedder = DeterministicEmbedder()

    # Index has chunks, but PostgreSQL has NO documents at all
    records = [
        {
            "chunk_id": str(uuid4()),
            "document_id": str(uuid4()),
            "document_version_id": None,
            "chunk_index": 0,
            "text": "equality",
            "page_start": 1,
            "page_end": 1,
            "hierarchy": {},
            "citation_ref": "None",
            "document_title": "Orphan Doc",
        }
    ]
    vectors = embedder.embed(["equality"])
    save_index(
        data_dir=tmp_path,
        index_name=isolated_settings.vector_index_name,
        vectors=vectors,
        chunk_records=records,
        model_name=isolated_settings.embedding_model_name,
        pooling_method=embedder.pooling_method,
        max_tokens=isolated_settings.embedding_max_tokens,
    )

    # 1. retrieve_ready_chunks
    res_dense = await retrieve_ready_chunks(
        session,
        "equality",
        5,
        isolated_settings,
        embedder=embedder,
    )
    assert res_dense == []

    # 2. hybrid_retrieve
    res_hybrid = await hybrid_retrieve(
        session,
        MockNeo4jClient(),
        "equality",
        5,
        isolated_settings,
        embedder=embedder,
    )
    assert res_hybrid["results"] == []
    assert res_hybrid["mode"] == "hybrid"


# ── Test 7: Successful pipeline keeps document READY and retrievable ───────────


async def test_successful_pipeline_marks_ready_and_retrievable(
    session: AsyncSession,
    isolated_settings: Settings,
    tmp_path: Path,
) -> None:
    embedder = DeterministicEmbedder()
    pdf_bytes = make_minimal_legal_pdf()

    doc = Document(
        title="Successful Act",
        type=DocumentType.ACT,
        source="test",
        status=DocumentStatus.REGISTERED,
    )
    session.add(doc)
    await session.commit()

    graph_client = MockNeo4jClient()

    chunks = await run_pipeline(
        db=session,
        document_id=doc.id,
        pdf_bytes=pdf_bytes,
        settings=isolated_settings,
        embedder=embedder,
        graph_client=graph_client,
    )
    assert len(chunks) > 0

    await session.refresh(doc)
    assert doc.status == DocumentStatus.READY

    # Verify document is retrievable via retrieve_ready_chunks
    results = await retrieve_ready_chunks(
        session,
        "constitution",
        5,
        isolated_settings,
        embedder=embedder,
    )
    assert len(results) >= 1
    assert any(r["document_id"] == str(doc.id) for r in results)
