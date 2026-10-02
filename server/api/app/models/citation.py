"""Citation — evidence supporting a generated answer.

The citation schema is intentionally extensible: the later grounding/
source-verification slice will refine fields such as source_type and relevance.
``document_id`` is nullable (a citation may initially reference sources that
are not yet registered documents) and uses RESTRICT so a document cannot be
removed while evidence still cites it.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, new_uuid

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.research_answer import ResearchAnswer


class Citation(CreatedAtMixin, Base):
    """A single piece of evidence backing a research answer."""

    __tablename__ = "citations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    answer_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_answers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    citation: Mapped[str] = mapped_column(Text, nullable=False)
    relevance: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    answer: Mapped["ResearchAnswer"] = relationship(back_populates="citations")
    document: Mapped["Document | None"] = relationship(back_populates="citations")

    def __repr__(self) -> str:
        return f"Citation(id={self.id!r}, citation={self.citation!r})"
