"""SavedResearch — a user's bookmark of a research session.

Saving a whole session (rather than an individual query/answer) keeps the
semantics clear: the bookmark preserves the full research thread including its
queries, answers and citations. A (user, session) pair can only be saved once.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, new_uuid

if TYPE_CHECKING:
    from app.models.research_session import ResearchSession
    from app.models.user import User


class SavedResearch(CreatedAtMixin, Base):
    """A bookmark linking a user to a research session."""

    __tablename__ = "saved_research"
    __table_args__ = (
        UniqueConstraint("user_id", "session_id", name="uq_saved_research_user_session"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="saved_research")
    session: Mapped["ResearchSession"] = relationship()

    def __repr__(self) -> str:
        return (
            f"SavedResearch(id={self.id!r}, user_id={self.user_id!r}, "
            f"session_id={self.session_id!r})"
        )
