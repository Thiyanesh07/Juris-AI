"""HTTP contracts for dense evidence retrieval (no answer synthesis)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str = Field(min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1)


class RetrievalEvidence(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rank: int
    score: float
    chunk_id: UUID
    document_id: UUID
    document_version_id: UUID | None = None
    chunk_index: int
    text: str
    page_start: int | None = None
    page_end: int | None = None
    hierarchy: dict[str, Any]
    citation_ref: str | None = None
    source_url: str | None = None
    document_title: str
    document_type: str | None = None
    char_count: int | None = None
    checksum: str | None = None


class RetrievalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str
    results: list[RetrievalEvidence]
    score_type: str = "cosine similarity (L2-normalized embedding inner product)"
