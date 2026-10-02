"""SystemSetting — configuration section key-value settings.

Stores settings by section (GENERAL, AI_LLM, EMBEDDINGS, RETRIEVAL, INGESTION, KNOWLEDGE_GRAPH, SECURITY)
with JSONB payloads and audit metadata.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.user import User


class SystemSetting(TimestampMixin, Base):
    """Configuration section key-value settings."""

    __tablename__ = "system_settings"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    section: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column("config_json", JSONB, nullable=False)
    updated_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    updated_by: Mapped["User | None"] = relationship()

    def __repr__(self) -> str:
        return f"SystemSetting(section={self.section!r})"
