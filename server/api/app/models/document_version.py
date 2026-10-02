"""DocumentVersion — a version of a legal document with its effective range.

Supports amendment-aware reasoning later: a version is *current* while
``effective_to`` is NULL; historical versions carry closed date ranges.
Overlapping effective ranges are not enforced here — temporal reasoning is a
later slice. Dates are calendar dates (timezone-free ``Date`` columns).
"""

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, new_uuid

if TYPE_CHECKING:
    from app.models.document import Document


class DocumentVersion(CreatedAtMixin, Base):
    """A specific version of a document with its effective date range."""

    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version", name="uq_document_versions_document_version"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_document_versions_effective_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="versions")

    def __repr__(self) -> str:
        return f"DocumentVersion(id={self.id!r}, version={self.version!r})"
