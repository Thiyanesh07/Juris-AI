"""Research History and Saved Research schemas (Phase 16)."""

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ResearchAnswerSummary(BaseModel):
    id: UUID
    answer: str
    validation_status: str
    created_at: datetime


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
