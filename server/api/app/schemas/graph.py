"""Admin Knowledge Graph schemas (Phase 16)."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class GraphNodeSchema(BaseModel):
    id: str
    label: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdgeSchema(BaseModel):
    id: str
    sourceId: str
    targetId: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphSearchResponse(BaseModel):
    nodes: list[GraphNodeSchema]
    total: int


class GraphNeighborsResponse(BaseModel):
    center_node: GraphNodeSchema | None = None
    nodes: list[GraphNodeSchema]
    edges: list[GraphEdgeSchema]
    depth: int


class GraphSubgraphResponse(BaseModel):
    nodes: list[GraphNodeSchema]
    edges: list[GraphEdgeSchema]
