"""Chunk model representing hierarchy-aware text units extracted from legal documents."""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, new_uuid

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.document_version import DocumentVersion


class Chunk(CreatedAtMixin, Base):
    """A hierarchy-aware chunk of text extracted from a legal document."""

    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "document_version_id",
            "chunk_index",
            name="uq_chunks_doc_version_index",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("document_versions.id", ondelete="SET NULL"), index=True, nullable=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hierarchy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    citation_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    document: Mapped["Document"] = relationship(back_populates="chunks")
    document_version: Mapped["DocumentVersion | None"] = relationship()

    def __repr__(self) -> str:
        return (
            f"Chunk(id={self.id!r}, doc_id={self.document_id!r}, "
            f"index={self.chunk_index!r}, citation={self.citation_ref!r})"
        )
