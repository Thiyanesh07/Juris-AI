"""HTTP contracts for hybrid dense+graph evidence retrieval."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class HybridRetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str = Field(min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1)


class HybridGraphEntityContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    label: str
    name: str


class HybridGraphContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hops: int = 2
    seed_chunk_ids: list[str]
    entities: list[HybridGraphEntityContext]


class HybridEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rank: int
    chunk_id: UUID
    document_id: UUID
    document_title: str
    document_version_id: UUID | None = None
    chunk_index: int
    text: str
    page_start: int | None = None
    page_end: int | None = None
    hierarchy: dict[str, Any]
    citation_ref: str | None = None
    source_url: str | None = None
    dense_score: float
    graph_score: float
    hybrid_score: float
    dense_rank: int | None = None
    graph_rank: int | None = None
    dense_matched: bool
    evidence_sources: list[Literal["dense", "graph"]]
    graph_context: HybridGraphContext | None = None


class HybridWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vector: float
    graph: float


class HybridRetrievalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str
    mode: Literal["hybrid"] = "hybrid"
    fallback: Literal["dense_only"] | None = None
    fallback_reason: Literal[
        "neo4j_unavailable",
        "neo4j_timeout",
        "neo4j_query_failed",
    ] | None = None
    weights: HybridWeights
    score_type: str = (
        "hybrid = vector_weight * clamp(cosine, 0, 1) + graph_weight * graph_support"
    )
    warnings: list[str] = Field(default_factory=list)
    results: list[HybridEvidence]
