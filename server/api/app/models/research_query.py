"""ResearchQuery — a question submitted inside a research session."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, new_uuid

if TYPE_CHECKING:
    from app.models.research_answer import ResearchAnswer
    from app.models.research_session import ResearchSession


class ResearchQuery(CreatedAtMixin, Base):
    """A question asked within a research session (immutable after creation)."""

    __tablename__ = "research_queries"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)

    session: Mapped["ResearchSession"] = relationship(back_populates="queries")
    answers: Mapped[list["ResearchAnswer"]] = relationship(
        back_populates="query", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"ResearchQuery(id={self.id!r}, question={self.question!r})"
