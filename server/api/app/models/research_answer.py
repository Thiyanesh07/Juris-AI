"""ResearchAnswer — a generated answer for a research query.

A query may hold several answers (one per generation); consumers treat the
newest row (by created_at) as the current answer. Grounding/validation logic
arrives in a later slice — this model only stores the resulting status.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid
from app.models.enums import ValidationStatus

if TYPE_CHECKING:
    from app.models.citation import Citation
    from app.models.research_query import ResearchQuery


class ResearchAnswer(TimestampMixin, Base):
    """Generated answer plus its grounding/validation state."""

    __tablename__ = "research_answers"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    query_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_queries.id", ondelete="CASCADE"), index=True, nullable=False
    )
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    validation_status: Mapped[ValidationStatus] = mapped_column(
        Enum(
            ValidationStatus,
            name="validation_status",
            native_enum=True,
            validate_strings=True,
            values_callable=lambda e: [member.value for member in e],
        ),
        default=ValidationStatus.PENDING,
        nullable=False,
    )

    query: Mapped["ResearchQuery"] = relationship(back_populates="answers")
    citations: Mapped[list["Citation"]] = relationship(
        back_populates="answer", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"ResearchAnswer(id={self.id!r}, validation_status={self.validation_status!r})"
