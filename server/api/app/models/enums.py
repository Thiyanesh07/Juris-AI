"""Application-level enums stored as native PostgreSQL enum types.

Member values (lowercase strings) are what get persisted; the member names
(USER, ADMIN, ...) are the Python-side identifiers.
"""

import enum


class UserRole(enum.StrEnum):
    """Role of an application user."""

    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class DocumentType(enum.StrEnum):
    """Kind of legal source registered in the document registry."""

    CONSTITUTION = "constitution"
    ACT = "act"
    STATUTE = "statute"
    JUDGMENT = "judgment"
    RULE = "rule"
    REGULATION = "regulation"
    CONSTITUTIONAL_AMENDMENT = "constitutional_amendment"
    NOTIFICATION = "notification"
    OTHER = "other"



class DocumentStatus(enum.StrEnum):
    """Lifecycle status of a registered legal document."""

    REGISTERED = "registered"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DISABLED = "disabled"


class ProcessingJobStage(enum.StrEnum):
    """Stages of the future document-processing pipeline."""

    INGESTION = "ingestion"
    EXTRACTION = "extraction"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    VECTOR_INDEX = "vector_index"
    ENTITY_EXTRACTION = "entity_extraction"
    RELATION_EXTRACTION = "relation_extraction"
    GRAPH_POPULATION = "graph_population"


class ProcessingJobStatus(enum.StrEnum):
    """Execution status of a processing job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ValidationStatus(enum.StrEnum):
    """Grounding/validation state of a generated answer."""

    PENDING = "pending"
    VALIDATED = "validated"
    WARNING = "warning"
    FAILED = "failed"
