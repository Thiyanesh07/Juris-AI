"""Audit log schemas (Phase 16)."""

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    actor_id: UUID | None = None
    actor_email: str | None = None
    event_metadata: dict[str, Any] | None = None
    created_at: datetime


class PaginatedAuditResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int
    page: int
    page_size: int
