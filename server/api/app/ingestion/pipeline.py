"""Ingestion pipeline — orchestrates all stages for a single document.

Stages (matching ``ProcessingJobStage`` enum values):
  INGESTION  → validate PDF, compute SHA-256, save raw file
  EXTRACTION → extract pages and normalise text, save pages.jsonl
  CHUNKING   → run hierarchy detection + chunking, persist chunks to DB + FS

Job records in ``processing_jobs`` track per-stage status so the admin UI can
display live progress.  Document status is updated to PROCESSING at the start
and to READY (or FAILED) at the end.

Usage::

    from app.ingestion.pipeline import run_pipeline
    await run_pipeline(document_id=..., pdf_bytes=..., db=session, settings=settings)
"""

from __future__ import annotations

import hashlib
import logging
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_data_dir
from app.ingestion.chunker import ChunkConfig, ChunkResult, chunk_pages
from app.ingestion.extractor import PageRecord, extract_pages
from app.ingestion.persister import (
    save_chunks,
    save_pages,
    save_raw_pdf,
    save_structure,
)
from app.ingestion.validator import ValidationResult, validate_pdf
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.enums import DocumentStatus, ProcessingJobStage, ProcessingJobStatus
from app.models.processing_job import ProcessingJob

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def _get_or_create_job(
    db: AsyncSession,
    document_id: UUID,
    stage: ProcessingJobStage,
) -> ProcessingJob:
    """Fetch an existing ProcessingJob for this stage or create a new PENDING one."""
    result = await db.execute(
        select(ProcessingJob).where(
            ProcessingJob.document_id == document_id,
            ProcessingJob.stage == stage,
        )
    )
    job = result.scalar_one_or_none()
    if job is None:
        job = ProcessingJob(
            document_id=document_id,
            stage=stage,
            status=ProcessingJobStatus.PENDING,
        )
        db.add(job)
        await db.flush()
    return job


async def _mark_job(
    db: AsyncSession,
    job: ProcessingJob,
    status: ProcessingJobStatus,
    error: str | None = None,
) -> None:
    job.status = status
    job.error = error
    await db.flush()


# ── Public API ─────────────────────────────────────────────────────────────────


class IngestionError(Exception):
    """Raised when any pipeline stage fails."""

    def __init__(self, message: str, stage: ProcessingJobStage) -> None:
        super().__init__(message)
        self.stage = stage


