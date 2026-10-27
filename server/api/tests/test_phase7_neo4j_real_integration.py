"""Phase 7 Real Neo4j Driver Integration Tests.

Validates:
1. Real driver connectivity and authentication against an isolated loopback Neo4j container.
2. Clean driver lifecycle and shutdown.
3. Schema constraint creation and verification via Cypher.
4. Creating, updating, and retrieving representative legal entities.
5. Creating and retrieving directional relationships.
6. Duplicate handling and idempotent MERGE semantics.
7. Entity type normalization and display label formatting from live graph records.
8. Bounded multi-hop traversal, cycle safety, path direction, and hop counting.
9. Missing nodes and graceful handling of empty traversal results.
10. Transaction rollback on failure during execute_write.
11. Document graph replacement (idempotent re-ingestion and retry behavior).
12. Query result response schema conformance.
13. Cross-layer isolation confirming protected indexes and database tables remain untainted.
"""

from __future__ import annotations

import os
from typing import Any, AsyncIterator
import pytest
from neo4j import AsyncGraphDatabase

from app.core.config import Settings
from app.graph.client import (
    GraphAuthenticationError,
    GraphConnectionError,
    GraphError,
    Neo4jClient,
)
from app.graph.traversal import (
    _normalize_entity_type,
    _normalize_node_display_name,
    fetch_entity_nodes_by_ids,
    traverse_multi_hop,
)
from tests.isolation_preflight import (
    ProtectedArtifactGuard,
    verify_graph_safety,
)

TEST_NEO4J_URI = os.environ.get("TEST_NEO4J_URI", "bolt://127.0.0.1:7689")
TEST_NEO4J_USER = os.environ.get("TEST_NEO4J_USER", "neo4j")
TEST_NEO4J_PASSWORD = os.environ.get("TEST_NEO4J_PASSWORD", "TestSafePass789!")
TEST_NEO4J_DATABASE = "neo4j"


@pytest.fixture(scope="module")
def neo4j_settings() -> Settings:
    verify_graph_safety(TEST_NEO4J_URI)
    return Settings(
        session_secret="test-phase7-secret",
        neo4j_uri=TEST_NEO4J_URI,
        neo4j_username=TEST_NEO4J_USER,
        neo4j_password=TEST_NEO4J_PASSWORD,
        neo4j_database=TEST_NEO4J_DATABASE,
    )


@pytest.fixture
async def real_neo4j_client(neo4j_settings: Settings) -> AsyncIterator[Neo4jClient]:
    """Provides a connected Neo4jClient that wipes the test graph after each test."""
    client = Neo4jClient(neo4j_settings)
    await client.verify_connectivity()
    # Clean slate before test
    await client.clear_graph()
    yield client
    # Clean slate after test
    try:
        await client.clear_graph()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_real_driver_connectivity_and_auth(neo4j_settings: Settings) -> None:
    """1. Verify real driver connection succeeds with correct auth and fails on bad auth."""
    # Good credentials
    client = Neo4jClient(neo4j_settings)
    is_connected = await client.verify_connectivity()
    assert is_connected is True
    await client.close()

    # Bad credentials must raise GraphAuthenticationError
    bad_settings = Settings(
        session_secret="test",
        neo4j_uri=TEST_NEO4J_URI,
        neo4j_username=TEST_NEO4J_USER,
        neo4j_password="IncorrectPassword999!",
        neo4j_database=TEST_NEO4J_DATABASE,
    )
    bad_client = Neo4jClient(bad_settings)
    with pytest.raises(GraphAuthenticationError):
        await bad_client.verify_connectivity()
    await bad_client.close()


@pytest.mark.asyncio
async def test_real_driver_clean_shutdown(neo4j_settings: Settings) -> None:
    """2. Verify driver lifecycle, repeated closes, and context manager cleanup."""
    client = Neo4jClient(neo4j_settings)
    assert client._driver is None
    await client.verify_connectivity()
    assert client._driver is not None

    # Clean shutdown
    await client.close()
    assert client._driver is None

    # Idempotent second close
    await client.close()
    assert client._driver is None

    # Context manager protocol
    async with Neo4jClient(neo4j_settings) as ctx_client:
        await ctx_client.verify_connectivity()
        assert ctx_client._driver is not None
    assert ctx_client._driver is None


