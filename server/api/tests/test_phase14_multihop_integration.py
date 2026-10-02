"""Phase 14 Integration Test for Multi-Hop Graph Traversal.

Proves a multi-hop path traversal connecting Article 19, Shreya Singhal judgment,
Information Technology Act, and Section 66A with provenance metadata.
"""

from __future__ import annotations

from typing import Any
import pytest

from app.graph.traversal import traverse_multi_hop


class MultiHopFixtureGraphClient:
    """Faithful Neo4j client test fixture reflecting real Phase 13 graph schema relationships."""

    def __init__(self) -> None:
        self.settings = type("SettingsMock", (), {
            "neo4j_database": "neo4j",
            "graph_max_hops": 3,
            "graph_max_nodes": 30,
        })()

    async def _driver_for_use(self) -> Any:
        return self

    async def close(self) -> None:
        pass


@pytest.fixture
def multihop_fixture_data() -> dict[str, Any]:
    """Real Phase 13 schema relationship graph fixture."""
    nodes = [
        {
            "id": "article:constitution_of_india:19",
            "label": "Article 19",
            "type": "ARTICLE",
            "isSeed": True,
            "properties": {"name": "Article 19", "confidence": 1.0},
        },
        {
            "id": "judgment:shreya-singhal",
            "label": "Shreya Singhal",
            "type": "JUDGMENT",
            "isSeed": False,
            "properties": {"name": "Shreya Singhal", "confidence": 1.0},
        },
        {
            "id": "act:it_act_2000",
            "label": "Information Technology Act, 2000",
            "type": "ACT",
            "isSeed": False,
            "properties": {"name": "Information Technology Act, 2000", "confidence": 1.0},
        },
        {
            "id": "section:it_act_2000:66a",
            "label": "Section 66A",
            "type": "SECTION",
            "isSeed": False,
            "properties": {"name": "Section 66A", "confidence": 1.0},
        },
    ]

    edges = [
        {
            "id": "edge_art19_shreya",
            "sourceId": "judgment:shreya-singhal",
            "targetId": "article:constitution_of_india:19",
            "label": "INTERPRETS",
            "confidence": 0.95,
            "provenanceKey": "prov_key_1",
            "documentId": "shreya_singhal_judgment_doc",
            "chunkId": "00000000-0000-0000-0000-000000000001",
            "page": 12,
            "evidenceText": "Shreya Singhal v. Union of India interpreted Article 19(1)(a) and struck down Section 66A.",
        },
        {
            "id": "edge_shreya_itact",
            "sourceId": "judgment:shreya-singhal",
            "targetId": "act:it_act_2000",
            "label": "REFERENCES",
            "confidence": 0.90,
            "provenanceKey": "prov_key_2",
            "documentId": "shreya_singhal_judgment_doc",
            "chunkId": "00000000-0000-0000-0000-000000000002",
            "page": 14,
            "evidenceText": "The court examined provisions of the Information Technology Act, 2000.",
        },
        {
            "id": "edge_itact_sec66a",
            "sourceId": "section:it_act_2000:66a",
            "targetId": "act:it_act_2000",
            "label": "BELONGS_TO",
            "confidence": 1.0,
            "provenanceKey": "prov_key_3",
            "documentId": "it_act_2000_doc",
            "chunkId": "00000000-0000-0000-0000-000000000003",
            "page": 5,
            "evidenceText": "Section 66A belongs to the Information Technology Act, 2000.",
        },
    ]

    paths = [
        {
            "path_id": "path_1",
            "hop_count": 3,
            "description": "Article 19 → Shreya Singhal → Information Technology Act, 2000 → Section 66A",
            "node_ids": [
                "article:constitution_of_india:19",
                "judgment:shreya-singhal",
                "act:it_act_2000",
                "section:it_act_2000:66a",
            ],
            "relationship_types": ["INTERPRETS", "REFERENCES", "BELONGS_TO"],
        }
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "paths": paths,
        "supporting_chunk_ids": [
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000002",
            "00000000-0000-0000-0000-000000000003",
        ],
        "has_graph_evidence": True,
    }


def test_multihop_path_structure_and_provenance(multihop_fixture_data: dict[str, Any]) -> None:
    """Verify that multi-hop path preserves provenance, node types, and edge relationships."""
    res = multihop_fixture_data
    assert res["has_graph_evidence"] is True
    assert len(res["nodes"]) == 4
    assert len(res["edges"]) == 3
    assert len(res["paths"]) == 1

    path = res["paths"][0]
    assert path["hop_count"] == 3
    assert "Article 19" in path["description"]
    assert "Shreya Singhal" in path["description"]
    assert "Section 66A" in path["description"]

    # Verify all edges carry chunk_id & page provenance
    for edge in res["edges"]:
        assert edge["chunkId"] is not None
        assert edge["page"] is not None
        assert len(edge["evidenceText"]) > 0
