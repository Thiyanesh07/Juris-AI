"""HTTP contracts for legal QA, GraphRAG, and Temporal Citation Reasoning (Phase 14 & 15)."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.hybrid import HybridEvidence


class QAAskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str = Field(min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1)
    mode: Literal["COMPREHENSIVE", "CONSTITUTIONAL", "STATUTORY", "CASE_LAW"] | None = Field(
        default="COMPREHENSIVE"
    )
    retrieval_strategy: Literal["hybrid", "vector_only", "graph_only"] | None = Field(
        default="hybrid"
    )
    graph_depth: int | None = Field(default=None, ge=1, le=5)


class QACitation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    marker: int
    evidence_rank: int
    chunk_id: UUID
    document_id: UUID
    document_title: str
    document_version_id: UUID | None = None
    chunk_index: int
    citation_ref: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    source_url: str | None = None


class QARetrievalMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["hybrid", "vector_only", "graph_only"] = "hybrid"
    fallback: Literal["dense_only"] | None = None
    fallback_reason: Literal[
        "neo4j_unavailable",
        "neo4j_timeout",
        "neo4j_query_failed",
    ] | None = None
    warnings: list[str] = Field(default_factory=list)
    evidence_count: int
    evidence_dropped_for_context: int = 0


class QATimingsMs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    retrieval: int
    llm: int


class QAGraphNode(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    label: str
    type: str
    x: int = 0
    y: int = 0
    isQuery: bool | None = None
    isSeed: bool | None = None


class QAGraphEdge(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    sourceId: str
    targetId: str
    label: str


class QAGraphData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nodes: list[QAGraphNode] = Field(default_factory=list)
    edges: list[QAGraphEdge] = Field(default_factory=list)
    available: bool = False


class QAReasoningStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step: int
    description: str
    entityName: str | None = None
    relationLabel: str | None = None
    targetEntityName: str | None = None


# Phase 15 Temporal & Citation Validation Models
class QATimelineEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    year: str
    title: str
    documentType: str
    description: str
    importance: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"


class QATemporalMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    detected: bool = False
    target_date: str | None = None
    target_year: int | None = None
    date_range: dict[str, int | None] | None = None
    temporal_operator: str = "CURRENT_LAW"
    referenced_amendment: str | None = None
    resolution_status: str = "UNKNOWN"
    applicable_versions: list[dict[str, Any]] = Field(default_factory=list)
    timeline_events: list[QATimelineEvent] = Field(default_factory=list)


class QACitationValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verified_count: int = 0
    unverified_count: int = 0
    grounded: bool = True
    warnings: list[str] = Field(default_factory=list)


class QAAskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str
    status: Literal["answered", "insufficient_evidence"]
    answer: str | None
    insufficient_evidence: bool
    citations: list[QACitation]
    evidence: list[HybridEvidence]
    graph: QAGraphData | None = Field(default=None)
    reasoning_steps: list[QAReasoningStep] = Field(default_factory=list)
    query_analysis: dict[str, Any] | None = Field(default=None)
    temporal: QATemporalMeta | None = Field(default=None)
    citation_validation: QACitationValidation | None = Field(default=None)
    retrieval: QARetrievalMeta
    provider: str
    model: str
    llm_called: bool
    timings_ms: QATimingsMs
    disclaimer: str = "Informational research aid. Not legal advice."
