"""Multi-Hop Graph Traversal and Graph Retrieval Module (Phase 14).

Performs controlled multi-hop graph retrieval over Neo4j with depth bounds,
cycle prevention, provenance tracking, and layout coordinates for UI rendering.
"""

from __future__ import annotations

import logging
from typing import Any, Literal
from app.graph.client import GraphError, Neo4jClient

logger = logging.getLogger(__name__)


def compute_node_layout(
    nodes: list[dict[str, Any]],
    query_name: str = "Query",
) -> list[dict[str, Any]]:
    """Assign deterministic 2D SVG coordinates (x, y) for UI rendering."""
    if not nodes:
        return []

    positioned: list[dict[str, Any]] = []
    # Seed/Query node at top center
    query_node = {
        "id": "node_query",
        "label": query_name[:30],
        "type": "QUERY",
        "x": 380,
        "y": 60,
        "isQuery": True,
    }
    positioned.append(query_node)

    # Group remaining nodes by type / seed status
    seeds = [n for n in nodes if n.get("isSeed")]
    others = [n for n in nodes if not n.get("isSeed")]

    # Position seed nodes in second row
    seed_count = len(seeds)
    for idx, node in enumerate(seeds):
        x = 180 + (400 / max(1, seed_count - 1)) * idx if seed_count > 1 else 380
        positioned.append({
            **node,
            "x": int(x),
            "y": 180,
        })

    # Position candidate/target nodes in third row
    other_count = len(others)
    for idx, node in enumerate(others):
        x = 120 + (520 / max(1, other_count - 1)) * idx if other_count > 1 else 380
        y = 300 + (idx % 2) * 60
        positioned.append({
            **node,
            "x": int(x),
            "y": int(y),
        })

    return positioned


async def fetch_entity_nodes_by_ids(
    graph_client: Neo4jClient,
    entity_ids: list[str],
) -> list[dict[str, Any]]:
    """Look up entity nodes in Neo4j by their canonical IDs."""
    if not entity_ids:
        return []

    driver = await graph_client._driver_for_use()
    query = """
        MATCH (n)
        WHERE n.id IN $entity_ids
        RETURN n.id AS id, labels(n) AS labels, properties(n) AS props
    """
    try:
        async with driver.session(database=graph_client.settings.neo4j_database) as session:
            result = await session.run(query, entity_ids=entity_ids)
            rows = [record async for record in result]
    except Exception as exc:
        logger.warning("Failed to fetch entity nodes by IDs: %s", exc)
        return []

    nodes: list[dict[str, Any]] = []
    for r in rows:
        labels = r["labels"] or []
        label = next((l for l in labels if l != "Chunk"), "Concept")
        props = r["props"] or {}
        nodes.append({
            "id": r["id"],
            "label": props.get("name") or r["id"],
            "type": label.upper(),
            "properties": props,
            "isSeed": True,
        })
    return nodes


