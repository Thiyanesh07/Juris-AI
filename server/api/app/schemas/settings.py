"""System settings schemas (Phase 16)."""

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class SettingSectionResponse(BaseModel):
    section: str
    config: dict[str, Any]
    updated_at: datetime | None = None
    updated_by_id: UUID | None = None


class SettingUpdateRequest(BaseModel):
    config: dict[str, Any]


class AllSettingsResponse(BaseModel):
    sections: dict[str, dict[str, Any]]
