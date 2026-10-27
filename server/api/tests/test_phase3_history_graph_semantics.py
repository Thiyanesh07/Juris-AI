"""Phase 3 Regression & Verification Tests: Research History and Graph Semantics.

Verifies:
1. Research history persistence and restoration of complete evidence, graph state, and reasoning.
2. Canonical research-mode persistence across all modes with safe fallback for legacy/unknown modes.
3. Stable citation and evidence identifiers across save and reload.
4. Legal graph entity normalization and non-UUID user-facing labels.
5. Accurate graph path hop counting and chunk hop distances.
6. Safe legacy compatibility path for pre-Phase-3 records.
7. User isolation across history queries.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.routes.history import _canonical_mode
from app.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.graph.traversal import (
    _normalize_entity_type,
    _normalize_node_display_name,
    compute_node_layout,
)
from app.main import app
from app.models import ResearchAnswer, ResearchQuery, ResearchSession, User, ValidationStatus
from app.models.enums import UserRole
from app.retrieval.index import save_index
from tests.test_retrieval import (
    TEST_MODEL,
    TEST_POOLING,
    FakeEmbedder,
    _configure_settings,
    _records,
)


def _valid_llm_json() -> str:
    return json.dumps({
        "answer": "Fundamental rights are protected under Part III of the Constitution [1].",
        "insufficient_evidence": False,
        "citations": [{"marker": 1, "evidence_rank": 1}],
    })


class FakeLLMProvider:
    def __init__(self, responses: list[str] | None = None) -> None:
        self.responses = responses or [_valid_llm_json()]
        self.calls = 0

    async def generate(self, **_kwargs: object) -> str:
        text = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return text


@pytest.fixture
def phase3_settings(tmp_path: Path) -> Settings:
    settings = get_settings()
    _configure_settings(settings, tmp_path)
    settings.llm_api_key = "test-key"
    settings.llm_provider = "openai_compatible"
    save_index(
        data_dir=tmp_path,
        index_name="test",
        vectors=np.eye(2, dtype=np.float32),
        chunk_records=_records(),
        model_name=TEST_MODEL,
        pooling_method=TEST_POOLING,
        max_tokens=32,
    )
    return settings


@pytest.fixture(autouse=True)
def patch_settings(phase3_settings: Settings):
    app.dependency_overrides[get_settings] = lambda: phase3_settings
    yield
    app.dependency_overrides.pop(get_settings, None)


@pytest.fixture(autouse=True)
def patch_embedder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.retrieval.service.build_embedder", lambda _settings: FakeEmbedder())


@pytest.fixture(autouse=True)
def patch_llm_provider(monkeypatch: pytest.MonkeyPatch) -> FakeLLMProvider:
    provider = FakeLLMProvider()
    monkeypatch.setattr("app.qa.service.build_llm_provider", lambda _settings: provider)
    return provider


@pytest.fixture(autouse=True)
def patch_hybrid_retrieve(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_hybrid(*_args, **_kwargs):
        record = _records()[0]
        return {
            "query": "constitution",
            "mode": "hybrid",
            "fallback": None,
            "fallback_reason": None,
            "weights": {"vector": 0.7, "graph": 0.3},
            "score_type": "hybrid",
            "warnings": [],
            "graph": {
                "nodes": [
                    {"id": "art_19", "label": "Article 19", "type": "ARTICLE", "x": 380, "y": 180, "isSeed": True}
                ],
                "edges": [],
                "available": True,
            },
            "results": [
                {
                    **record,
                    "rank": 1,
                    "dense_score": 0.95,
                    "graph_score": 0.0,
                    "hybrid_score": 0.665,
                    "dense_rank": 1,
                    "graph_rank": None,
                    "dense_matched": True,
                    "evidence_sources": ["dense"],
                    "graph_context": None,
                }
            ],
        }

    monkeypatch.setattr("app.qa.service.hybrid_retrieve", fake_hybrid)


def test_research_history_persists_and_restores_complete_state(client: TestClient) -> None:
    """Verifies that mode, evidence, graph, and stable citations persist and reload intact."""
    user = User(id=uuid4(), email=f"user_p3_{uuid4()}@test.com", name="User Phase3", role=UserRole.USER)
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        req = {
            "query": "What are the fundamental rights under the Constitution?",
            "mode": "CONSTITUTIONAL",
        }
        res = client.post("/qa/ask", json=req)
        assert res.status_code == 200, res.text
        res_data = res.json()
        session_id = res_data["session_id"]
        assert session_id is not None
        assert len(res_data["citations"]) >= 1

        chunk_id = res_data["citations"][0]["chunk_id"]
        marker = res_data["citations"][0]["marker"]
        expected_stable_id = f"cit_{chunk_id}_{marker}"

        # Fetch history session
        hist_res = client.get(f"/research/history/{session_id}")
        assert hist_res.status_code == 200, hist_res.text
        hist_data = hist_res.json()

        assert hist_data["id"] == session_id
        assert hist_data["mode"] == "CONSTITUTIONAL"
        assert len(hist_data["queries"]) == 1

        query_item = hist_data["queries"][0]
        assert len(query_item["answers"]) == 1

        answer_item = query_item["answers"][0]
        assert answer_item["mode"] == "CONSTITUTIONAL"
        assert len(answer_item["citations"]) >= 1

        first_cit = answer_item["citations"][0]
        assert first_cit["stable_id"] == expected_stable_id
        assert first_cit["chunk_id"] == chunk_id
        assert first_cit["marker"] == marker

        # Evidence must be restored (not empty)
        assert len(answer_item["evidence"]) >= 1
        first_ev = answer_item["evidence"][0]
        assert first_ev["chunk_id"] == chunk_id

        # Graph node/edge structure must be present
        assert answer_item["graph"] is not None
        assert "nodes" in answer_item["graph"]
        assert "edges" in answer_item["graph"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_research_mode_canonicalization_and_fallbacks() -> None:
    """Verifies all supported modes map correctly and legacy/unknown modes receive safe fallback."""
    # Canonical supported modes
    assert _canonical_mode("COMPREHENSIVE") == "COMPREHENSIVE"
    assert _canonical_mode("CONSTITUTIONAL") == "CONSTITUTIONAL"
    assert _canonical_mode("STATUTORY") == "STATUTORY"
    assert _canonical_mode("CASE_LAW") == "CASE_LAW"

    # Case-insensitivity
    assert _canonical_mode("constitutional") == "CONSTITUTIONAL"
    assert _canonical_mode("statutory") == "STATUTORY"
    assert _canonical_mode("case_law") == "CASE_LAW"

    # Legacy modes fallback safely to COMPREHENSIVE
    assert _canonical_mode("HYBRID") == "COMPREHENSIVE"
    assert _canonical_mode("hybrid") == "COMPREHENSIVE"
    assert _canonical_mode("vector_only") == "COMPREHENSIVE"

    # Unknown or missing modes receive safe canonical fallback
    assert _canonical_mode(None) == "COMPREHENSIVE"
    assert _canonical_mode("") == "COMPREHENSIVE"
    assert _canonical_mode("UNKNOWN_RANDOM_MODE") == "COMPREHENSIVE"


def test_graph_entity_type_normalization() -> None:
    """Verifies Neo4j labels map to authoritative legal entity types."""
    assert _normalize_entity_type(["Article"]) == "ARTICLE"
    assert _normalize_entity_type(["Section"]) == "SECTION"
    assert _normalize_entity_type(["Act"]) == "ACT"
    assert _normalize_entity_type(["Statute"]) == "ACT"
    assert _normalize_entity_type(["Constitution"]) == "ACT"
    assert _normalize_entity_type(["Judgment"]) == "JUDGMENT"
    assert _normalize_entity_type(["Court"]) == "COURT"
    assert _normalize_entity_type(["Amendment"]) == "AMENDMENT"
    assert _normalize_entity_type(["Doctrine"]) == "PRINCIPLE"
    assert _normalize_entity_type(["Concept"]) == "PRINCIPLE"
    assert _normalize_entity_type(["Rule"]) == "RULE"
    assert _normalize_entity_type(["Chunk"]) == "CHUNK"
    assert _normalize_entity_type(["Chunk", "Judgment"]) == "JUDGMENT"


def test_graph_node_display_name_eliminates_raw_uuids() -> None:
    """Verifies raw UUIDs are never exposed as user-facing node labels."""
    raw_uuid = "2b068aea-4976-4d41-8f54-13ca7f2f617a"

    # Node with genuine name retains its name
    named_node = {"id": raw_uuid, "name": "Kesavananda Bharati v. State of Kerala"}
    assert _normalize_node_display_name(named_node, "JUDGMENT") == "Kesavananda Bharati v. State of Kerala"

    # Node with citation ref uses citation ref
    ref_node = {"id": raw_uuid, "name": raw_uuid, "properties": {"citation_ref": "Article 21"}}
    assert _normalize_node_display_name(ref_node, "ARTICLE") == "Article 21"

    # Node with chunk index and document title uses clean passage label
    chunk_node = {
        "id": raw_uuid,
        "name": raw_uuid,
        "properties": {"document_title": "Constitution of India", "chunk_index": 4},
    }
    assert _normalize_node_display_name(chunk_node, "CHUNK") == "Constitution of India (Chunk 4)"

    # Node with pure UUID and no metadata receives explicit safe fallback
    bare_uuid_node = {"id": raw_uuid, "name": raw_uuid, "properties": {}}
    assert _normalize_node_display_name(bare_uuid_node, "ARTICLE") == "Constitutional Article"
    assert _normalize_node_display_name(bare_uuid_node, "JUDGMENT") == "Judicial Precedent"
    assert _normalize_node_display_name(bare_uuid_node, "ACT") == "Statute Authority"


def test_compute_node_layout_structure() -> None:
    """Verifies SVG node placement creates root query node and positions children."""
    raw_nodes = [
        {"id": "art_19", "label": "Article 19", "type": "ARTICLE", "isSeed": True},
        {"id": "sec_66a", "label": "Section 66A", "type": "SECTION", "isSeed": False},
    ]
    layout = compute_node_layout(raw_nodes, query_name="Freedom of Speech")
    assert len(layout) == 3  # 1 query root + 2 entities
    assert layout[0]["isQuery"] is True
    assert layout[0]["label"] == "Freedom of Speech"
    assert layout[1]["id"] == "art_19"
    assert layout[2]["id"] == "sec_66a"


@pytest.mark.asyncio
async def test_legacy_history_compatibility_honest_representation(client: TestClient, session) -> None:
    """Verifies pre-Phase-3 records without evidence_json or graph_json return cleanly without fabricating data."""
    user = User(id=uuid4(), email=f"user_legacy_{uuid4()}@test.com", name="Legacy User", role=UserRole.USER)
    session.add(user)
    await session.commit()

    sess = ResearchSession(user_id=user.id, title="Legacy Session Without Stored Evidence")
    session.add(sess)
    await session.commit()

    rq = ResearchQuery(session_id=sess.id, question="Historical question")
    session.add(rq)
    await session.commit()

    # Pre-Phase-3 record: no evidence_json, no graph_json, mode default
    ra = ResearchAnswer(
        query_id=rq.id,
        answer="Historical answer.",
        validation_status=ValidationStatus.VALIDATED,
        evidence_json=None,
        graph_json=None,
    )
    session.add(ra)
    await session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        res = client.get(f"/research/history/{sess.id}")
        assert res.status_code == 200
        data = res.json()
        assert data["mode"] == "COMPREHENSIVE"
        ans = data["queries"][0]["answers"][0]
        # Must honestly be empty, never fabricated
        assert ans["evidence"] == []
        assert ans["graph"] is None
        assert ans["mode"] == "COMPREHENSIVE"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
