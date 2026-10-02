"""Validation queue schemas (Phase 16)."""

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ValidationItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_type: str
    status: str
    confidence: float
    proposed_payload: dict[str, Any]
    evidence_text: str | None = None
    source_document_id: UUID | None = None
    source_chunk_id: str | None = None
    page_number: int | None = None
    reviewer_id: UUID | None = None
    decision_timestamp: datetime | None = None
    rejection_note: str | None = None
    created_at: datetime


class ValidationRejectRequest(BaseModel):
    rejection_note: str = Field(min_length=1)


class BulkApproveRequest(BaseModel):
    item_ids: list[UUID]


class PaginatedValidationResponse(BaseModel):
    items: list[ValidationItemResponse]
    total: int
    page: int
    page_size: int
