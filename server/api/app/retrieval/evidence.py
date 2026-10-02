"""PostgreSQL batch loading for retrieval evidence enrichment."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.document import Document


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
            .where(Chunk.id.in_(uuid_ids))
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
        }
    return evidence
