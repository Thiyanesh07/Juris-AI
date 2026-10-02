"""ValidationItem — persistent human-in-the-loop legal entity & relationship validation queue item.

Supports review workflow for extraction items, relationship triples, citations, and metadata.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.user import User


class ValidationItem(TimestampMixin, Base):
    """Validation queue item for legal entities, triples, citations, and document metadata."""

    __tablename__ = "validation_items"
    __table_args__ = (
        Index("ix_validation_items_status", "status"),
        Index("ix_validation_items_item_type", "item_type"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    item_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ENTITY, RELATIONSIP, CITATION, DOCUMENT_METADATA
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    
    proposed_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    source_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    source_chunk_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    reviewer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decision_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_document: Mapped["Document | None"] = relationship()
    reviewer: Mapped["User | None"] = relationship()

    def __repr__(self) -> str:
        return f"ValidationItem(id={self.id!r}, item_type={self.item_type!r}, status={self.status!r})"
