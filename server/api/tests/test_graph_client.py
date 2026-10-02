"""Neo4j client validation and in-memory replacement semantics."""

from __future__ import annotations

import inspect

import pytest

from app.core.config import Settings
from app.graph.client import GraphError, Neo4jClient
from tests.fake_neo4j import FakeNeo4jClient, InMemoryGraph


@pytest.mark.asyncio
async def test_merge_node_rejects_invalid_label() -> None:
    client = Neo4jClient(Settings(session_secret="test"))
    with pytest.raises(GraphError):
        await client.merge_node("NotALabel", {"id": "x"})


@pytest.mark.asyncio
async def test_merge_relationship_requires_provenance_key() -> None:
    client = Neo4jClient(Settings(session_secret="test"))
    with pytest.raises(GraphError):
        await client.merge_relationship("a", "b", "CONTAINS", {})


def test_in_memory_merge_uses_label_and_id() -> None:
    graph = InMemoryGraph()
    graph.merge_node("Article", {"id": "article:a:1", "name": "Article 1", "confidence": 1.0})
    assert graph.nodes["article:a:1"]["name"] == "Article 1"
    assert graph.node_labels["article:a:1"] == "Article"


def test_in_memory_relationship_merge_uses_provenance_key() -> None:
    graph = InMemoryGraph()
    graph.merge_node("Document", {"id": "doc-1", "title": "T", "document_type": "act"})
    graph.merge_node("Chunk", {"id": "chunk-1", "document_id": "doc-1", "chunk_index": 0})
    props = {
        "provenance_key": "pk-1",
        "document_id": "doc-1",
        "chunk_id": "chunk-1",
        "confidence": 1.0,
        "extraction_method": "deterministic_rule",
    }
    graph.merge_relationship("doc-1", "chunk-1", "CONTAINS", props)
    graph.merge_relationship("doc-1", "chunk-1", "CONTAINS", props)
    contains = [rel for rel in graph.relationships if rel.type == "CONTAINS"]
    assert len(contains) == 1


def _minimal_payload(doc_id: str, chunk_id: str, *, with_act: bool = True) -> dict:
    shared_act = {"label": "Act", "id": "act:ipc", "name": "IPC", "confidence": 1.0}
    return {
        "document_id": doc_id,
        "document": {"id": doc_id, "title": doc_id, "document_type": "act"},
        "chunks": [
            {
                "id": chunk_id,
                "document_id": doc_id,
                "chunk_index": 0,
                "page_start": None,
                "page_end": None,
                "citation_ref": None,
                "hierarchy_json": {},
                "provenance_key": f"pk-{chunk_id}",
                "extraction_method": "deterministic_rule",
            }
        ],
        "entity_nodes": [shared_act] if with_act else [],
        "supported_by": (
            [
                {
                    "source_id": "act:ipc",
                    "target_id": chunk_id,
                    "provenance_key": f"sb-{chunk_id}",
                    "document_id": doc_id,
                    "chunk_id": chunk_id,
                    "confidence": 1.0,
                    "extraction_method": "deterministic_rule",
                }
            ]
            if with_act
            else []
        ),
        "defines": [],
    }


@pytest.mark.asyncio
async def test_replace_document_graph_uses_single_execute_write() -> None:
    client = Neo4jClient(Settings(session_secret="test"))
    calls: list[int] = []

    async def fake_execute_write(work: object) -> None:
        calls.append(1)

        class _Tx:
            async def run(self, *_args: object, **_kwargs: object) -> None:
                return None

        await work(_Tx())  # type: ignore[misc, operator]

    client.execute_write = fake_execute_write  # type: ignore[method-assign]
    await client.replace_document_graph(_minimal_payload("doc-1", "chunk-1"))
    assert calls == [1]


def test_replace_document_graph_cypher_is_document_scoped_and_transactional() -> None:
    source = inspect.getsource(Neo4jClient.replace_document_graph)
    assert "execute_write(_replace)" in source
    assert "DETACH DELETE c" in source
    assert "DETACH DELETE d" in source
    assert "document_id: $document_id" in source
    assert "NOT (n)-[:SUPPORTED_BY]->(:Chunk)" in source
    assert "MATCH (n) DETACH DELETE n" not in source


def test_document_scoped_replacement_removes_old_chunks() -> None:
    graph = InMemoryGraph()
    payload_v1 = {
        "document_id": "doc-1",
        "document": {"id": "doc-1", "title": "Act", "document_type": "act"},
        "chunks": [
            {
                "id": "chunk-old",
                "document_id": "doc-1",
                "chunk_index": 0,
                "page_start": 1,
                "page_end": 1,
                "citation_ref": None,
                "hierarchy_json": {},
                "provenance_key": "pk-old",
                "extraction_method": "deterministic_rule",
            }
        ],
        "entity_nodes": [],
        "supported_by": [],
        "defines": [],
    }
    graph.replace_document_graph(payload_v1)
    payload_v2 = dict(payload_v1)
    payload_v2["chunks"] = [
        {
            **payload_v1["chunks"][0],
            "id": "chunk-new",
            "provenance_key": "pk-new",
        }
    ]
    graph.replace_document_graph(payload_v2)
    assert "chunk-old" not in graph.nodes
    assert "chunk-new" in graph.nodes


