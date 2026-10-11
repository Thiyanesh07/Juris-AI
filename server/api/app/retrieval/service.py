"""Corpus index construction and dense evidence retrieval service."""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_data_dir
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.enums import DocumentStatus, ProcessingJobStage, ProcessingJobStatus
from app.models.processing_job import ProcessingJob
from app.retrieval.embeddings import (
    EmbeddingConfig,
    EmbeddingError,
    InLegalBertEmbedder,
    OnnxInLegalBertEmbedder,
)
from app.retrieval.index import (
    IndexError,
    load_index,
    save_index,
    search_index_rows,
    validate_index_embedder_settings,
    validate_query_embedding,
)


@lru_cache(maxsize=4)
def _cached_embedder(
    model_name: str, device: str, batch_size: int, max_tokens: int, backend: str = "onnx"
) -> Any:
    cfg = EmbeddingConfig(
        model_name=model_name,
        device=device,
        batch_size=batch_size,
        max_tokens=max_tokens,
        backend=backend,
    )
    if backend.lower() in {"onnx", "onnx_int8"}:
        return OnnxInLegalBertEmbedder(cfg)
    elif backend.lower() == "pytorch":
        return InLegalBertEmbedder(cfg)
    else:
        raise EmbeddingError(
            f"Unsupported embedding backend {backend!r}. Must be 'onnx', 'onnx_int8', or 'pytorch'."
        )


def build_embedder(settings: Settings) -> Any:
    return _cached_embedder(
        settings.embedding_model_name,
        settings.embedding_device,
        settings.embedding_batch_size,
        settings.embedding_max_tokens,
        settings.inlegalbert_backend,
    )


async def rebuild_index(
    db: AsyncSession, settings: Settings, embedder: Any | None = None
) -> dict[str, Any]:
    """Build the complete corpus index in deterministic document/chunk order."""
    rows = (
        await db.execute(
            select(Chunk, Document)
            .join(Document, Document.id == Chunk.document_id)
            .order_by(Chunk.document_id, Chunk.document_version_id, Chunk.chunk_index, Chunk.id)
        )
    ).all()
    if not rows:
        raise IndexError("Cannot build an index because the corpus has no chunks")
    document_ids = {chunk.document_id for chunk, _ in rows}
    jobs = (
        (await db.execute(select(ProcessingJob).where(ProcessingJob.document_id.in_(document_ids))))
        .scalars()
        .all()
    )
    jobs_by_key = {(job.document_id, job.stage): job for job in jobs}
    for document_id in document_ids:
        for stage in (ProcessingJobStage.EMBEDDING, ProcessingJobStage.VECTOR_INDEX):
            job = jobs_by_key.get((document_id, stage))
            if job is None:
                job = ProcessingJob(
                    document_id=document_id, stage=stage, status=ProcessingJobStatus.RUNNING
                )
                db.add(job)
                jobs_by_key[(document_id, stage)] = job
            else:
                job.status, job.error = ProcessingJobStatus.RUNNING, None
    await db.flush()
    records = [
        {
            "chunk_id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "document_version_id": str(chunk.document_version_id)
            if chunk.document_version_id
            else None,
            "chunk_index": chunk.chunk_index,
            "text": chunk.text,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "hierarchy": chunk.hierarchy,
            "citation_ref": chunk.citation_ref,
            "source_url": document.source_url,
            "document_title": document.title,
        }
        for chunk, document in rows
    ]
    encoder = embedder or build_embedder(settings)
    pooling_method = getattr(encoder, "pooling_method", "attention_mask_mean_pooling")

    def _embed_and_persist() -> tuple[Any, Any]:
        vectors = encoder.embed([record["text"] for record in records])
        directory = save_index(
            data_dir=get_data_dir(),
            index_name=settings.vector_index_name,
            vectors=vectors,
            chunk_records=records,
            model_name=settings.embedding_model_name,
            pooling_method=pooling_method,
            max_tokens=settings.embedding_max_tokens,
        )
        return directory, vectors

    try:
        directory, vectors = await asyncio.to_thread(_embed_and_persist)
    except Exception as exc:
        for document_id in document_ids:
            for stage in (ProcessingJobStage.EMBEDDING, ProcessingJobStage.VECTOR_INDEX):
                job = jobs_by_key[(document_id, stage)]
                job.status, job.error = ProcessingJobStatus.FAILED, str(exc)
        await db.commit()
        raise
    for document_id in document_ids:
        for stage in (ProcessingJobStage.EMBEDDING, ProcessingJobStage.VECTOR_INDEX):
            job = jobs_by_key[(document_id, stage)]
            job.status, job.error = ProcessingJobStatus.COMPLETED, None
    await db.commit()
    return {
        "chunk_count": len(records),
        "directory": str(directory),
        "dimension": int(vectors.shape[1]),
    }