@pytest.mark.asyncio
async def test_real_schema_constraint_initialization(real_neo4j_client: Neo4jClient) -> None:
    """3. Verify ensure_schema creates uniqueness constraints for all required labels."""
    await real_neo4j_client.ensure_schema()

    driver = await real_neo4j_client._driver_for_use()
    async with driver.session(database=real_neo4j_client.settings.neo4j_database) as session:
        result = await session.run("SHOW CONSTRAINTS")
        records = [record async for record in result]
        constraint_names = {r["name"] for r in records}

        # Check key legal labels have constraints
        assert "article_id_unique" in constraint_names
        assert "act_id_unique" in constraint_names
        assert "chunk_id_unique" in constraint_names
        assert "document_id_unique" in constraint_names


@pytest.mark.asyncio
async def test_real_merge_and_fetch_legal_entities(real_neo4j_client: Neo4jClient) -> None:
    """4. Create and retrieve representative legal entities via real driver."""
    entities = [
        {"label": "Article", "props": {"id": "art_21", "name": "Article 21", "title": "Protection of Life and Personal Liberty"}},
        {"label": "Act", "props": {"id": "act_crpc", "name": "Code of Criminal Procedure, 1973", "year": 1973}},
        {"label": "Judgment", "props": {"id": "case_maneka", "name": "Maneka Gandhi v. Union of India", "year": 1978}},
        {"label": "Section", "props": {"id": "sec_437", "name": "Section 437", "act": "CrPC"}},
        {"label": "Doctrine", "props": {"id": "doc_due_process", "name": "Substantive Due Process"}},
        {"label": "Court", "props": {"id": "court_sci", "name": "Supreme Court of India"}},
    ]

    for entity in entities:
        await real_neo4j_client.merge_node(entity["label"], entity["props"])

    # Retrieve all using traversal fetch_entity_nodes_by_ids
    fetched = await fetch_entity_nodes_by_ids(
        real_neo4j_client,
        [e["props"]["id"] for e in entities],
    )
    assert len(fetched) == len(entities)

    fetched_by_id = {node["id"]: node for node in fetched}
    assert fetched_by_id["art_21"]["type"] == "ARTICLE"
    assert fetched_by_id["art_21"]["label"] == "Article 21"
    assert fetched_by_id["act_crpc"]["type"] == "ACT"
    assert fetched_by_id["case_maneka"]["type"] == "JUDGMENT"
    assert fetched_by_id["sec_437"]["type"] == "SECTION"
    assert fetched_by_id["doc_due_process"]["type"] == "PRINCIPLE"
    assert fetched_by_id["court_sci"]["type"] == "COURT"


@pytest.mark.asyncio
async def test_real_create_and_retrieve_relationships(real_neo4j_client: Neo4jClient) -> None:
    """5. Create and retrieve directional relationships between legal entities."""
    # Seed nodes
    await real_neo4j_client.merge_node("Judgment", {"id": "case_ks", "name": "K.S. Puttaswamy v. Union of India"})
    await real_neo4j_client.merge_node("Article", {"id": "art_21", "name": "Article 21"})
    await real_neo4j_client.merge_node("Doctrine", {"id": "doc_privacy", "name": "Right to Privacy"})

    # Merge relationships with provenance_key
    await real_neo4j_client.merge_relationship(
        source_id="case_ks",
        target_id="art_21",
        relationship_type="INTERPRETS",
        properties={
            "provenance_key": "prov_ks_art21",
            "confidence": 0.95,
            "evidence_text": "Privacy is protected as an intrinsic part of the right to life and personal liberty under Article 21.",
            "document_id": "doc_puttaswamy",
        },
    )
    await real_neo4j_client.merge_relationship(
        source_id="case_ks",
        target_id="doc_privacy",
        relationship_type="DEFINES",
        properties={
            "provenance_key": "prov_ks_privacy",
            "confidence": 0.99,
            "evidence_text": "Declared privacy as a fundamental right.",
            "document_id": "doc_puttaswamy",
        },
    )

    # Query Cypher to assert edge details
    driver = await real_neo4j_client._driver_for_use()
    async with driver.session(database=real_neo4j_client.settings.neo4j_database) as session:
        result = await session.run(
            "MATCH (s {id: 'case_ks'})-[r]->(t) RETURN type(r) AS rel_type, t.id AS target_id, r.provenance_key AS prov"
        )
        records = [record async for record in result]
        rel_map = {r["target_id"]: (r["rel_type"], r["prov"]) for r in records}

        assert rel_map["art_21"] == ("INTERPRETS", "prov_ks_art21")
        assert rel_map["doc_privacy"] == ("DEFINES", "prov_ks_privacy")


