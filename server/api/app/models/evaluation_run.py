"""EvaluationRun — a reproducible research evaluation run.

The evaluation runner does not exist yet; this model records the run identity
and keeps experiment configuration/results as flexible JSONB payloads.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, new_uuid


class EvaluationRun(CreatedAtMixin, Base):
    """A recorded evaluation run with flexible JSON configuration/results."""

    __tablename__ = "evaluation_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    configuration: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    results: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"EvaluationRun(id={self.id!r}, name={self.name!r})"
