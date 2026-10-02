"""In-memory Neo4j stand-in for graph unit tests (no live database)."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from app.graph.client import GraphError

_LEGAL_ENTITY_LABELS = frozenset(
    {
        "Article",
        "Section",
        "Act",
        "Court",
        "Concept",
        "Amendment",
        "Judgment",
        "Rule",
        "Regulation",
        "Person",
        "Organization",
    }
)


@dataclass
class _Relationship:
    type: str
    source_id: str
    target_id: str
    properties: dict[str, Any]


@dataclass
class InMemoryGraph:
    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    node_labels: dict[str, str] = field(default_factory=dict)
    relationships: list[_Relationship] = field(default_factory=list)
    cleared: bool = False
    fail_after_delete: bool = False

    def _snapshot(self) -> tuple[dict[str, dict[str, Any]], dict[str, str], list[_Relationship]]:
        return (
            {node_id: dict(props) for node_id, props in self.nodes.items()},
            dict(self.node_labels),
            [
                _Relationship(rel.type, rel.source_id, rel.target_id, dict(rel.properties))
                for rel in self.relationships
            ],
        )

    def merge_node(self, label: str, properties: dict[str, Any]) -> None:
        if label not in _LEGAL_ENTITY_LABELS | {"Document", "Chunk"}:
            raise GraphError("Invalid graph node label or stable ID")
        node_id = properties.get("id")
        if not node_id:
            raise GraphError("Invalid graph node label or stable ID")
        self.nodes[node_id] = dict(properties)
        self.node_labels[node_id] = label

    def merge_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: dict[str, Any],
    ) -> None:
        if not properties.get("provenance_key"):
            raise GraphError("Relationship merge requires a provenance_key")
        self.relationships = [
            rel
            for rel in self.relationships
            if not (
                rel.type == relationship_type
                and rel.source_id == source_id
                and rel.target_id == target_id
                and rel.properties.get("provenance_key") == properties["provenance_key"]
            )
        ]
        self.relationships.append(
            _Relationship(relationship_type, source_id, target_id, dict(properties))
        )

    def clear(self) -> None:
        self.nodes.clear()
        self.node_labels.clear()
        self.relationships.clear()
        self.cleared = True

    def replace_document_graph(self, payload: dict[str, Any]) -> None:
        """Apply replacement atomically: restore the prior graph if anything fails."""
        snapshot = self._snapshot()
        try:
            self._apply_replace(payload)
        except Exception:
            self.nodes, self.node_labels, self.relationships = snapshot
            raise

    def _apply_replace(self, payload: dict[str, Any]) -> None:
        document_id = payload["document_id"]
        self.relationships = [
            rel
            for rel in self.relationships
            if not (rel.type == "DEFINES" and rel.properties.get("document_id") == document_id)
        ]
        old_chunk_ids = {
            node_id
            for node_id, label in self.node_labels.items()
            if label == "Chunk" and self.nodes[node_id].get("document_id") == document_id
        }
        removed_ids = old_chunk_ids | {document_id}
        self.relationships = [
            rel
            for rel in self.relationships
            if rel.source_id not in removed_ids and rel.target_id not in removed_ids
        ]
        for node_id in removed_ids:
            self.nodes.pop(node_id, None)
            self.node_labels.pop(node_id, None)

        orphan_ids = [
            node_id
            for node_id, label in self.node_labels.items()
            if label in _LEGAL_ENTITY_LABELS
            and not any(
                rel.type == "SUPPORTED_BY" and rel.source_id == node_id
                for rel in self.relationships
            )
        ]
        orphan_set = set(orphan_ids)
        self.relationships = [
            rel
            for rel in self.relationships
            if rel.source_id not in orphan_set and rel.target_id not in orphan_set
        ]
        for node_id in orphan_ids:
            self.nodes.pop(node_id, None)
            self.node_labels.pop(node_id, None)

        if self.fail_after_delete:
            self.fail_after_delete = False
            raise RuntimeError("simulated mid-transaction failure")

        document = payload["document"]
        self.merge_node("Document", document)
        for chunk in payload["chunks"]:
            self.merge_node(
                "Chunk",
                {
                    "id": chunk["id"],
                    "document_id": chunk["document_id"],
                    "chunk_index": chunk["chunk_index"],
                    "page_start": chunk["page_start"],
                    "page_end": chunk["page_end"],
                    "citation_ref": chunk["citation_ref"],
                    "hierarchy_json": chunk["hierarchy_json"],
                },
            )
            self.merge_relationship(
                document_id,
                chunk["id"],
                "CONTAINS",
                {
                    "provenance_key": chunk["provenance_key"],
                    "document_id": document_id,
                    "chunk_id": chunk["id"],
                    "confidence": 1.0,
                    "extraction_method": chunk["extraction_method"],
                },
            )
        for node in payload["entity_nodes"]:
            self.merge_node(node["label"], node)
        for rel in payload["supported_by"]:
            self.merge_relationship(
                rel["source_id"],
                rel["target_id"],
                "SUPPORTED_BY",
                rel,
            )
        for rel in payload["defines"]:
            self.merge_relationship(
                rel["source_id"],
                rel["target_id"],
                "DEFINES",
                rel,
            )

    def statistics(self) -> dict[str, Any]:
        nodes_by_label = Counter(self.node_labels.values())
        rels_by_type = Counter(rel.type for rel in self.relationships)
        orphans = sum(
            1
            for node_id, label in self.node_labels.items()
            if label in _LEGAL_ENTITY_LABELS
            and not any(
                rel.type == "SUPPORTED_BY" and rel.source_id == node_id
                for rel in self.relationships
            )
        )
        return {
            "nodes_by_label": dict(nodes_by_label),
            "relationships_by_type": dict(rels_by_type),
            "orphan_legal_entities": orphans,
        }


class FakeNeo4jClient:
    """Minimal async-compatible client surface used by population tests."""

    def __init__(self) -> None:
        self.graph = InMemoryGraph()
        self.schema_calls = 0
        self.fail_next_replace = False
        self.fail_after_delete = False

    async def ensure_schema(self) -> None:
        self.schema_calls += 1

    async def health(self) -> dict[str, Any]:
        return {"status": "ok", "name": "fake-neo4j", "version": "0"}

    async def statistics(self) -> dict[str, Any]:
        return self.graph.statistics()

    async def clear_graph(self) -> None:
        self.graph.clear()

    async def replace_document_graph(self, payload: dict[str, Any]) -> None:
        if self.fail_next_replace:
            self.fail_next_replace = False
            raise RuntimeError("simulated Neo4j failure")
        if self.fail_after_delete:
            self.fail_after_delete = False
            self.graph.fail_after_delete = True
        self.graph.replace_document_graph(payload)

    async def close(self) -> None:
        return None