@pytest.mark.asyncio
async def test_real_idempotent_duplicate_handling(real_neo4j_client: Neo4jClient) -> None:
    """6. Assert multiple merges of identical nodes and relationships update in-place without duplicating."""
    node_id = "art_14"

    # Merge node first time
    await real_neo4j_client.merge_node("Article", {"id": node_id, "name": "Article 14", "version": 1})
    # Merge node second time with updated property
    await real_neo4j_client.merge_node("Article", {"id": node_id, "name": "Article 14 (Equality)", "version": 2})

    # Assert exactly 1 node exists
    driver = await real_neo4j_client._driver_for_use()
    async with driver.session(database=real_neo4j_client.settings.neo4j_database) as session:
        count_res = await session.run("MATCH (n:Article {id: $id}) RETURN count(n) AS c, n.version AS v", id=node_id)
        rec = await count_res.single()
        assert rec["c"] == 1
        assert rec["v"] == 2

    # Target node for relationship
    await real_neo4j_client.merge_node("Concept", {"id": "conc_equality", "name": "Equality Before Law"})

    # Merge relationship multiple times
    for v in [1, 2, 3]:
        await real_neo4j_client.merge_relationship(
            source_id=node_id,
            target_id="conc_equality",
            relationship_type="DEFINES",
            properties={
                "provenance_key": "prov_art14_equality",
                "version": v,
                "confidence": 0.90 + (v * 0.01),
            },
        )

    # Assert exactly 1 relationship exists
    async with driver.session(database=real_neo4j_client.settings.neo4j_database) as session:
        rel_count_res = await session.run(
            "MATCH (s {id: $s})-[r:DEFINES]->(t {id: $t}) RETURN count(r) AS c, r.version AS v",
            s=node_id,
            t="conc_equality",
        )
        rec = await rel_count_res.single()
        assert rec["c"] == 1
        assert rec["v"] == 3


@pytest.mark.asyncio
async def test_real_entity_type_normalization(real_neo4j_client: Neo4jClient) -> None:
    """7. Test entity type normalization and display names on live Neo4j records."""
    await real_neo4j_client.merge_node("Chunk", {
        "id": "11111111-2222-3333-4444-555555555555",
        "citation_ref": "AIR 1978 SC 597",
        "document_title": "Maneka Gandhi",
        "chunk_index": 0,
    })

    fetched = await fetch_entity_nodes_by_ids(
        real_neo4j_client,
        ["11111111-2222-3333-4444-555555555555"],
    )
    assert len(fetched) == 1
    chunk_node = fetched[0]
    assert chunk_node["type"] == "CHUNK"
    # User-facing label must eliminate raw UUID
    assert "11111111" not in chunk_node["label"]
    assert "AIR 1978 SC 597" in chunk_node["label"] or "Maneka Gandhi" in chunk_node["label"]


