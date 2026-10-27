"""Research History and Saved Research schemas (Phase 16)."""

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ResearchCitationSummary(BaseModel):
    id: UUID
    citation: str
    relevance: float | None = None
    source_type: str | None = None
    document_id: UUID | None = None
    chunk_id: UUID | None = None
    marker: int | None = None
    page_start: int | None = None
    page_end: int | None = None
    citation_ref: str | None = None
    pdf_url: str | None = None
    document_title: str | None = None
    verification_status: str | None = None
    stable_id: str | None = None


class ResearchAnswerSummary(BaseModel):
    id: UUID
    answer: str
    validation_status: str
    created_at: datetime
    mode: str = "COMPREHENSIVE"
    citations: list[ResearchCitationSummary] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    graph: dict[str, Any] | None = None
    reasoning_steps: list[dict[str, Any]] = Field(default_factory=list)
    citation_validation: dict[str, Any] | None = None


class ResearchQuerySummary(BaseModel):
    id: UUID
    question: str
    created_at: datetime
    answers: list[ResearchAnswerSummary] = Field(default_factory=list)


class ResearchHistoryItemResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    mode: str = "COMPREHENSIVE"
    queries: list[ResearchQuerySummary] = Field(default_factory=list)
    saved: bool = False


class PaginatedHistoryResponse(BaseModel):
    items: list[ResearchHistoryItemResponse]
    total: int
    page: int
    page_size: int


class SavedResearchCreateRequest(BaseModel):
    session_id: UUID
    title: str | None = None


class SavedResearchResponse(BaseModel):
    id: UUID
    user_id: UUID
    session_id: UUID
    title: str
    created_at: datetime
    session: ResearchHistoryItemResponse | None = None
