"""Admin Knowledge Graph API Routes (Phase 16).

Provides read-only multi-hop Neo4j Cypher querying for entity search, node inspection,
and neighbor/subgraph traversal with strict depth bounding (default 3, max 5).
"""

import logging
from typing import Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.graph.client import Neo4jClient
from app.graph.traversal import traverse_multi_hop
from app.schemas.graph import (
    GraphEdgeSchema,
    GraphNeighborsResponse,
    GraphNodeSchema,
    GraphSearchResponse,
    GraphSubgraphResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph_admin"])


def get_graph_client(settings: Settings = Depends(get_settings)) -> Neo4jClient:
    """Dependency returning Neo4j graph client instance."""
    return Neo4jClient(settings)


@router.get("/search", response_model=GraphSearchResponse)
async def search_graph_nodes(
    query: str = Query(..., min_length=1, description="Search query string"),
    entity_type: str | None = Query(None, description="Optional entity label filter"),
    limit: int = Query(20, ge=1, le=100),
    current_user: Any = Depends(require_admin),
    graph_client: Neo4jClient = Depends(get_graph_client),
) -> GraphSearchResponse:
    """Search legal entity nodes in Neo4j knowledge graph."""
    cypher = """
    MATCH (n)
    WHERE (n.name IS NOT NULL AND toLower(n.name) CONTAINS toLower($q))
       OR (n.id IS NOT NULL AND toLower(n.id) CONTAINS toLower($q))
       OR (n.title IS NOT NULL AND toLower(n.title) CONTAINS toLower($q))
    """
    params: dict[str, Any] = {"q": query.strip(), "limit": limit}
    if entity_type and entity_type.upper() != "ALL":
        cypher += " AND ANY(lbl IN labels(n) WHERE toUpper(lbl) = toUpper($etype))"
        params["etype"] = entity_type

    cypher += " RETURN n, [lbl IN labels(n) WHERE lbl <> 'Chunk'][0] AS label_type LIMIT $limit"

    nodes: list[GraphNodeSchema] = []
    try:
        driver = await graph_client._driver_for_use()
        async with driver.session(database=graph_client.settings.neo4j_database) as session:
            result = await session.run(cypher, **params)
            records = [record async for record in result]
            for r in records:
                node_obj = dict(r["n"])
                label = r["label_type"] or (r["n"].labels[0] if hasattr(r["n"], "labels") and r["n"].labels else "Entity")
                node_id = str(node_obj.get("id") or node_obj.get("name") or "")
                name = str(node_obj.get("name") or node_obj.get("title") or node_id)
                nodes.append(
                    GraphNodeSchema(
                        id=node_id,
                        label=name,
                        type=str(label),
                        properties=node_obj,
                    )
                )
    except Exception as exc:
        logger.error("Neo4j graph search failed for query %r: %s", query, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge graph database is currently unavailable",
        )

    return GraphSearchResponse(nodes=nodes, total=len(nodes))


@router.get("/nodes/{node_id}", response_model=GraphNodeSchema)
async def get_graph_node(
    node_id: str,
    current_user: Any = Depends(require_admin),
    graph_client: Neo4jClient = Depends(get_graph_client),
) -> GraphNodeSchema:
    """Get single node attributes by ID."""
    cypher = "MATCH (n {id: $node_id}) RETURN n, [lbl IN labels(n) WHERE lbl <> 'Chunk'][0] AS label_type LIMIT 1"
    try:
        driver = await graph_client._driver_for_use()
        async with driver.session(database=graph_client.settings.neo4j_database) as session:
            result = await session.run(cypher, node_id=node_id)
            record = await result.single()
            if record:
                node_obj = dict(record["n"])
                label = record["label_type"] or (record["n"].labels[0] if hasattr(record["n"], "labels") and record["n"].labels else "Entity")
                name = str(node_obj.get("name") or node_obj.get("title") or node_id)
                return GraphNodeSchema(
                    id=node_id,
                    label=name,
                    type=str(label),
                    properties=node_obj,
                )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Neo4j get_node failed for %s: %s", node_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge graph database is currently unavailable",
        )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found")


