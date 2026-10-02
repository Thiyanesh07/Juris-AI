from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class CurrentUserResponse(BaseModel):
    """Safe browser-facing representation of the signed-in user."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str | None
    image_url: str | None
    role: UserRole
    is_active: bool = True
    last_login_at: datetime | None = None