def test_shared_entity_survives_other_document_replacement() -> None:
    graph = InMemoryGraph()
    graph.replace_document_graph(_minimal_payload("doc-a", "chunk-a"))
    graph.replace_document_graph(_minimal_payload("doc-b", "chunk-b"))
    graph.replace_document_graph(_minimal_payload("doc-a", "chunk-a2", with_act=False))
    assert "act:ipc" in graph.nodes
    assert "doc-b" in graph.nodes
    assert "chunk-b" in graph.nodes
    assert "chunk-a" not in graph.nodes
    supported = [rel for rel in graph.relationships if rel.type == "SUPPORTED_BY"]
    assert any(rel.source_id == "act:ipc" and rel.target_id == "chunk-b" for rel in supported)
    assert any(rel.type == "CONTAINS" and rel.source_id == "doc-b" for rel in graph.relationships)


def test_mid_transaction_failure_rolls_back_previous_graph() -> None:
    graph = InMemoryGraph()
    graph.replace_document_graph(_minimal_payload("doc-a", "chunk-a"))
    graph.fail_after_delete = True
    with pytest.raises(RuntimeError, match="mid-transaction"):
        graph.replace_document_graph(_minimal_payload("doc-a", "chunk-a2"))
    assert "chunk-a" in graph.nodes
    assert "chunk-a2" not in graph.nodes
    assert "act:ipc" in graph.nodes


def test_orphan_entities_removed_after_replacement() -> None:
    graph = InMemoryGraph()
    payload = {
        "document_id": "doc-1",
        "document": {"id": "doc-1", "title": "Act", "document_type": "act"},
        "chunks": [
            {
                "id": "chunk-1",
                "document_id": "doc-1",
                "chunk_index": 0,
                "page_start": None,
                "page_end": None,
                "citation_ref": None,
                "hierarchy_json": {},
                "provenance_key": "pk-1",
                "extraction_method": "deterministic_rule",
            }
        ],
        "entity_nodes": [
            {"label": "Concept", "id": "concept:act:person", "name": "person", "confidence": 0.9}
        ],
        "supported_by": [
            {
                "source_id": "concept:act:person",
                "target_id": "chunk-1",
                "provenance_key": "sb-1",
                "document_id": "doc-1",
                "chunk_id": "chunk-1",
                "confidence": 0.9,
                "extraction_method": "deterministic_rule",
            }
        ],
        "defines": [],
    }
    graph.replace_document_graph(payload)
    empty = {**payload, "entity_nodes": [], "supported_by": [], "defines": []}
    graph.replace_document_graph(empty)
    assert "concept:act:person" not in graph.nodes
    assert graph.statistics()["orphan_legal_entities"] == 0


def test_statistics_counts() -> None:
    graph = InMemoryGraph()
    graph.merge_node("Document", {"id": "d1", "title": "T", "document_type": "act"})
    graph.merge_node("Chunk", {"id": "c1", "document_id": "d1", "chunk_index": 0})
    graph.merge_relationship(
        "d1",
        "c1",
        "CONTAINS",
        {
            "provenance_key": "pk",
            "document_id": "d1",
            "chunk_id": "c1",
            "confidence": 1.0,
            "extraction_method": "deterministic_rule",
        },
    )
    stats = graph.statistics()
    assert stats["nodes_by_label"]["Document"] == 1
    assert stats["relationships_by_type"]["CONTAINS"] == 1


@pytest.mark.asyncio
async def test_traverse_empty_seeds_returns_empty() -> None:
    client = Neo4jClient(Settings(session_secret="test"))
    assert await client.traverse([], max_hops=2, max_nodes=10) == []


def test_expand_supported_chunks_is_bounded_two_hop_supported_by() -> None:
    source = inspect.getsource(Neo4jClient.expand_supported_chunks)
    assert "SUPPORTED_BY" in source
    assert "candidate.id <> seed.id" in source or "candidate.id != seed.id" in source
    assert "LIMIT $max_paths" in source
    assert "execute_read" in source
    assert "CONTAINS" not in source
    assert "DEFINES" not in source
    assert "traverse(" not in source
    traverse_source = inspect.getsource(Neo4jClient.traverse)
    assert "rels*1.." in traverse_source


@pytest.mark.asyncio
async def test_expand_supported_chunks_empty_or_shallow_skips_driver() -> None:
    client = Neo4jClient(Settings(session_secret="test", graph_max_hops=1))
    assert await client.expand_supported_chunks(["seed"], max_paths=10) == []
    client.settings = Settings(session_secret="test", graph_max_hops=2)
    assert await client.expand_supported_chunks([], max_paths=10) == []


@pytest.mark.asyncio
async def test_fake_client_clear_flag() -> None:
    client = FakeNeo4jClient()
    client.graph.merge_node("Document", {"id": "d1", "title": "T", "document_type": "act"})
    await client.clear_graph()
    assert client.graph.cleared
    assert client.graph.nodes == {}
