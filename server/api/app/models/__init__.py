"""Application SQLAlchemy models.

Importing this package registers every model with ``Base.metadata`` (this is
what Alembic and the test fixtures rely on). Import models from here, e.g.
``from app.models import User``.
"""

from app.models.chunk import Chunk
from app.models.citation import Citation
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.enums import (
    DocumentStatus,
    DocumentType,
    ProcessingJobStage,
    ProcessingJobStatus,
    UserRole,
    ValidationStatus,
)
from app.models.evaluation_run import EvaluationRun
from app.models.processing_job import ProcessingJob
from app.models.research_answer import ResearchAnswer
from app.models.research_query import ResearchQuery
from app.models.research_session import ResearchSession
from app.models.saved_research import SavedResearch
from app.models.system_event import SystemEvent
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.models.validation_item import ValidationItem

__all__ = [
    "Chunk",
    "Citation",
    "Document",
    "DocumentStatus",
    "DocumentType",
    "DocumentVersion",
    "EvaluationRun",
    "ProcessingJob",
    "ProcessingJobStage",
    "ProcessingJobStatus",
    "ResearchAnswer",
    "ResearchQuery",
    "ResearchSession",
    "SavedResearch",
    "SystemEvent",
    "SystemSetting",
    "User",
    "UserRole",
    "ValidationItem",
    "ValidationStatus",
]
