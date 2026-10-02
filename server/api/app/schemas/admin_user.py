"""User & Admin management schemas (Phase 16)."""

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str | None = None
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str | None = None
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None


class UserUpdateRequest(BaseModel):
    name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class AdminProvisionRequest(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=8)
    role: str = "admin"  # "admin" or "super_admin"


class PaginatedUsersResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int
