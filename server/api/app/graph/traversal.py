"""Multi-Hop Graph Traversal and Graph Retrieval Module (Phase 14).

Performs controlled multi-hop graph retrieval over Neo4j with depth bounds,
cycle prevention, provenance tracking, and layout coordinates for UI rendering.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal
from app.graph.client import GraphError, Neo4jClient

logger = logging.getLogger(__name__)

_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _normalize_entity_type(labels: list[str]) -> str:
    """Map raw Neo4j graph labels to canonical legal entity type."""
    cleaned = [l for l in labels if l != "Chunk"]
    if not cleaned:
        if "Chunk" in labels:
            return "CHUNK"
        return "PRINCIPLE"

    primary = cleaned[0].upper()
    type_map = {
        "ARTICLE": "ARTICLE",
        "SECTION": "SECTION",
        "ACT": "ACT",
        "STATUTE": "ACT",
        "CONSTITUTION": "ACT",
        "JUDGMENT": "JUDGMENT",
        "COURT": "COURT",
        "AMENDMENT": "AMENDMENT",
        "CONSTITUTIONAL_AMENDMENT": "AMENDMENT",
        "DOCTRINE": "PRINCIPLE",
        "PRINCIPLE": "PRINCIPLE",
        "CONCEPT": "PRINCIPLE",
        "RULE": "RULE",
        "REGULATION": "RULE",
    }
    return type_map.get(primary, "PRINCIPLE")


def _normalize_node_display_name(node_info: dict[str, Any], entity_type: str) -> str:
    """Normalize node display name: eliminate raw UUIDs in user-facing labels."""
    props = node_info.get("properties") or {}

    raw_name = str(node_info.get("name") or props.get("name") or props.get("title") or "").strip()
    if raw_name and not _UUID_PATTERN.match(raw_name):
        return raw_name

    ref = props.get("citation_ref")
    doc_title = props.get("document_title") or props.get("source_title")
    chunk_idx = props.get("chunk_index")

    if ref:
        return str(ref)
    if doc_title and chunk_idx is not None:
        return f"{doc_title} (Chunk {chunk_idx})"
    if doc_title:
        return str(doc_title)
    if chunk_idx is not None:
        return f"Passage Chunk {chunk_idx}"

    type_fallbacks = {
        "ARTICLE": "Constitutional Article",
        "SECTION": "Statutory Section",
        "ACT": "Statute Authority",
        "JUDGMENT": "Judicial Precedent",
        "COURT": "Judicial Authority",
        "AMENDMENT": "Constitutional Amendment",
        "PRINCIPLE": "Legal Principle",
        "RULE": "Legal Rule",
        "CHUNK": "Document Passage",
    }
    return type_fallbacks.get(entity_type, "Legal Authority")


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
        entity_type = _normalize_entity_type(labels)
        props = r["props"] or {}
        display_label = _normalize_node_display_name(
            {"id": r["id"], "name": props.get("name"), "properties": props},
            entity_type,
        )
        nodes.append({
            "id": r["id"],
            "label": display_label,
            "type": entity_type,
            "properties": props,
            "isSeed": True,
        })
    return nodes


async def traverse_multi_hop(
    graph_client: Neo4jClient,
    seed_entity_ids: list[str] | None = None,
    seed_chunk_ids: list[str] | None = None,
    max_hops: int = 3,
    max_nodes: int = 30,
    mode: str | None = None,
) -> dict[str, Any]:
    """Execute bounded multi-hop traversal starting from seed entities or seed chunks.

    Returns structured nodes, edges, multi-hop paths, and supporting chunk IDs with actual hop counts.
    """
    hops = min(max(max_hops, 1), 5)
    limit = min(max(max_nodes, 1), 50)

    entity_ids = seed_entity_ids or []
    chunk_ids = seed_chunk_ids or []
    all_seed_ids = list(dict.fromkeys(entity_ids + chunk_ids))
    if not all_seed_ids:
        return {
            "nodes": [],
            "edges": [],
            "paths": [],
            "supporting_chunk_ids": [],
            "chunk_hop_distance": {},
            "has_graph_evidence": False,
        }

    driver = await graph_client._driver_for_use()

    # Cypher query performing bounded path traversal while returning node/edge details
    query = f"""
        MATCH p=(seed)-[rels*1..{hops}]-(target)
        WHERE seed.id IN $seed_ids
          AND ALL(x IN nodes(p) WHERE single(y IN nodes(p) WHERE y = x))
        LIMIT $limit
        RETURN nodes(p) AS path_nodes, relationships(p) AS path_relationships
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
            "chunk_hop_distance": {},
            "has_graph_evidence": False,
        }

    seen_nodes: dict[str, dict[str, Any]] = {}
    seen_edges: dict[str, dict[str, Any]] = {}
    paths_summary: list[dict[str, Any]] = []
    supporting_chunk_ids: set[str] = set()
    chunk_hop_distance: dict[str, int] = {}

    for idx, path_record in enumerate(raw_paths, start=1):
        raw_nodes = path_record.get("path_nodes") or []
        raw_rels = path_record.get("path_relationships") or []

        path_nodes: list[dict[str, Any]] = []
        for n in raw_nodes:
            if hasattr(n, "items"):
                props = dict(n)
                labels = list(getattr(n, "labels", []))
                nid = str(props.get("id") or "")
                path_nodes.append({
                    "id": nid,
                    "labels": labels,
                    "name": props.get("name") or props.get("title") or nid,
                    "properties": props,
                })
            elif isinstance(n, dict):
                path_nodes.append(n)

        path_rels: list[dict[str, Any]] = []
        for rel in raw_rels:
            if hasattr(rel, "items"):
                props = dict(rel)
                rel_type = getattr(rel, "type", "")
                src_node = getattr(rel, "start_node", None)
                tgt_node = getattr(rel, "end_node", None)
                src_id = str(src_node.get("id") if src_node and hasattr(src_node, "get") else props.get("source_id", ""))
                tgt_id = str(tgt_node.get("id") if tgt_node and hasattr(tgt_node, "get") else props.get("target_id", ""))
                path_rels.append({
                    "type": rel_type,
                    "source_id": src_id,
                    "target_id": tgt_id,
                    **props,
                })
            elif isinstance(rel, dict):
                path_rels.append(rel)

        actual_path_hop_count = len(path_rels)

        path_desc_parts: list[str] = []

        for node_info in path_nodes:
            nid = str(node_info.get("id"))
            if not nid:
                continue

            labels = node_info.get("labels") or []
            entity_type = _normalize_entity_type(labels)
            display_label = _normalize_node_display_name(node_info, entity_type)

            if nid not in seen_nodes:
                is_seed = nid in all_seed_ids
                seen_nodes[nid] = {
                    "id": nid,
                    "label": display_label,
                    "type": entity_type,
                    "isSeed": is_seed,
                    "properties": node_info.get("properties") or {},
                }

            if entity_type == "CHUNK" or "Chunk" in labels:
                supporting_chunk_ids.add(nid)
                if nid not in chunk_hop_distance or actual_path_hop_count < chunk_hop_distance[nid]:
                    chunk_hop_distance[nid] = actual_path_hop_count

            path_desc_parts.append(display_label)

        for hop_idx, rel in enumerate(path_rels, start=1):
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

            cid = str(rel.get("chunk_id") or "")
            if cid:
                supporting_chunk_ids.add(cid)
                if cid not in chunk_hop_distance or hop_idx < chunk_hop_distance[cid]:
                    chunk_hop_distance[cid] = hop_idx

        paths_summary.append({
            "path_id": f"path_{idx}",
            "hop_count": actual_path_hop_count,
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
        "chunk_hop_distance": chunk_hop_distance,
        "has_graph_evidence": len(nodes_list) > 0,
    }