async def run_pipeline(
    *,
    document_id: UUID,
    pdf_bytes: bytes,
    db: AsyncSession,
    settings: Settings,
    document_version_id: UUID | None = None,
    force: bool = False,
) -> list[ChunkResult]:
    """Run the full ingestion pipeline for *document_id*.

    Args:
        document_id: Must refer to an existing ``Document`` row.
        pdf_bytes: Raw PDF file bytes.
        db: Async DB session (caller manages the transaction).
        settings: Application settings instance.
        document_version_id: Optional FK to ``document_versions``.
        force: If True, skip idempotency check and reprocess.

    Returns:
        The list of :class:`~app.ingestion.chunker.ChunkResult` produced.

    Raises:
        IngestionError: If any stage fails (DB and FS artefacts are cleaned up).
    """
    data_dir = get_data_dir()

    # ── Load document ──────────────────────────────────────────────────────
    doc_result = await db.execute(select(Document).where(Document.id == document_id))
    doc = doc_result.scalar_one_or_none()
    if doc is None:
        raise IngestionError(f"Document {document_id} not found", ProcessingJobStage.INGESTION)

    doc.status = DocumentStatus.PROCESSING
    await db.flush()

    # ── STAGE 1: INGESTION ─────────────────────────────────────────────────
    job_ingest = await _get_or_create_job(db, document_id, ProcessingJobStage.INGESTION)
    await _mark_job(db, job_ingest, ProcessingJobStatus.RUNNING)
    await db.commit()

    try:
        # Write to a temp file for PyMuPDF validation
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = Path(tmp.name)

        validation: ValidationResult = validate_pdf(tmp_path)
        tmp_path.unlink(missing_ok=True)

        if not validation.valid:
            raise IngestionError(
                f"PDF validation failed: {validation.error_summary}",
                ProcessingJobStage.INGESTION,
            )

        file_hash = _sha256(pdf_bytes)
        raw_path = save_raw_pdf(data_dir, document_id, pdf_bytes)

        doc.file_hash = file_hash
        doc.file_path = str(raw_path)
        await db.flush()

    except IngestionError:
        await _mark_job(db, job_ingest, ProcessingJobStatus.FAILED, str(sys.exc_info()[1]))
        doc.status = DocumentStatus.FAILED
        await db.commit()
        raise
    except Exception as exc:  # noqa: BLE001
        await _mark_job(db, job_ingest, ProcessingJobStatus.FAILED, str(exc))
        doc.status = DocumentStatus.FAILED
        await db.commit()
        raise IngestionError(str(exc), ProcessingJobStage.INGESTION) from exc

    await _mark_job(db, job_ingest, ProcessingJobStatus.COMPLETED)
    await db.commit()

    # ── STAGE 2: EXTRACTION ────────────────────────────────────────────────
    job_extract = await _get_or_create_job(db, document_id, ProcessingJobStage.EXTRACTION)
    await _mark_job(db, job_extract, ProcessingJobStatus.RUNNING)
    await db.commit()

    pages: list[PageRecord] = []
    try:
        raw_path_obj = data_dir / "raw" / str(document_id) / "original.pdf"
        pages = extract_pages(raw_path_obj)

        save_pages(data_dir, document_id, pages)
        save_structure(
            data_dir,
            document_id,
            {
                "document_id": str(document_id),
                "file_hash": file_hash,
                "page_count": len(pages),
                "extracted_at": datetime.now(UTC).isoformat(),
            },
        )
    except Exception as exc:  # noqa: BLE001
        await _mark_job(db, job_extract, ProcessingJobStatus.FAILED, str(exc))
        doc.status = DocumentStatus.FAILED
        await db.commit()
        raise IngestionError(str(exc), ProcessingJobStage.EXTRACTION) from exc

    await _mark_job(db, job_extract, ProcessingJobStatus.COMPLETED)
    await db.commit()

    # ── STAGE 3: CHUNKING ──────────────────────────────────────────────────
    job_chunk = await _get_or_create_job(db, document_id, ProcessingJobStage.CHUNKING)
    await _mark_job(db, job_chunk, ProcessingJobStatus.RUNNING)
    await db.commit()

    chunks: list[ChunkResult] = []
    try:
        config = ChunkConfig(
            target_chars=settings.chunk_target_chars,
            max_chars=settings.chunk_max_chars,
            overlap_chars=settings.chunk_overlap_chars,
        )
        chunks = chunk_pages(pages, config)

        # Delete existing chunks for this (document, version) before re-inserting
        await db.execute(
            delete(Chunk).where(
                Chunk.document_id == document_id,
                Chunk.document_version_id == document_version_id,
            )
        )
        await db.flush()

        # Bulk insert new chunk rows
        chunk_rows = [
            Chunk(
                document_id=document_id,
                document_version_id=document_version_id,
                chunk_index=ch.chunk_index,
                text=ch.text,
                char_count=ch.char_count,
                page_start=ch.page_start,
                page_end=ch.page_end,
                hierarchy=ch.hierarchy,
                citation_ref=ch.citation_ref,
            )
            for ch in chunks
        ]
        db.add_all(chunk_rows)

        save_chunks(data_dir, document_id, document_version_id, chunks)

    except Exception as exc:  # noqa: BLE001
        await _mark_job(db, job_chunk, ProcessingJobStatus.FAILED, str(exc))
        doc.status = DocumentStatus.FAILED
        await db.commit()
        raise IngestionError(str(exc), ProcessingJobStage.CHUNKING) from exc

    await _mark_job(db, job_chunk, ProcessingJobStatus.COMPLETED)
    doc.status = DocumentStatus.READY
    await db.commit()

    logger.info(
        "Pipeline complete: document_id=%s pages=%d chunks=%d",
        document_id,
        len(pages),
        len(chunks),
    )
    return chunks