def embed_query_vector(
    query: str, settings: Settings, embedder: Any | None = None
) -> tuple[Any, dict[str, Any], Any, Any]:
    """Load the index, validate embedder settings, and return one query embedding."""
    if not query or not query.strip():
        raise ValueError("Query must not be blank")
    index, metadata = load_index(get_data_dir(), settings.vector_index_name)
    encoder = embedder or build_embedder(settings)
    validate_index_embedder_settings(
        metadata,
        model_name=settings.embedding_model_name,
        pooling_method=getattr(encoder, "pooling_method", "attention_mask_mean_pooling"),
        normalization=getattr(encoder, "normalization", "l2"),
    )
    vector = encoder.embed([query.strip()])
    validate_query_embedding(vector, index)
    return index, metadata, vector, encoder


def retrieve(
    query: str,
    top_k: int,
    settings: Settings,
    embedder: Any | None = None,
    eligible_document_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    if not 1 <= top_k <= settings.retrieval_max_top_k:
        raise ValueError(f"top_k must be between 1 and {settings.retrieval_max_top_k}")
    index, metadata, vector, _encoder = embed_query_vector(query, settings, embedder=embedder)
    candidate_k = (
        min(index.ntotal, max(top_k * 3, top_k + 20))
        if eligible_document_ids is not None
        else top_k
    )
    hits = search_index_rows(index, metadata, vector, candidate_k)
    results: list[dict[str, Any]] = []
    for hit in hits:
        chunk_rec = metadata["chunks"][hit["faiss_row"]]
        if (
            eligible_document_ids is not None
            and str(chunk_rec.get("document_id")) not in eligible_document_ids
        ):
            continue
        result = dict(chunk_rec)
        result.update(score=hit["score"])
        results.append(result)
        if len(results) >= top_k:
            break
    for rank, item in enumerate(results, start=1):
        item["rank"] = rank
    return results


async def retrieve_ready_chunks(
    session: AsyncSession,
    query: str,
    top_k: int,
    settings: Settings,
    embedder: Any | None = None,
) -> list[dict[str, Any]]:
    """Retrieve dense evidence chunks belonging ONLY to READY documents in PostgreSQL.

    1. Oversamples FAISS hits to prevent candidate starvation.
    2. Queries authoritative PostgreSQL Document.status == READY in a single batch query (no N+1).
    3. Excludes chunks for FAILED, PROCESSING, DISABLED, or deleted/missing documents.
    4. Preserves ranking and scores of eligible chunks and handles empty results safely.
    """
    if not 1 <= top_k <= settings.retrieval_max_top_k:
        raise ValueError(f"top_k must be between 1 and {settings.retrieval_max_top_k}")
    index, metadata, vector, _encoder = embed_query_vector(query, settings, embedder=embedder)
    if index.ntotal == 0:
        return []

    candidate_k = min(index.ntotal, max(top_k * 3, top_k + 20))
    hits = search_index_rows(index, metadata, vector, candidate_k)
    if not hits:
        return []

    candidate_doc_uuids: set[UUID] = set()
    for hit in hits:
        doc_id_val = metadata["chunks"][hit["faiss_row"]].get("document_id")
        if doc_id_val:
            try:
                candidate_doc_uuids.add(UUID(str(doc_id_val)))
            except (ValueError, TypeError):
                pass

    if not candidate_doc_uuids:
        return []

    ready_doc_rows = (
        await session.execute(
            select(Document.id).where(
                Document.id.in_(candidate_doc_uuids),
                Document.status == DocumentStatus.READY,
            )
        )
    ).scalars().all()
    ready_doc_ids = {str(doc_id) for doc_id in ready_doc_rows}

    results: list[dict[str, Any]] = []
    for hit in hits:
        chunk_rec = metadata["chunks"][hit["faiss_row"]]
        if str(chunk_rec.get("document_id")) not in ready_doc_ids:
            continue
        result = dict(chunk_rec)
        result.update(score=hit["score"])
        results.append(result)
        if len(results) >= top_k:
            break

    for rank, item in enumerate(results, start=1):
        item["rank"] = rank

    return results
