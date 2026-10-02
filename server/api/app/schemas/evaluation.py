"""Pydantic schemas for read-only evaluation run endpoints (Phase 7C.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EvaluationRunSchema(BaseModel):
    """One recorded evaluation run from ``evaluation_runs``."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    name: str
    configuration: dict[str, Any] | None = None
    results: dict[str, Any] | None = None
    created_at: datetime


class PaginatedEvaluationRuns(BaseModel):
    """Paginated list of evaluation runs."""

    model_config = ConfigDict(extra="forbid")

    items: list[EvaluationRunSchema]
    total: int
    page: int
    page_size: int