@router.get("/neighbors/{node_id}", response_model=GraphNeighborsResponse)
async def get_graph_neighbors(
    node_id: str,
    depth: int = Query(3, ge=1, le=5, description="Traversal depth (default 3, max 5)"),
    limit: int = Query(50, ge=1, le=200),
    current_user: Any = Depends(require_admin),
    graph_client: Neo4jClient = Depends(get_graph_client),
) -> GraphNeighborsResponse:
    """Retrieve multi-hop neighbors surrounding a target node (bounded depth 1–5)."""
    bounded_depth = min(max(depth, 1), 5)

    try:
        res = await traverse_multi_hop(
            graph_client=graph_client,
            seed_entity_ids=[node_id],
            seed_chunk_ids=[],
            max_hops=bounded_depth,
            max_nodes=limit,
        )
    except Exception as exc:
        logger.error("Multi-hop traversal failed for node %s: %s", node_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge graph database is currently unavailable",
        )

    nodes = [
        GraphNodeSchema(
            id=str(n.get("id")),
            label=str(n.get("label") or n.get("name") or n.get("id")),
            type=str(n.get("type") or "Entity"),
            properties=dict(n.get("properties") or {}),
        )
        for n in res.get("nodes", [])
    ]
    edges = [
        GraphEdgeSchema(
            id=str(e.get("id")),
            sourceId=str(e.get("sourceId")),
            targetId=str(e.get("targetId")),
            label=str(e.get("label")),
            properties={
                k: v for k, v in e.items()
                if k not in ("id", "sourceId", "targetId", "label")
            },
        )
        for e in res.get("edges", [])
    ]

    center = next((n for n in nodes if n.id == node_id), None)
    if not center:
        # Check if center node exists standalone in Neo4j
        try:
            center_record = await get_graph_node(node_id, current_user, graph_client)
            center = center_record
            if center not in nodes:
                nodes.insert(0, center)
        except HTTPException:
            pass

    return GraphNeighborsResponse(center_node=center, nodes=nodes, edges=edges, depth=bounded_depth)


@router.get("/subgraph", response_model=GraphSubgraphResponse)
async def get_subgraph(
    node_ids: list[str] = Query(..., description="List of seed node IDs"),
    depth: int = Query(2, ge=1, le=5),
    current_user: Any = Depends(require_admin),
    graph_client: Neo4jClient = Depends(get_graph_client),
) -> GraphSubgraphResponse:
    """Retrieve connected subgraph spanning multiple seed node IDs."""
    bounded_depth = min(max(depth, 1), 5)

    try:
        res = await traverse_multi_hop(
            graph_client=graph_client,
            seed_entity_ids=node_ids,
            seed_chunk_ids=[],
            max_hops=bounded_depth,
            max_nodes=min(max(len(node_ids) * 20, 20), 100),
        )
    except Exception as exc:
        logger.error("Subgraph traversal failed for node_ids %s: %s", node_ids, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge graph database is currently unavailable",
        )

    nodes = [
        GraphNodeSchema(
            id=str(n.get("id")),
            label=str(n.get("label") or n.get("name") or n.get("id")),
            type=str(n.get("type") or "Entity"),
            properties=dict(n.get("properties") or {}),
        )
        for n in res.get("nodes", [])
    ]
    edges = [
        GraphEdgeSchema(
            id=str(e.get("id")),
            sourceId=str(e.get("sourceId")),
            targetId=str(e.get("targetId")),
            label=str(e.get("label")),
            properties={
                k: v for k, v in e.items()
                if k not in ("id", "sourceId", "targetId", "label")
            },
        )
        for e in res.get("edges", [])
    ]

    return GraphSubgraphResponse(nodes=nodes, edges=edges)


@router.post("/populate", summary="Trigger knowledge graph population for eligible documents (admin only)")
async def trigger_graph_population(
    document_id: UUID | None = Query(None, description="Optional single document ID to populate"),
    limit: int | None = Query(None, ge=1, le=100, description="Optional maximum number of documents to populate"),
    clear: bool = Query(False, description="Whether to clear graph first if populating all documents"),
    current_user: Any = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    graph_client: Neo4jClient = Depends(get_graph_client),
) -> dict[str, Any]:
    """Trigger graph population for eligible documents (READY, or FAILED with chunks)."""
    from app.graph.population import populate_graph

    try:
        summary = await populate_graph(
            session,
            graph_client,
            document_id=document_id,
            limit=limit,
            clear=clear,
        )
        return summary.to_dict()
    except Exception as exc:
        logger.error("Graph population execution failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph population failed: {exc}",
        )

