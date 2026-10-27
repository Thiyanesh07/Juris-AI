"""PostgreSQL batch loading for retrieval evidence enrichment."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.document import Document
from app.models.enums import DocumentStatus


async def load_chunks_by_ids(
    session: AsyncSession,
    chunk_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """Load chunk evidence rows in a single query; missing IDs are omitted."""
    if not chunk_ids:
        return {}
    uuid_ids: list[UUID] = []
    for chunk_id in chunk_ids:
        try:
            uuid_ids.append(UUID(str(chunk_id)))
        except (ValueError, TypeError):
            continue
    if not uuid_ids:
        return {}
    rows = (
        await session.execute(
            select(Chunk, Document)
            .join(Document, Document.id == Chunk.document_id)
            .where(
                Chunk.id.in_(uuid_ids),
                Document.status == DocumentStatus.READY,
            )
        )
    ).all()
    evidence: dict[str, dict[str, Any]] = {}
    for chunk, document in rows:
        evidence[str(chunk.id)] = {
            "chunk_id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "document_title": document.title,
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
            "pdf_url": f"/api/v1/documents/{chunk.document_id}/pdf",
        }
    return evidence


async def search_chunks_by_identifiers(
    session: AsyncSession,
    terms: list[str],
    top_k: int = 15,
) -> list[dict[str, Any]]:
    """Retrieve chunks matching explicit legal identifiers, section numbers, or judgment names."""
    if not terms:
        return []

    from sqlalchemy import or_

    conditions = []
    seen_terms: set[str] = set()
    for term in terms:
        clean = " ".join(term.strip().split())
        if len(clean) >= 3 and clean.lower() not in seen_terms:
            seen_terms.add(clean.lower())
            conditions.append(Chunk.citation_ref.ilike(f"%{clean}%"))
            conditions.append(Document.title.ilike(f"%{clean}%"))
            # For short phrases like "Section 66A" or "Article 21", also match in chunk text
            if len(clean) <= 40:
                conditions.append(Chunk.text.ilike(f"%{clean}%"))

    if not conditions:
        return []

    stmt = (
        select(Chunk, Document)
        .join(Document, Document.id == Chunk.document_id)
        .where(
            Document.status == DocumentStatus.READY,
            or_(*conditions[:12]),
        )
        .limit(top_k)
    )

    try:
        rows = (await session.execute(stmt)).all()
    except Exception:
        return []

    results: list[dict[str, Any]] = []
    for rank, (chunk, document) in enumerate(rows, start=1):
        results.append({
            "chunk_id": str(chunk.id),
            "score": 0.88,
            "rank": rank,
            "document_title": document.title,
            "citation_ref": chunk.citation_ref,
            "text": chunk.text,
            "document_id": str(document.id),
            "chunk_index": chunk.chunk_index,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "hierarchy": chunk.hierarchy,
            "pdf_url": f"/api/v1/documents/{chunk.document_id}/pdf",
            "source_url": document.source_url,
        })
    return results
