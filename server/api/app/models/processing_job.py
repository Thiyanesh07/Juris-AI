"""ProcessingJob — tracking for future document-processing pipeline stages.

The pipeline itself (ingestion, chunking, embedding, graph population, ...)
does not exist yet; this model only records job state.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid, pg_enum
from app.models.enums import ProcessingJobStage, ProcessingJobStatus

if TYPE_CHECKING:
    from app.models.document import Document


class ProcessingJob(TimestampMixin, Base):
    """A pipeline job for a document (stage + status + optional error)."""

    __tablename__ = "processing_jobs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    stage: Mapped[ProcessingJobStage] = mapped_column(
        pg_enum(ProcessingJobStage, "processing_job_stage"), nullable=False
    )
    status: Mapped[ProcessingJobStatus] = mapped_column(
        pg_enum(ProcessingJobStatus, "processing_job_status"),
        default=ProcessingJobStatus.PENDING,
        index=True,
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="processing_jobs")

    def __repr__(self) -> str:
        return f"ProcessingJob(id={self.id!r}, stage={self.stage!r}, status={self.status!r})"
