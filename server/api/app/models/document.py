"""Document — a registered legal source in the application registry.

This is registry metadata only. The legal graph entities (Article, Act,
Section, ...) live in Neo4j in a later slice; processing lives in ProcessingJob.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid, pg_enum
from app.models.enums import DocumentStatus, DocumentType

if TYPE_CHECKING:
    from app.models.chunk import Chunk
    from app.models.citation import Citation
    from app.models.document_version import DocumentVersion
    from app.models.processing_job import ProcessingJob


class Document(TimestampMixin, Base):
    """A registered legal source (Constitution, Act, judgment, ...)."""

    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[DocumentType] = mapped_column(
        pg_enum(DocumentType, "document_type"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        pg_enum(DocumentStatus, "document_status"),
        default=DocumentStatus.REGISTERED,
        index=True,
        nullable=False,
    )

    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    # Evidence is retained and protects a registered source from deletion.
    # ``passive_deletes`` lets PostgreSQL enforce the FK's RESTRICT policy
    # instead of SQLAlchemy silently nulling the optional ``document_id``.
    citations: Mapped[list["Citation"]] = relationship(
        back_populates="document", passive_deletes="all"
    )

    def __repr__(self) -> str:
        return f"Document(id={self.id!r}, title={self.title!r}, type={self.type!r})"
