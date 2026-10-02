"""Pydantic schemas for the documents API (G03).

Schemas are strict (extra fields forbidden) and use ``model_config`` with
``from_attributes=True`` so ORM objects can be serialised directly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ── Upload / Registration ──────────────────────────────────────────────────────


class DocumentUploadResponse(BaseModel):
    """Returned immediately after a successful upload (202 Accepted)."""

    model_config = ConfigDict(extra="forbid")

    document_id: UUID
    message: str = "Document accepted for processing"
    status: str  # e.g. "PROCESSING"
    duplicate: bool = False  # True if the same file hash was already registered


# ── Document list / detail ─────────────────────────────────────────────────────


class DocumentSummary(BaseModel):
    """Compact document representation for list endpoints."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    title: str
    type: str
    source: str
    status: str
    file_hash: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentDetail(DocumentSummary):
    """Full document representation including file_path and source_url."""

    source_url: str | None = None
    file_path: str | None = None


class PaginatedDocuments(BaseModel):
    """Paginated list of documents."""

    model_config = ConfigDict(extra="forbid")

    items: list[DocumentSummary]
    total: int
    page: int
    page_size: int


# ── Chunks ─────────────────────────────────────────────────────────────────────


class ChunkSchema(BaseModel):
    """A single hierarchy-aware chunk."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    document_id: UUID
    document_version_id: UUID | None = None
    chunk_index: int
    char_count: int
    page_start: int | None = None
    page_end: int | None = None
    hierarchy: dict[str, Any]
    citation_ref: str | None = None
    text: str
    created_at: datetime


class PaginatedChunks(BaseModel):
    """Paginated list of chunks for a document."""

    model_config = ConfigDict(extra="forbid")

    items: list[ChunkSchema]
    total: int
    page: int
    page_size: int


# ── Processing Jobs ────────────────────────────────────────────────────────────


class ProcessingJobSchema(BaseModel):
    """A processing job status record."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    document_id: UUID
    stage: str
    status: str
    error: str | None = None
    created_at: datetime
    updated_at: datetime


# ── Reprocess ─────────────────────────────────────────────────────────────────


class ReprocessResponse(BaseModel):
    """Returned when a reprocess is accepted."""

    model_config = ConfigDict(extra="forbid")

    document_id: UUID
    message: str = "Document queued for reprocessing"
