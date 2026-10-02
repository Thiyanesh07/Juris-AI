"""SystemEvent — audit/operational events (the event system comes later).

``actor_id`` is nullable and uses SET NULL: events must survive user removal
for audit purposes. The JSON payload column is named ``metadata`` in the
database but exposed as ``event_metadata`` in Python (``metadata`` is reserved
by SQLAlchemy's declarative API).
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, new_uuid

if TYPE_CHECKING:
    from app.models.user import User


class SystemEvent(CreatedAtMixin, Base):
    """A structured operational/audit event."""

    __tablename__ = "system_events"
    __table_args__ = (
        # Common audit queries filter/paginate by time.
        Index("ix_system_events_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    event_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)

    actor: Mapped["User | None"] = relationship()

    def __repr__(self) -> str:
        return f"SystemEvent(id={self.id!r}, event_type={self.event_type!r})"
