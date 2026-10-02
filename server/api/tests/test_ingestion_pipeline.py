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

    # Processing jobs should be COMPLETED
    jobs = (
        await session.execute(
            select(ProcessingJob).where(ProcessingJob.document_id == registered_doc.id)
        )
    ).scalars().all()
    assert len(jobs) == 3  # INGESTION, EXTRACTION, CHUNKING
    for job in jobs:
        assert job.status == ProcessingJobStatus.COMPLETED


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
    )
    count_after_second = (
        await session.execute(
            select(Chunk).where(Chunk.document_id == registered_doc.id)
        )
    ).scalars().all()

    # Chunks should be replaced not doubled
    assert len(count_after_second) == len(count_after_first)