async def traverse_multi_hop(
    graph_client: Neo4jClient,
    seed_entity_ids: list[str],
    seed_chunk_ids: list[str],
    max_hops: int = 3,
    max_nodes: int = 30,
    mode: str | None = None,
) -> dict[str, Any]:
    """Execute bounded multi-hop traversal starting from seed entities or seed chunks.

    Returns structured nodes, edges, multi-hop paths, and supporting chunk IDs.
    """
    hops = min(max(max_hops, 1), 5)
    limit = min(max(max_nodes, 1), 50)

    all_seed_ids = list(dict.fromkeys(seed_entity_ids + seed_chunk_ids))
    if not all_seed_ids:
        return {
            "nodes": [],
            "edges": [],
            "paths": [],
            "supporting_chunk_ids": [],
            "has_graph_evidence": False,
        }

    driver = await graph_client._driver_for_use()

    # Cypher query performing bounded path traversal while returning node/edge details
    query = f"""
        MATCH p=(seed)-[rels*1..{hops}]-(target)
        WHERE seed.id IN $seed_ids
          AND ALL(x IN nodes(p) WHERE single(y IN nodes(p) WHERE y = x))  -- prevent cycles
        WITH p, rels, nodes(p) AS n_list
        LIMIT $limit
        RETURN
          [n IN n_list | {{
            id: n.id,
            labels: labels(n),
            name: COALESCE(n.name, n.title, n.id),
            properties: properties(n)
          }}] AS path_nodes,
          [r IN rels | {{
            type: type(r),
            source_id: startNode(r).id,
            target_id: endNode(r).id,
            provenance_key: r.provenance_key,
            confidence: r.confidence,
            document_id: r.document_id,
            chunk_id: r.chunk_id,
            page: r.page,
            evidence_text: r.evidence_text
          }}] AS path_relationships
    """

    try:
        async with driver.session(database=graph_client.settings.neo4j_database) as session:
            result = await session.run(query, seed_ids=all_seed_ids, limit=limit)
            raw_paths = [record async for record in result]
    except Exception as exc:
        logger.warning("Multi-hop Neo4j traversal failed: %s", exc)
        return {
            "nodes": [],
            "edges": [],
            "paths": [],
            "supporting_chunk_ids": [],
            "has_graph_evidence": False,
        }

    seen_nodes: dict[str, dict[str, Any]] = {}
    seen_edges: dict[str, dict[str, Any]] = {}
    paths_summary: list[dict[str, Any]] = []
    supporting_chunk_ids: set[str] = set()

    for idx, path_record in enumerate(raw_paths, start=1):
        path_nodes = path_record.get("path_nodes") or []
        path_rels = path_record.get("path_relationships") or []

        path_desc_parts: list[str] = []

        for node_info in path_nodes:
            nid = str(node_info.get("id"))
            if not nid:
                continue

            labels = node_info.get("labels") or []
            label_type = next((l for l in labels if l != "Chunk"), "Concept")

            if nid not in seen_nodes:
                is_seed = nid in all_seed_ids
                seen_nodes[nid] = {
                    "id": nid,
                    "label": str(node_info.get("name") or nid),
                    "type": label_type.upper(),
                    "isSeed": is_seed,
                    "properties": node_info.get("properties") or {},
                }

            if label_type == "Chunk":
                supporting_chunk_ids.add(nid)

            path_desc_parts.append(str(node_info.get("name") or nid))

        for rel in path_rels:
            src = str(rel.get("source_id"))
            tgt = str(rel.get("target_id"))
            rel_type = str(rel.get("type"))
            edge_id = f"edge_{src}_{rel_type}_{tgt}"

            if edge_id not in seen_edges:
                seen_edges[edge_id] = {
                    "id": edge_id,
                    "sourceId": src,
                    "targetId": tgt,
                    "label": rel_type,
                    "confidence": rel.get("confidence", 1.0),
                    "provenanceKey": rel.get("provenance_key"),
                    "documentId": rel.get("document_id"),
                    "chunkId": rel.get("chunk_id"),
                    "page": rel.get("page"),
                    "evidenceText": rel.get("evidence_text", ""),
                }

            if rel.get("chunk_id"):
                supporting_chunk_ids.add(str(rel["chunk_id"]))

        paths_summary.append({
            "path_id": f"path_{idx}",
            "hop_count": len(path_rels),
            "description": " → ".join(path_desc_parts),
            "node_ids": [n.get("id") for n in path_nodes],
            "relationship_types": [r.get("type") for r in path_rels],
        })

    nodes_list = list(seen_nodes.values())
    edges_list = list(seen_edges.values())

    return {
        "nodes": nodes_list,
        "edges": edges_list,
        "paths": paths_summary,
        "supporting_chunk_ids": sorted(supporting_chunk_ids),
        "has_graph_evidence": len(nodes_list) > 0,
    }