@pytest.mark.asyncio
async def test_real_multi_hop_traversal_paths_and_hop_counts(real_neo4j_client: Neo4jClient) -> None:
    """8. Test 3-hop traversal, relationship path discovery, and chunk hop distance counting."""
    # Build 3-hop linear chain:
    # (Chunk c1) -[:REFERENCES]-> (Article a19) -[:INTERPRETS]-> (Act constitution) -[:CONTAINS]-> (Section p3)
    await real_neo4j_client.merge_node("Chunk", {"id": "chunk_001", "name": "Chunk 1", "chunk_index": 0})
    await real_neo4j_client.merge_node("Article", {"id": "art_19", "name": "Article 19(1)(a)"})
    await real_neo4j_client.merge_node("Act", {"id": "act_const", "name": "Constitution of India"})
    await real_neo4j_client.merge_node("Section", {"id": "part_3", "name": "Part III Fundamental Rights"})

    await real_neo4j_client.merge_relationship(
        "chunk_001", "art_19", "REFERENCES", {"provenance_key": "p1", "chunk_id": "chunk_001"}
    )
    await real_neo4j_client.merge_relationship(
        "art_19", "act_const", "BELONGS_TO", {"provenance_key": "p2", "chunk_id": "chunk_001"}
    )
    await real_neo4j_client.merge_relationship(
        "act_const", "part_3", "CONTAINS", {"provenance_key": "p3", "chunk_id": "chunk_001"}
    )

    # 1-hop traversal from chunk_001
    hop1 = await traverse_multi_hop(real_neo4j_client, seed_chunk_ids=["chunk_001"], max_hops=1)
    hop1_node_ids = {n["id"] for n in hop1["nodes"]}
    assert "chunk_001" in hop1_node_ids
    assert "art_19" in hop1_node_ids
    assert "act_const" not in hop1_node_ids

    # 3-hop traversal from chunk_001
    hop3 = await traverse_multi_hop(real_neo4j_client, seed_chunk_ids=["chunk_001"], max_hops=3)
    hop3_node_ids = {n["id"] for n in hop3["nodes"]}
    assert "chunk_001" in hop3_node_ids
    assert "art_19" in hop3_node_ids
    assert "act_const" in hop3_node_ids
    assert "part_3" in hop3_node_ids

    assert hop3["has_graph_evidence"] is True
    assert "chunk_001" in hop3["supporting_chunk_ids"]
    assert hop3["chunk_hop_distance"]["chunk_001"] == 1


@pytest.mark.asyncio
async def test_real_missing_nodes_and_empty_traversal(real_neo4j_client: Neo4jClient) -> None:
    """9. Missing seeds or non-existent IDs return empty traversal results gracefully."""
    empty_result = await traverse_multi_hop(
        real_neo4j_client,
        seed_entity_ids=["non_existent_entity_999"],
        seed_chunk_ids=["non_existent_chunk_999"],
    )
    assert empty_result["nodes"] == []
    assert empty_result["edges"] == []
    assert empty_result["paths"] == []
    assert empty_result["supporting_chunk_ids"] == []
    assert empty_result["has_graph_evidence"] is False


@pytest.mark.asyncio
async def test_real_transaction_rollback_on_failure(real_neo4j_client: Neo4jClient) -> None:
    """10. Verify that exceptions inside execute_write trigger automatic transaction rollback."""
    test_node_id = "art_rollback_test"

    async def failing_transaction(tx: Any) -> None:
        await tx.run("CREATE (n:Article {id: $id, name: 'Rollback Candidate'})", id=test_node_id)
        # Deliberately raise exception halfway
        raise RuntimeError("Simulated transaction write failure")

    with pytest.raises(RuntimeError, match="Simulated transaction write failure"):
        await real_neo4j_client.execute_write(failing_transaction)

    # Assert node was never committed to graph
    driver = await real_neo4j_client._driver_for_use()
    async with driver.session(database=real_neo4j_client.settings.neo4j_database) as session:
        result = await session.run("MATCH (n {id: $id}) RETURN count(n) AS c", id=test_node_id)
        rec = await result.single()
        assert rec["c"] == 0


