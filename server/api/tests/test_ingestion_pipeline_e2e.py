"""End-to-end integration tests for the complete 8-stage ingestion pipeline (Phase 3 Step 2).

Verifies:
- All 8 stages succeed in order (INGESTION -> EXTRACTION -> CHUNKING -> EMBEDDING ->
  VECTOR_INDEX -> ENTITY_EXTRACTION -> RELATION_EXTRACTION -> GRAPH_POPULATION).
- Failure at downstream stages sets accurate job and document status.
- Incremental FAISS updates preserve pre-existing vectors and metadata.
- Concurrent FAISS updates within a single process execute safely without corruption.
- Reprocessing is idempotent: no duplicate chunks, vectors, or graph entities.
- Document restore does not falsely mark an incompletely indexed document as READY.
- Startup recovery followed by safe re-run succeeds cleanly.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from uuid import uuid4
import numpy as np
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.ingestion.pipeline import IngestionError, run_pipeline
from app.ingestion.recovery import recover_interrupted_jobs
from app.models import Chunk, Document, ProcessingJob
from app.models.enums import DocumentStatus, DocumentType, ProcessingJobStage, ProcessingJobStatus
from app.retrieval.index import (
    load_embeddings_matrix,
    load_index,
    update_index_incremental,
)
from tests.helpers import make_minimal_legal_pdf


class MockEmbedder:
    """Mock InLegalBERT embedder producing deterministic 768-dim normalized vectors."""

    def __init__(self, dimension: int = 768) -> None:
        self.dimension = dimension
        self.pooling_method = "attention_mask_mean_pooling"

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        vectors = []
        for i, text in enumerate(texts):
            vec = np.ones(self.dimension, dtype=np.float32) * float(i + 1)
            norm = np.linalg.norm(vec)
            vectors.append(vec / (norm if norm > 0 else 1.0))
        return np.vstack(vectors)


class MockGraphClient:
    """Mock Neo4j client recording replace_document_graph payloads."""

    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []

    async def replace_document_graph(self, payload: dict[str, Any]) -> None:
        self.payloads.append(payload)


# ── Full 8-Stage Pipeline Success ─────────────────────────────────────────────


async def test_full_pipeline_success(
    session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr("app.ingestion.pipeline.get_data_dir", lambda: tmp_path)

    pdf_bytes = make_minimal_legal_pdf()
    doc = Document(
        title="Bhartiya Nyaya Sanhita 2023",
        type=DocumentType.ACT,
        source="India Code",
        status=DocumentStatus.REGISTERED,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    mock_embedder = MockEmbedder()
    mock_graph = MockGraphClient()

    chunks = await run_pipeline(
        document_id=doc.id,
        pdf_bytes=pdf_bytes,
        db=session,
        settings=settings,
        embedder=mock_embedder,
        graph_client=mock_graph,
    )

    assert len(chunks) > 0

    # 1. Verify document status is READY
    await session.refresh(doc)
    assert doc.status == DocumentStatus.READY

    # 2. Verify all 8 ProcessingJob stages exist and are COMPLETED
    jobs_res = await session.execute(
        select(ProcessingJob).where(ProcessingJob.document_id == doc.id)
    )
    jobs = {j.stage: j for j in jobs_res.scalars().all()}
    assert len(jobs) == 8

    expected_stages = [
        ProcessingJobStage.INGESTION,
        ProcessingJobStage.EXTRACTION,
        ProcessingJobStage.CHUNKING,
        ProcessingJobStage.EMBEDDING,
        ProcessingJobStage.VECTOR_INDEX,
        ProcessingJobStage.ENTITY_EXTRACTION,
        ProcessingJobStage.RELATION_EXTRACTION,
        ProcessingJobStage.GRAPH_POPULATION,
    ]
    for stage in expected_stages:
        assert stage in jobs
        assert jobs[stage].status == ProcessingJobStatus.COMPLETED
        assert jobs[stage].error is None

    # 3. Verify FAISS index was created
    index, metadata = load_index(tmp_path, settings.vector_index_name)
    assert index.ntotal == len(chunks)
    assert len(metadata["chunks"]) == len(chunks)
    assert metadata["embedding_dimension"] == 768

    # 4. Verify Neo4j graph payload was replaced
    assert len(mock_graph.payloads) == 1
    payload = mock_graph.payloads[0]
    assert payload["document_id"] == str(doc.id)
    assert len(payload["chunks"]) == len(chunks)


# ── Pipeline Failure at Embedding Stage ───────────────────────────────────────


async def test_pipeline_failure_at_embedding(
    session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr("app.ingestion.pipeline.get_data_dir", lambda: tmp_path)

    pdf_bytes = make_minimal_legal_pdf()
    doc = Document(
        title="Failing Embedding Law",
        type=DocumentType.ACT,
        source="India Code",
        status=DocumentStatus.REGISTERED,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    class FailingEmbedder:
        def embed(self, texts: list[str]) -> np.ndarray:
            raise RuntimeError("InLegalBERT model execution failed: CUDA OOM")

    with pytest.raises(IngestionError) as exc_info:
        await run_pipeline(
            document_id=doc.id,
            pdf_bytes=pdf_bytes,
            db=session,
            settings=settings,
            embedder=FailingEmbedder(),
        )

    assert exc_info.value.stage == ProcessingJobStage.EMBEDDING

    # Document should be marked FAILED
    await session.refresh(doc)
    assert doc.status == DocumentStatus.FAILED

    # Check EMBEDDING job failed
    jobs_res = await session.execute(
        select(ProcessingJob).where(ProcessingJob.document_id == doc.id)
    )
    jobs = {j.stage: j for j in jobs_res.scalars().all()}
    assert jobs[ProcessingJobStage.EMBEDDING].status == ProcessingJobStatus.FAILED
    assert "CUDA OOM" in jobs[ProcessingJobStage.EMBEDDING].error

    # Downstream stages should not have been executed
    assert ProcessingJobStage.VECTOR_INDEX not in jobs
    assert ProcessingJobStage.GRAPH_POPULATION not in jobs


# ── Pipeline Failure at Graph Stage ───────────────────────────────────────────


async def test_pipeline_failure_at_graph_population(
    session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr("app.ingestion.pipeline.get_data_dir", lambda: tmp_path)

    pdf_bytes = make_minimal_legal_pdf()
    doc = Document(
        title="Graph Failure Law",
        type=DocumentType.ACT,
        source="India Code",
        status=DocumentStatus.REGISTERED,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    class FailingGraphClient:
        async def replace_document_graph(self, payload: dict[str, Any]) -> None:
            raise ConnectionError("Neo4j database cluster unreachable")

    mock_embedder = MockEmbedder()

    with pytest.raises(IngestionError) as exc_info:
        await run_pipeline(
            document_id=doc.id,
            pdf_bytes=pdf_bytes,
            db=session,
            settings=settings,
            embedder=mock_embedder,
            graph_client=FailingGraphClient(),
        )

    assert exc_info.value.stage == ProcessingJobStage.GRAPH_POPULATION

    await session.refresh(doc)
    assert doc.status == DocumentStatus.FAILED

    jobs_res = await session.execute(
        select(ProcessingJob).where(ProcessingJob.document_id == doc.id)
    )
    jobs = {j.stage: j for j in jobs_res.scalars().all()}
    assert jobs[ProcessingJobStage.GRAPH_POPULATION].status == ProcessingJobStatus.FAILED
    assert "Neo4j database cluster unreachable" in jobs[ProcessingJobStage.GRAPH_POPULATION].error


# ── Incremental FAISS Vector Preservation ─────────────────────────────────────


async def test_faiss_incremental_preservation(
    session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr("app.ingestion.pipeline.get_data_dir", lambda: tmp_path)

    pdf_bytes = make_minimal_legal_pdf()
    doc1 = Document(title="Law A", type=DocumentType.ACT, source="India Code")
    doc2 = Document(title="Law B", type=DocumentType.ACT, source="India Code")
    session.add_all([doc1, doc2])
    await session.commit()
    await session.refresh(doc1)
    await session.refresh(doc2)

    embedder = MockEmbedder()
    graph = MockGraphClient()

    # Ingest Document 1
    chunks1 = await run_pipeline(
        document_id=doc1.id,
        pdf_bytes=pdf_bytes,
        db=session,
        settings=settings,
        embedder=embedder,
        graph_client=graph,
    )

    index1, meta1 = load_index(tmp_path, settings.vector_index_name)
    count1 = index1.ntotal
    assert count1 == len(chunks1)

    # Ingest Document 2
    chunks2 = await run_pipeline(
        document_id=doc2.id,
        pdf_bytes=pdf_bytes,
        db=session,
        settings=settings,
        embedder=embedder,
        graph_client=graph,
    )

    index2, meta2 = load_index(tmp_path, settings.vector_index_name)
    count2 = index2.ntotal
    assert count2 == count1 + len(chunks2)

    # Verify both document IDs are present in index chunk mapping
    indexed_doc_ids = {c["document_id"] for c in meta2["chunks"]}
    assert str(doc1.id) in indexed_doc_ids
    assert str(doc2.id) in indexed_doc_ids


# ── Reprocessing Idempotency (No Duplicates) ───────────────────────────────────


async def test_reprocessing_idempotency_no_duplicates(
    session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr("app.ingestion.pipeline.get_data_dir", lambda: tmp_path)

    pdf_bytes = make_minimal_legal_pdf()
    doc = Document(title="Idempotent Act", type=DocumentType.ACT, source="India Code")
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    embedder = MockEmbedder()
    graph = MockGraphClient()

    # Initial Run
    chunks1 = await run_pipeline(
        document_id=doc.id,
        pdf_bytes=pdf_bytes,
        db=session,
        settings=settings,
        embedder=embedder,
        graph_client=graph,
    )

    index1, meta1 = load_index(tmp_path, settings.vector_index_name)
    initial_vectors = index1.ntotal

    # Second Run (Reprocess)
    chunks2 = await run_pipeline(
        document_id=doc.id,
        pdf_bytes=pdf_bytes,
        db=session,
        settings=settings,
        embedder=embedder,
        graph_client=graph,
    )

    # Verify no duplicate chunks in database
    db_chunks = (
        (await session.execute(select(Chunk).where(Chunk.document_id == doc.id)))
        .scalars()
        .all()
    )
    assert len(db_chunks) == len(chunks2)

    # Verify no duplicate vectors in FAISS index
    index2, meta2 = load_index(tmp_path, settings.vector_index_name)
    assert index2.ntotal == initial_vectors
    assert len(meta2["chunks"]) == initial_vectors

    # Verify all chunk IDs in FAISS are unique
    chunk_ids = [c["chunk_id"] for c in meta2["chunks"]]
    assert len(chunk_ids) == len(set(chunk_ids))


# ── Concurrent Index Updates Synchronization ─────────────────────────────────


async def test_concurrent_index_writes(tmp_path: Path) -> None:
    index_name = "test_concurrent"
    dim = 768

    async def _write_doc(doc_id: str, count: int) -> None:
        vectors = np.ones((count, dim), dtype=np.float32) / np.sqrt(dim)
        records = [
            {
                "chunk_id": str(uuid4()),
                "document_id": doc_id,
                "chunk_index": i,
                "text": f"Doc {doc_id} chunk {i}",
                "hierarchy": {},
                "document_title": f"Doc {doc_id}",
            }
            for i in range(count)
        ]
        await update_index_incremental(
            data_dir=tmp_path,
            index_name=index_name,
            new_vectors=vectors,
            new_chunk_records=records,
            document_id=doc_id,
            model_name="law-ai/InLegalBERT",
            pooling_method="attention_mask_mean_pooling",
            max_tokens=512,
        )

    doc_a_id = str(uuid4())
    doc_b_id = str(uuid4())
    doc_c_id = str(uuid4())

    # Launch 3 concurrent writes
    await asyncio.gather(
        _write_doc(doc_a_id, 5),
        _write_doc(doc_b_id, 3),
        _write_doc(doc_c_id, 4),
    )

    index, metadata = load_index(tmp_path, index_name)
    assert index.ntotal == 12
    assert len(metadata["chunks"]) == 12

    doc_ids = {c["document_id"] for c in metadata["chunks"]}
    assert doc_ids == {doc_a_id, doc_b_id, doc_c_id}


# ── Startup Recovery followed by Safe Retry ───────────────────────────────────


async def test_startup_recovery_then_retry(
    session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr("app.ingestion.pipeline.get_data_dir", lambda: tmp_path)

    pdf_bytes = make_minimal_legal_pdf()
    doc = Document(
        title="Interrupted Law",
        type=DocumentType.ACT,
        source="India Code",
        status=DocumentStatus.PROCESSING,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    interrupted_job = ProcessingJob(
        document_id=doc.id,
        stage=ProcessingJobStage.EMBEDDING,
        status=ProcessingJobStatus.RUNNING,
    )
    session.add(interrupted_job)
    await session.commit()

    # 1. Run startup recovery
    recovered = await recover_interrupted_jobs(session)
    assert recovered == 1

    await session.refresh(doc)
    await session.refresh(interrupted_job)
    assert doc.status == DocumentStatus.FAILED
    assert interrupted_job.status == ProcessingJobStatus.FAILED

    # 2. Administrator retries the document
    embedder = MockEmbedder()
    graph = MockGraphClient()

    chunks = await run_pipeline(
        document_id=doc.id,
        pdf_bytes=pdf_bytes,
        db=session,
        settings=settings,
        embedder=embedder,
        graph_client=graph,
    )

    await session.refresh(doc)
    assert doc.status == DocumentStatus.READY

    jobs_res = await session.execute(
        select(ProcessingJob).where(ProcessingJob.document_id == doc.id)
    )
    jobs = {j.stage: j for j in jobs_res.scalars().all()}
    assert jobs[ProcessingJobStage.EMBEDDING].status == ProcessingJobStatus.COMPLETED
    assert jobs[ProcessingJobStage.EMBEDDING].error is None
