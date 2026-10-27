"""Stage 3 Tests â€” Persistent Research History and User Isolation.

Verifies:
1. New query creates ResearchSession, ResearchQuery, ResearchAnswer, and Citation, returning session_id.
2. Follow-up query reusing session_id appends to the same ResearchSession.
3. Query with non-existent session_id returns 404.
4. User isolation: User B attempting to post to User A's session returns 403.
5. User B attempting to view User A's session returns 404.
6. History API returns full session structure with queries, answers, and citations.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.main import app
from app.models import User
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
    return json.dumps(
        {
            "answer": "Freedom of speech is protected under Article 19(1)(a) [1].",
            "insufficient_evidence": False,
            "citations": [{"marker": 1, "evidence_rank": 1}],
        }
    )


class FakeLLMProvider:
    def __init__(self, responses: list[str] | None = None) -> None:
        self.responses = responses or [_valid_llm_json()]
        self.calls = 0

    async def generate(self, **_kwargs: object) -> str:
        text = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return text


@pytest.fixture
def stage3_settings(tmp_path: Path) -> Settings:
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
def patch_settings(stage3_settings: Settings):
    app.dependency_overrides[get_settings] = lambda: stage3_settings
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
            "query": "article 19",
            "mode": "hybrid",
            "fallback": None,
            "fallback_reason": None,
            "weights": {"vector": 0.7, "graph": 0.3},
            "score_type": "hybrid",
            "warnings": [],
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


def test_stage3_new_query_persists_session_and_citations(client: TestClient) -> None:
    user_a = User(id=uuid4(), email=f"user_a_{uuid4()}@test.com", name="User A", role=UserRole.USER)
    app.dependency_overrides[get_current_user] = lambda: user_a
    try:
        res = client.post("/qa/ask", json={"query": "What are the freedoms in Article 19?"})
        assert res.status_code == 200, res.text
        data = res.json()
        session_id = data.get("session_id")
        assert session_id is not None
        assert data["answer"] is not None
        assert len(data["citations"]) >= 1

        # Check history API returns this session
        hist_res = client.get(f"/research/history/{session_id}")
        assert hist_res.status_code == 200, hist_res.text
        hist_data = hist_res.json()
        assert hist_data["id"] == session_id
        assert len(hist_data["queries"]) == 1
        assert hist_data["queries"][0]["question"] == "What are the freedoms in Article 19?"
        assert len(hist_data["queries"][0]["answers"]) == 1
        assert len(hist_data["queries"][0]["answers"][0]["citations"]) >= 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_stage3_follow_up_appends_to_existing_session(client: TestClient) -> None:
    user_a = User(id=uuid4(), email=f"user_a_{uuid4()}@test.com", name="User A", role=UserRole.USER)
    app.dependency_overrides[get_current_user] = lambda: user_a
    try:
        # First query
        res1 = client.post("/qa/ask", json={"query": "Initial question"})
        assert res1.status_code == 200
        session_id = res1.json()["session_id"]

        # Follow-up query reusing session_id
        res2 = client.post("/qa/ask", json={"query": "Follow-up question", "session_id": session_id})
        assert res2.status_code == 200
        assert res2.json()["session_id"] == session_id

        # Verify history has 2 queries in the same session
        hist_res = client.get(f"/research/history/{session_id}")
        assert hist_res.status_code == 200
        hist_data = hist_res.json()
        assert len(hist_data["queries"]) == 2
        assert hist_data["queries"][0]["question"] == "Initial question"
        assert hist_data["queries"][1]["question"] == "Follow-up question"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_stage3_nonexistent_session_id_returns_404(client: TestClient) -> None:
    user = User(id=uuid4(), email=f"user_{uuid4()}@test.com", name="User", role=UserRole.USER)
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        fake_id = str(uuid4())
        res = client.post("/qa/ask", json={"query": "A question", "session_id": fake_id})
        assert res.status_code == 404
        assert "not found" in res.text.lower()
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_stage3_user_isolation_cannot_append_or_read_other_session(client: TestClient) -> None:
    user_a = User(id=uuid4(), email=f"user_a_{uuid4()}@test.com", name="User A", role=UserRole.USER)
    user_b = User(id=uuid4(), email=f"user_b_{uuid4()}@test.com", name="User B", role=UserRole.USER)

    # 1. User A creates session
    app.dependency_overrides[get_current_user] = lambda: user_a
    try:
        res1 = client.post("/qa/ask", json={"query": "Private research for User A"})
        assert res1.status_code == 200
        session_id = res1.json()["session_id"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    # 2. User B tries to post to User A's session -> must be 403 Forbidden
    app.dependency_overrides[get_current_user] = lambda: user_b
    try:
        res2 = client.post("/qa/ask", json={"query": "Intruder question", "session_id": session_id})
        assert res2.status_code == 403
        assert "not authorized" in res2.text.lower()

        # 3. User B tries to read User A's session -> must be 404 (not found for User B)
        res3 = client.get(f"/research/history/{session_id}")
        assert res3.status_code == 404

        # 4. User B's history listing does NOT include User A's session
        list_res = client.get("/research/history")
        assert list_res.status_code == 200
        items = list_res.json()["items"]
        assert all(item["id"] != session_id for item in items)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_stage3_llm_failure_rolls_back_session(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    user = User(id=uuid4(), email=f"user_fail_{uuid4()}@test.com", name="User Fail", role=UserRole.USER)
    app.dependency_overrides[get_current_user] = lambda: user

    async def failing_ask_legal_question(*args, **kwargs):
        raise RuntimeError("Simulated LLM Provider Outage")

    monkeypatch.setattr("app.api.routes.qa.ask_legal_question", failing_ask_legal_question)

    try:
        # Before failure: 0 history items
        hist_before = client.get("/research/history")
        assert hist_before.status_code == 200
        initial_count = hist_before.json()["total"]

        # Call /qa/ask which will fail during generation; TestClient re-raises the 500 exception
        with pytest.raises(RuntimeError, match="Simulated LLM Provider Outage"):
            client.post("/qa/ask", json={"query": "Question that will fail LLM"})

        # After failure: database transaction rolled back; no orphaned session exists
        hist_after = client.get("/research/history")
        assert hist_after.status_code == 200
        assert hist_after.json()["total"] == initial_count
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_stage3_history_persists_across_new_client_session(client: TestClient) -> None:
    user = User(id=uuid4(), email=f"user_persist_{uuid4()}@test.com", name="User Persist", role=UserRole.USER)
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        # Create a research session
        res = client.post("/qa/ask", json={"query": "Persisted inquiry on fundamental rights"})
        assert res.status_code == 200
        session_id = res.json()["session_id"]
        assert session_id is not None

        # Simulate new browser session: clear all client cookies and local state
        client.cookies.clear()

        # Re-fetch the session with user credentials in place
        hist_res = client.get(f"/research/history/{session_id}")
        assert hist_res.status_code == 200
        data = hist_res.json()
        assert data["id"] == session_id
        assert data["title"].startswith("Persisted inquiry")
        assert len(data["queries"]) == 1
        assert len(data["queries"][0]["answers"]) == 1
        assert len(data["queries"][0]["answers"][0]["citations"]) >= 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)