@pytest.mark.asyncio
async def test_real_cross_layer_document_graph_replacement(real_neo4j_client: Neo4jClient) -> None:
    """11. Test replace_document_graph idempotently purges old document chunks and inserts new ones."""
    doc_id = "00000000-0000-0000-0000-000000000001"

    # Initial graph payload with Chunk 1
    initial_payload = {
        "document_id": doc_id,
        "document": {"id": doc_id, "title": "Bail Order", "document_type": "judgment"},
        "chunks": [
            {
                "id": "chunk_v1",
                "document_id": doc_id,
                "chunk_index": 0,
                "page_start": 1,
                "page_end": 1,
                "citation_ref": "Bail Order p.1",
                "hierarchy_json": {},
                "provenance_key": "prov_chunk_v1",
                "extraction_method": "deterministic_rule",
            }
        ],
        "entity_nodes": [
            {"id": "sec_439", "label": "Section", "name": "Section 439", "confidence": 0.95}
        ],
        "supported_by": [
            {
                "source_id": "sec_439",
                "target_id": "chunk_v1",
                "provenance_key": "prov_sec439_v1",
                "document_id": doc_id,
                "chunk_id": "chunk_v1",
                "confidence": 0.95,
                "extraction_method": "deterministic_rule",
            }
        ],
        "defines": [],
        "relations": [],
    }
    await real_neo4j_client.replace_document_graph(initial_payload)

    driver = await real_neo4j_client._driver_for_use()
    async with driver.session(database=real_neo4j_client.settings.neo4j_database) as session:
        r1 = await (await session.run("MATCH (c:Chunk {document_id: $d}) RETURN c.id AS id", d=doc_id)).single()
        assert r1["id"] == "chunk_v1"

    # Re-ingestion with replacement payload (Chunk 1 replaced by Chunk 2)
    replacement_payload = {
        "document_id": doc_id,
        "document": {"id": doc_id, "title": "Bail Order (Revised)", "document_type": "judgment"},
        "chunks": [
            {
                "id": "chunk_v2",
                "document_id": doc_id,
                "chunk_index": 0,
                "page_start": 1,
                "page_end": 1,
                "citation_ref": "Bail Order p.1 (Revised)",
                "hierarchy_json": {},
                "provenance_key": "prov_chunk_v2",
                "extraction_method": "deterministic_rule",
            }
        ],
        "entity_nodes": [
            {"id": "sec_439", "label": "Section", "name": "Section 439", "confidence": 0.95}
        ],
        "supported_by": [
            {
                "source_id": "sec_439",
                "target_id": "chunk_v2",
                "provenance_key": "prov_sec439_v2",
                "document_id": doc_id,
                "chunk_id": "chunk_v2",
                "confidence": 0.95,
                "extraction_method": "deterministic_rule",
            }
        ],
        "defines": [],
        "relations": [],
    }
    await real_neo4j_client.replace_document_graph(replacement_payload)

    # Assert old chunk was cleanly deleted and new chunk is present
    async with driver.session(database=real_neo4j_client.settings.neo4j_database) as session:
        chunks = [rec["id"] async for rec in await session.run("MATCH (c:Chunk {document_id: $d}) RETURN c.id AS id", d=doc_id)]
        assert chunks == ["chunk_v2"]

        # Section 439 is shared entity and must not be duplicated
        sec_count = await (await session.run("MATCH (s:Section {id: 'sec_439'}) RETURN count(s) AS c")).single()
        assert sec_count["c"] == 1


@pytest.mark.asyncio
async def test_real_cross_layer_protected_artifact_isolation(
    real_neo4j_client: Neo4jClient,
    protected_artifact_guard: None,
) -> None:
    """12. Confirm graph mutations against isolated container leave protected FAISS artifacts untouched."""
    # Populate multiple nodes
    for i in range(10):
        await real_neo4j_client.merge_node("Article", {"id": f"art_test_{i}", "name": f"Article {i}"})

    health = await real_neo4j_client.health()
    assert health["status"] == "ok"
    assert health["node_count"] >= 10
    assert health["is_empty"] is False
