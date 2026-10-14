"""Integration tests for app/ingestion/pipeline.py against real PostgreSQL.

Requires the test database fixture (migrated_database / session from conftest).
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.ingestion.pipeline import IngestionError, run_pipeline
from app.models import Document
from app.models.chunk import Chunk
from app.models.enums import DocumentStatus, DocumentType, ProcessingJobStage, ProcessingJobStatus
from app.models.processing_job import ProcessingJob
from tests.fake_neo4j import FakeNeo4jClient
from tests.helpers import make_minimal_legal_pdf


@pytest.fixture
async def registered_doc(session: AsyncSession) -> Document:
    """Insert and return a REGISTERED Document for use in pipeline tests."""
    doc = Document(
        title="Test Constitution",
        type=DocumentType.CONSTITUTION,
        source="test-fixture",
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return doc


async def test_pipeline_succeeds_on_valid_pdf(
    registered_doc: Document, session: AsyncSession, tmp_path: Path
) -> None:
    settings = get_settings()
    # Override data_dir to tmp so we don't pollute real data dir during tests
    object.__setattr__(settings, "data_dir", str(tmp_path))

    pdf_bytes = make_minimal_legal_pdf()
    chunks = await run_pipeline(
        document_id=registered_doc.id,
        pdf_bytes=pdf_bytes,
        db=session,
        settings=settings,
        graph_client=FakeNeo4jClient(),
    )

    assert len(chunks) >= 1

    # Document should be READY
    await session.refresh(registered_doc)
    assert registered_doc.status == DocumentStatus.READY
    assert registered_doc.file_hash is not None
    assert registered_doc.file_path is not None

    # Chunks should exist in DB
    db_chunks = (
        await session.execute(select(Chunk).where(Chunk.document_id == registered_doc.id))
    ).scalars().all()
    assert len(db_chunks) >= 1

    # All chunks should have valid indices and text
    for ch in db_chunks:
        assert ch.chunk_index >= 0
        assert len(ch.text) > 0
        assert ch.char_count == len(ch.text)
        assert isinstance(ch.hierarchy, dict)

    # Processing jobs should be COMPLETED for all 8 stages of the modern pipeline lifecycle
    jobs = (
        await session.execute(
            select(ProcessingJob).where(ProcessingJob.document_id == registered_doc.id)
        )
    ).scalars().all()
    assert len(jobs) == 8
    expected_stages = {
        ProcessingJobStage.INGESTION,
        ProcessingJobStage.EXTRACTION,
        ProcessingJobStage.CHUNKING,
        ProcessingJobStage.EMBEDDING,
        ProcessingJobStage.VECTOR_INDEX,
        ProcessingJobStage.ENTITY_EXTRACTION,
        ProcessingJobStage.RELATION_EXTRACTION,
        ProcessingJobStage.GRAPH_POPULATION,
    }
    assert {job.stage for job in jobs} == expected_stages
    for job in jobs:
        assert job.status == ProcessingJobStatus.COMPLETED
        assert job.error is None


async def test_pipeline_fails_on_invalid_pdf(
    registered_doc: Document, session: AsyncSession, tmp_path: Path
) -> None:
    settings = get_settings()
    object.__setattr__(settings, "data_dir", str(tmp_path))

    with pytest.raises(IngestionError) as exc_info:
        await run_pipeline(
            document_id=registered_doc.id,
            pdf_bytes=b"NOT A PDF AT ALL",
            db=session,
            settings=settings,
        )

    assert exc_info.value.stage == ProcessingJobStage.INGESTION

    await session.refresh(registered_doc)
    assert registered_doc.status == DocumentStatus.FAILED


async def test_pipeline_stores_file_on_disk(
    registered_doc: Document, session: AsyncSession, tmp_path: Path
) -> None:
    settings = get_settings()
    object.__setattr__(settings, "data_dir", str(tmp_path))

    pdf_bytes = make_minimal_legal_pdf()
    await run_pipeline(
        document_id=registered_doc.id,
        pdf_bytes=pdf_bytes,
        db=session,
        settings=settings,
        graph_client=FakeNeo4jClient(),
    )

    raw_pdf = tmp_path / "raw" / str(registered_doc.id) / "original.pdf"
    pages_jsonl = tmp_path / "processed" / str(registered_doc.id) / "pages.jsonl"
    chunks_jsonl = tmp_path / "chunks" / str(registered_doc.id) / "chunks.jsonl"

    assert raw_pdf.exists(), "Raw PDF should be saved to disk"
    assert pages_jsonl.exists(), "Pages JSONL should be saved"
    assert chunks_jsonl.exists(), "Chunks JSONL should be saved"


async def test_pipeline_nonexistent_document_raises(session: AsyncSession, tmp_path: Path) -> None:
    settings = get_settings()
    object.__setattr__(settings, "data_dir", str(tmp_path))

    with pytest.raises(IngestionError) as exc_info:
        await run_pipeline(
            document_id=uuid.uuid4(),
            pdf_bytes=make_minimal_legal_pdf(),
            db=session,
            settings=settings,
        )

    assert exc_info.value.stage == ProcessingJobStage.INGESTION


async def test_pipeline_reprocess_replaces_chunks(
    registered_doc: Document, session: AsyncSession, tmp_path: Path
) -> None:
    settings = get_settings()
    object.__setattr__(settings, "data_dir", str(tmp_path))

    pdf_bytes = make_minimal_legal_pdf()

    # First run
    await run_pipeline(
        document_id=registered_doc.id,
        pdf_bytes=pdf_bytes,
        db=session,
        settings=settings,
        graph_client=FakeNeo4jClient(),
    )
    count_after_first = (
        await session.execute(
            select(Chunk).where(Chunk.document_id == registered_doc.id)
        )
    ).scalars().all()

    # Second run (reprocess)
    await run_pipeline(
        document_id=registered_doc.id,
        pdf_bytes=pdf_bytes,
        db=session,
        settings=settings,
        force=True,
        graph_client=FakeNeo4jClient(),
    )
    count_after_second = (
        await session.execute(
            select(Chunk).where(Chunk.document_id == registered_doc.id)
        )
    ).scalars().all()

    # Chunks should be replaced not doubled
    assert len(count_after_second) == len(count_after_first)


async def test_pipeline_graph_failure_preserves_faiss_and_chunks(
    registered_doc: Document, session: AsyncSession, tmp_path: Path
) -> None:
    """When graph population fails, PostgreSQL chunks and FAISS vectors must be preserved."""
    from app.retrieval.index import load_index

    settings = get_settings()
    object.__setattr__(settings, "data_dir", str(tmp_path))

    class FailingGraphClient:
        async def replace_document_graph(self, payload: dict) -> None:
            raise RuntimeError("Neo4j connection refused: simulated Aura outage")

    pdf_bytes = make_minimal_legal_pdf()

    with pytest.raises(IngestionError) as exc_info:
        await run_pipeline(
            document_id=registered_doc.id,
            pdf_bytes=pdf_bytes,
            db=session,
            settings=settings,
            graph_client=FailingGraphClient(),
        )

    # Ingestion error should specifically pinpoint GRAPH_POPULATION
    assert exc_info.value.stage == ProcessingJobStage.GRAPH_POPULATION

    # Document must NOT be marked READY
    await session.refresh(registered_doc)
    assert registered_doc.status == DocumentStatus.FAILED

    # GRAPH_POPULATION job must be FAILED, while VECTOR_INDEX must be COMPLETED
    jobs = (
        await session.execute(
            select(ProcessingJob).where(ProcessingJob.document_id == registered_doc.id)
        )
    ).scalars().all()
    job_map = {job.stage: job for job in jobs}
    assert job_map[ProcessingJobStage.VECTOR_INDEX].status == ProcessingJobStatus.COMPLETED
    assert job_map[ProcessingJobStage.GRAPH_POPULATION].status == ProcessingJobStatus.FAILED
    assert "simulated Aura outage" in (job_map[ProcessingJobStage.GRAPH_POPULATION].error or "")

    # Crucial Requirement: PostgreSQL chunks must still exist (preserved)
    db_chunks = (
        await session.execute(select(Chunk).where(Chunk.document_id == registered_doc.id))
    ).scalars().all()
    assert len(db_chunks) >= 1

    # Crucial Requirement: FAISS vectors must still exist on disk (NOT wiped by cleanup)
    index, metadata = load_index(tmp_path, settings.vector_index_name)
    assert index.ntotal == len(db_chunks)

    # Now retry with a working graph client after the simulated outage resolves
    chunks_retry = await run_pipeline(
        document_id=registered_doc.id,
        pdf_bytes=pdf_bytes,
        db=session,
        settings=settings,
        force=True,
        graph_client=FakeNeo4jClient(),
    )
    assert len(chunks_retry) == len(db_chunks)

    await session.refresh(registered_doc)
    assert registered_doc.status == DocumentStatus.READY

    # After retry, chunks and vectors should not be duplicated
    index_after_retry, _ = load_index(tmp_path, settings.vector_index_name)
    assert index_after_retry.ntotal == len(db_chunks)


async def test_pipeline_graph_failure_and_graph_only_recovery_lifecycle(
    registered_doc: Document, session: AsyncSession, tmp_path: Path
) -> None:
    """Full lifecycle: initial ingestion graph outage -> preserved data -> retrieval exclusion -> graph-only recovery -> retrieval restored."""
    from app.graph.population import populate_graph
    from app.retrieval.hybrid import hybrid_retrieve
    from app.retrieval.index import load_index
    from app.retrieval.service import retrieve_ready_chunks

    settings = get_settings()
    object.__setattr__(settings, "data_dir", str(tmp_path))

    class FailingGraphClient:
        async def replace_document_graph(self, payload: dict) -> None:
            raise RuntimeError("Simulated Neo4j network timeout")

    pdf_bytes = make_minimal_legal_pdf()

    # Step 1: Initial ingestion with graph outage
    with pytest.raises(IngestionError) as exc_info:
        await run_pipeline(
            document_id=registered_doc.id,
            pdf_bytes=pdf_bytes,
            db=session,
            settings=settings,
            graph_client=FailingGraphClient(),
        )
    assert exc_info.value.stage == ProcessingJobStage.GRAPH_POPULATION

    # Step 2: Document is FAILED, but chunks and vectors are preserved
    await session.refresh(registered_doc)
    assert registered_doc.status == DocumentStatus.FAILED

    db_chunks = (
        await session.execute(select(Chunk).where(Chunk.document_id == registered_doc.id))
    ).scalars().all()
    assert len(db_chunks) >= 1
    chunk_count_initial = len(db_chunks)

    index_initial, _ = load_index(tmp_path, settings.vector_index_name)
    assert index_initial.ntotal == chunk_count_initial

    # Step 3: Retrieval Exclusion while in FAILED status
    # The document must NOT be returned in user retrieval queries
    dense_results_before = await retrieve_ready_chunks(
        session, "Constitution of India", top_k=5, settings=settings
    )
    doc_ids_before = {str(r.get("document_id")) for r in dense_results_before}
    assert str(registered_doc.id) not in doc_ids_before

    fake_client = FakeNeo4jClient()
    hybrid_results_before = await hybrid_retrieve(
        session, fake_client, "Constitution of India", top_k=5, settings=settings
    )
    hybrid_doc_ids_before = {
        str(r.get("document_id")) for r in hybrid_results_before.get("results", [])
    }
    assert str(registered_doc.id) not in hybrid_doc_ids_before

    # Step 4: Graph-only recovery via populate_graph (without re-chunking or re-embedding)
    summary = await populate_graph(
        session,
        fake_client,
        document_id=registered_doc.id,
    )
    assert summary.ok
    assert summary.processed == 1
    assert len(summary.successes) == 1

    # Step 5: Document status transitioned to READY, graph populated
    await session.refresh(registered_doc)
    assert registered_doc.status == DocumentStatus.READY

    job_graph = (
        await session.execute(
            select(ProcessingJob).where(
                ProcessingJob.document_id == registered_doc.id,
                ProcessingJob.stage == ProcessingJobStage.GRAPH_POPULATION,
            )
        )
    ).scalar_one()
    assert job_graph.status == ProcessingJobStatus.COMPLETED

    # Step 6: Chunks and vectors were NOT duplicated
    db_chunks_after = (
        await session.execute(select(Chunk).where(Chunk.document_id == registered_doc.id))
    ).scalars().all()
    assert len(db_chunks_after) == chunk_count_initial

    index_after, _ = load_index(tmp_path, settings.vector_index_name)
    assert index_after.ntotal == chunk_count_initial

    # Step 7: Retrieval is now RESTORED (both dense and hybrid return the document)
    dense_results_after = await retrieve_ready_chunks(
        session, "Constitution of India", top_k=5, settings=settings
    )
    doc_ids_after = {str(r.get("document_id")) for r in dense_results_after}
    assert str(registered_doc.id) in doc_ids_after

    hybrid_results_after = await hybrid_retrieve(
        session, fake_client, "Constitution of India", top_k=5, settings=settings
    )
    hybrid_doc_ids_after = {
        str(r.get("document_id")) for r in hybrid_results_after.get("results", [])
    }
    assert str(registered_doc.id) in hybrid_doc_ids_after
