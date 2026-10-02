"""Admin Knowledge Graph API Routes (Phase 16).

Provides read-only multi-hop Neo4j Cypher querying for entity search, node inspection,
and neighbor/subgraph traversal with strict depth bounding (default 3, max 5).
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import require_admin
from app.graph.client import Neo4jClient
from app.graph.traversal import traverse_multi_hop
from app.schemas.graph import (
    GraphEdgeSchema,
    GraphNeighborsResponse,
    GraphNodeSchema,
    GraphSearchResponse,
    GraphSubgraphResponse,
)

router = APIRouter(prefix="/graph", tags=["graph_admin"])


from app.core.config import Settings, get_settings

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
    if not graph_client._driver:
        return GraphSearchResponse(nodes=[], total=0)

    cypher = """
    MATCH (n)
    WHERE (n.name IS NOT NULL AND toLower(n.name) CONTAINS toLower($q))
       OR (n.id IS NOT NULL AND toLower(n.id) CONTAINS toLower($q))
       OR (n.title IS NOT NULL AND toLower(n.title) CONTAINS toLower($q))
    """
    if entity_type:
        cypher += f" AND (n:{entity_type} OR labels(n)[0] = $etype)"

    cypher += " RETURN n, labels(n)[0] AS label_type LIMIT $limit"

    nodes: list[GraphNodeSchema] = []
    try:
        async with graph_client._driver.session(database=graph_client._database) as session:
            result = await session.run(cypher, q=query.strip(), etype=entity_type, limit=limit)
            records = await result.data()
            for r in records:
                node_obj = r["n"]
                label = r["label_type"] or "Entity"
                node_id = str(node_obj.get("id") or node_obj.get("name") or "")
                name = str(node_obj.get("name") or node_obj.get("title") or node_id)
                nodes.append(
                    GraphNodeSchema(
                        id=node_id,
                        label=name,
                        type=label,
                        properties=dict(node_obj),
                    )
                )
    except Exception:
        pass

    return GraphSearchResponse(nodes=nodes, total=len(nodes))


@router.get("/nodes/{node_id}", response_model=GraphNodeSchema)
async def get_graph_node(
    node_id: str,
    current_user: Any = Depends(require_admin),
    graph_client: Neo4jClient = Depends(get_graph_client),
) -> GraphNodeSchema:
    """Get single node attributes by ID."""
    if not graph_client._driver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")

    cypher = "MATCH (n {id: $node_id}) RETURN n, labels(n)[0] AS label_type LIMIT 1"
    try:
        async with graph_client._driver.session(database=graph_client._database) as session:
            result = await session.run(cypher, node_id=node_id)
            record = await result.single()
            if record:
                node_obj = record["n"]
                label = record["label_type"] or "Entity"
                name = str(node_obj.get("name") or node_obj.get("title") or node_id)
                return GraphNodeSchema(
                    id=node_id,
                    label=name,
                    type=label,
                    properties=dict(node_obj),
                )
    except Exception:
        pass

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")


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

    if not graph_client._driver:
        return GraphNeighborsResponse(center_node=None, nodes=[], edges=[], depth=bounded_depth)

    res = await traverse_multi_hop(
        client=graph_client,
        seed_entity_ids=[node_id],
        hops=bounded_depth,
        limit_per_hop=limit,
    )

    nodes = [
        GraphNodeSchema(
            id=str(n.get("id")),
            label=str(n.get("label") or n.get("name") or n.get("id")),
            type=str(n.get("type") or "Entity"),
        )
        for n in res.get("nodes", [])
    ]
    edges = [
        GraphEdgeSchema(
            id=str(e.get("id")),
            sourceId=str(e.get("sourceId")),
            targetId=str(e.get("targetId")),
            label=str(e.get("label")),
        )
        for e in res.get("edges", [])
    ]

    center = next((n for n in nodes if n.id == node_id), None)
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

    if not graph_client._driver:
        return GraphSubgraphResponse(nodes=[], edges=[])

    res = await traverse_multi_hop(
        client=graph_client,
        seed_entity_ids=node_ids,
        hops=bounded_depth,
        limit_per_hop=30,
    )

    nodes = [
        GraphNodeSchema(
            id=str(n.get("id")),
            label=str(n.get("label") or n.get("name") or n.get("id")),
            type=str(n.get("type") or "Entity"),
        )
        for n in res.get("nodes", [])
    ]
    edges = [
        GraphEdgeSchema(
            id=str(e.get("id")),
            sourceId=str(e.get("sourceId")),
            targetId=str(e.get("targetId")),
            label=str(e.get("label")),
        )
        for e in res.get("edges", [])
    ]

    return GraphSubgraphResponse(nodes=nodes, edges=edges)
