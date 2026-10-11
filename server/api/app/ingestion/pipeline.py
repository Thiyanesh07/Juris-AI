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

import asyncio
import hashlib
import logging
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_data_dir
from app.graph.client import Neo4jClient
from app.graph.extraction import Entity, Relation, extract_entities, extract_relations
from app.graph.population import build_graph_payload
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
from app.retrieval.index import remove_document_from_index, update_index_incremental
from app.retrieval.service import build_embedder

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _cleanup_faiss_on_failure(
    *,
    data_dir: Path,
    settings: Settings,
    document_id: str,
) -> None:
    """Best-effort cleanup of FAISS vectors following downstream ingestion failure.

    Failure during cleanup is logged safely and will NEVER mask the primary ingestion exception.
    """
    try:
        await remove_document_from_index(
            data_dir=data_dir,
            index_name=settings.vector_index_name,
            document_id=document_id,
        )
    except Exception as cleanup_exc:  # noqa: BLE001
        logger.warning(
            "Failed to clean up FAISS index after pipeline failure for document %s: %s",
            document_id,
            cleanup_exc,
            exc_info=True,
        )


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
    embedder: Any | None = None,
    graph_client: Any | None = None,
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
    chunk_rows: list[Chunk] = []
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
        await db.flush()

        save_chunks(data_dir, document_id, document_version_id, chunks)

    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        await _mark_job(db, job_chunk, ProcessingJobStatus.FAILED, str(exc))
        doc.status = DocumentStatus.FAILED
        await db.commit()
        raise IngestionError(str(exc), ProcessingJobStage.CHUNKING) from exc

    await _mark_job(db, job_chunk, ProcessingJobStatus.COMPLETED)
    await db.commit()

    # ── STAGE 4: EMBEDDING ─────────────────────────────────────────────────
    job_embed = await _get_or_create_job(db, document_id, ProcessingJobStage.EMBEDDING)
    await _mark_job(db, job_embed, ProcessingJobStatus.RUNNING)
    await db.commit()

    vectors: Any = None
    try:
        enc = embedder or build_embedder(settings)
        texts = [ch.text for ch in chunks]
        if texts:
            vectors = await asyncio.to_thread(enc.embed, texts)
        else:
            vectors = []
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        await _mark_job(db, job_embed, ProcessingJobStatus.FAILED, str(exc))
        doc.status = DocumentStatus.FAILED
        await db.commit()
        raise IngestionError(str(exc), ProcessingJobStage.EMBEDDING) from exc

    await _mark_job(db, job_embed, ProcessingJobStatus.COMPLETED)
    await db.commit()

    # ── STAGE 5: VECTOR_INDEX ──────────────────────────────────────────────
    job_vindex = await _get_or_create_job(db, document_id, ProcessingJobStage.VECTOR_INDEX)
    await _mark_job(db, job_vindex, ProcessingJobStatus.RUNNING)
    await db.commit()

    try:
        if chunks:
            chunk_records = [
                {
                    "chunk_id": str(ch_row.id),
                    "document_id": str(document_id),
                    "document_version_id": str(document_version_id)
                    if document_version_id
                    else None,
                    "chunk_index": ch_row.chunk_index,
                    "text": ch_row.text,
                    "page_start": ch_row.page_start,
                    "page_end": ch_row.page_end,
                    "hierarchy": ch_row.hierarchy or {},
                    "citation_ref": ch_row.citation_ref,
                    "document_title": doc.title,
                    "source_url": doc.source_url,
                }
                for ch_row in chunk_rows
            ]

            pooling_method = getattr(enc, "pooling_method", "attention_mask_mean_pooling")
            await update_index_incremental(
                data_dir=data_dir,
                index_name=settings.vector_index_name,
                new_vectors=vectors,
                new_chunk_records=chunk_records,
                document_id=str(document_id),
                model_name=settings.embedding_model_name,
                pooling_method=pooling_method,
                max_tokens=settings.embedding_max_tokens,
            )
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        await _mark_job(db, job_vindex, ProcessingJobStatus.FAILED, str(exc))
        doc.status = DocumentStatus.FAILED
        await db.commit()
        raise IngestionError(str(exc), ProcessingJobStage.VECTOR_INDEX) from exc

    await _mark_job(db, job_vindex, ProcessingJobStatus.COMPLETED)
    await db.commit()

    # ── STAGE 6: ENTITY_EXTRACTION ─────────────────────────────────────────
    job_entity = await _get_or_create_job(db, document_id, ProcessingJobStage.ENTITY_EXTRACTION)
    await _mark_job(db, job_entity, ProcessingJobStatus.RUNNING)
    await db.commit()

    entities_by_chunk: dict[str, list[Entity]] = {}
    try:
        for ch_row in chunk_rows:
            chunk_id_str = str(ch_row.id)
            entities = extract_entities(
                ch_row.text,
                document_title=doc.title,
                document_id=str(document_id),
            )
            entities_by_chunk[chunk_id_str] = entities
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        await _mark_job(db, job_entity, ProcessingJobStatus.FAILED, str(exc))
        doc.status = DocumentStatus.FAILED
        await db.commit()
        await _cleanup_faiss_on_failure(
            data_dir=data_dir,
            settings=settings,
            document_id=str(document_id),
        )
        raise IngestionError(str(exc), ProcessingJobStage.ENTITY_EXTRACTION) from exc

    await _mark_job(db, job_entity, ProcessingJobStatus.COMPLETED)
    await db.commit()

    # ── STAGE 7: RELATION_EXTRACTION ───────────────────────────────────────
    job_rel = await _get_or_create_job(db, document_id, ProcessingJobStage.RELATION_EXTRACTION)
    await _mark_job(db, job_rel, ProcessingJobStatus.RUNNING)
    await db.commit()

    relations_by_chunk: dict[str, list[Relation]] = {}
    try:
        for ch_row in chunk_rows:
            chunk_id_str = str(ch_row.id)
            relations = extract_relations(
                ch_row.text,
                entities_by_chunk.get(chunk_id_str, []),
                document_title=doc.title,
                document_id=str(document_id),
            )
            relations_by_chunk[chunk_id_str] = relations
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        await _mark_job(db, job_rel, ProcessingJobStatus.FAILED, str(exc))
        doc.status = DocumentStatus.FAILED
        await db.commit()
        await _cleanup_faiss_on_failure(
            data_dir=data_dir,
            settings=settings,
            document_id=str(document_id),
        )
        raise IngestionError(str(exc), ProcessingJobStage.RELATION_EXTRACTION) from exc

    await _mark_job(db, job_rel, ProcessingJobStatus.COMPLETED)
    await db.commit()

    # ── STAGE 8: GRAPH_POPULATION ──────────────────────────────────────────
    job_graph = await _get_or_create_job(db, document_id, ProcessingJobStage.GRAPH_POPULATION)
    await _mark_job(db, job_graph, ProcessingJobStatus.RUNNING)
    await db.commit()

    try:
        doc_type_val = doc.type.value if hasattr(doc.type, "value") else str(doc.type)
        payload = build_graph_payload(
            doc_id=document_id,
            doc_title=doc.title,
            doc_type=doc_type_val,
            chunks=chunk_rows,
            entities_by_chunk=entities_by_chunk,
            relations_by_chunk=relations_by_chunk,
        )
        gclient = graph_client or Neo4jClient(settings)
        await gclient.replace_document_graph(payload)
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        await _mark_job(db, job_graph, ProcessingJobStatus.FAILED, str(exc))
        doc.status = DocumentStatus.FAILED
        await db.commit()
        await _cleanup_faiss_on_failure(
            data_dir=data_dir,
            settings=settings,
            document_id=str(document_id),
        )
        raise IngestionError(str(exc), ProcessingJobStage.GRAPH_POPULATION) from exc

    await _mark_job(db, job_graph, ProcessingJobStatus.COMPLETED)

    # ── ALL STAGES SUCCEEDED: DOCUMENT IS READY ────────────────────────────
    doc.status = DocumentStatus.READY
    await db.commit()

    logger.info(
        "Pipeline complete (8/8 stages): document_id=%s pages=%d chunks=%d status=READY",
        document_id,
        len(pages),
        len(chunks),
    )
    return chunks
