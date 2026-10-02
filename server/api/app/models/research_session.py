"""ResearchSession — a user's research workspace containing their queries."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.research_query import ResearchQuery
    from app.models.user import User


class ResearchSession(TimestampMixin, Base):
    """A named research workspace owned by exactly one user."""

    __tablename__ = "research_sessions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    user: Mapped["User"] = relationship(back_populates="sessions")
    queries: Mapped[list["ResearchQuery"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"ResearchSession(id={self.id!r}, title={self.title!r})"
