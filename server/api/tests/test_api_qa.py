"""Integration tests for POST /qa/ask."""

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
from app.qa.provider import LLMProviderTimeout, LLMProviderUnavailable
from app.retrieval.embeddings import EmbeddingError
from app.retrieval.index import save_index
from tests.test_retrieval import (
    TEST_MODEL,
    TEST_POOLING,
    FakeEmbedder,
    _configure_settings,
    _records,
)


def _make_user(role: UserRole = UserRole.USER) -> User:
    return User(id=uuid4(), email="user@test.com", name="Test", role=role)


def _override_user(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.pop(get_current_user, None)


def _valid_llm_json() -> str:
    return json.dumps(
        {
            "answer": "Equality is guaranteed [1].",
            "insufficient_evidence": False,
            "citations": [{"marker": 1, "evidence_rank": 1}],
        }
    )


class FakeLLMProvider:
    def __init__(
        self,
        responses: list[str] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.responses = responses or [_valid_llm_json()]
        self.error = error
        self.calls = 0

    async def generate(self, **_kwargs: object) -> str:
        if self.error is not None:
            raise self.error
        text = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return text


@pytest.fixture
def qa_settings(tmp_path: Path) -> Settings:
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
def patch_settings(qa_settings: Settings):
    app.dependency_overrides[get_settings] = lambda: qa_settings
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
            "query": "equality",
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


def test_qa_requires_authentication(client: TestClient) -> None:
    _clear_overrides()
    try:
        response = client.post("/qa/ask", json={"query": "equality"})
        assert response.status_code == 401
    finally:
        _clear_overrides()


def test_qa_invalid_request(client: TestClient) -> None:
    user = _make_user()
    _override_user(user)
    try:
        response = client.post("/qa/ask", json={"query": "   "})
        assert response.status_code == 422
    finally:
        _clear_overrides()


def test_qa_rejects_extra_fields(client: TestClient) -> None:
    user = _make_user()
    _override_user(user)
    try:
        response = client.post(
            "/qa/ask",
            json={"query": "equality", "dense_weight": 0.9},
        )
        assert response.status_code == 422
    finally:
        _clear_overrides()


def test_qa_successful_answer(client: TestClient) -> None:
    user = _make_user()
    _override_user(user)
    try:
        response = client.post("/qa/ask", json={"query": "equality", "top_k": 2})
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "answered"
        assert body["llm_called"] is True
        assert body["citations"]
        assert body["evidence"]
        assert body["disclaimer"] == "Informational research aid. Not legal advice."
    finally:
        _clear_overrides()


def test_qa_empty_retrieval(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    patch_llm_provider: FakeLLMProvider,
) -> None:
    user = _make_user()
    _override_user(user)

    async def empty_hybrid(*_args, **_kwargs):
        return {
            "query": "missing",
            "mode": "hybrid",
            "fallback": None,
            "fallback_reason": None,
            "weights": {"vector": 0.7, "graph": 0.3},
            "score_type": "hybrid",
            "warnings": [],
            "results": [],
        }

    monkeypatch.setattr("app.qa.service.hybrid_retrieve", empty_hybrid)
    try:
        response = client.post("/qa/ask", json={"query": "missing"})
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "insufficient_evidence"
        assert body["llm_called"] is False
        assert body["answer"] is None
        assert body["citations"] == []
        assert body["evidence"] == []
        assert patch_llm_provider.calls == 0
    finally:
        _clear_overrides()


def test_qa_retrieval_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    user = _make_user()
    _override_user(user)

    async def failing_hybrid(*_args, **_kwargs):
        raise EmbeddingError("embed down")

    monkeypatch.setattr("app.qa.service.hybrid_retrieve", failing_hybrid)
    try:
        response = client.post("/qa/ask", json={"query": "equality"})
        assert response.status_code == 503
    finally:
        _clear_overrides()


def test_qa_provider_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _make_user()
    _override_user(user)

    def failing_provider(_settings: Settings) -> FakeLLMProvider:
        raise LLMProviderUnavailable("no provider")

    monkeypatch.setattr("app.qa.service.build_llm_provider", failing_provider)
    try:
        response = client.post("/qa/ask", json={"query": "equality"})
        assert response.status_code == 503
    finally:
        _clear_overrides()


def test_qa_timeout(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    patch_llm_provider: FakeLLMProvider,
) -> None:
    user = _make_user()
    _override_user(user)

    async def timeout_generate(**_kwargs: object) -> str:
        raise LLMProviderTimeout("timeout")

    patch_llm_provider.generate = timeout_generate  # type: ignore[method-assign]
    try:
        response = client.post("/qa/ask", json={"query": "equality"})
        assert response.status_code == 504
    finally:
        _clear_overrides()


def test_qa_malformed_output(
    client: TestClient,
    patch_llm_provider: FakeLLMProvider,
) -> None:
    user = _make_user()
    _override_user(user)
    bad = json.dumps({"answer": "no markers", "insufficient_evidence": False, "citations": []})
    patch_llm_provider.responses = [bad, bad]
    try:
        response = client.post("/qa/ask", json={"query": "equality"})
        assert response.status_code == 502
        assert response.json()["detail"] == "Invalid model output"
        assert "missing marker" not in response.text
        assert "no markers" not in response.text
    finally:
        _clear_overrides()


def test_qa_missing_api_key(
    client: TestClient,
    qa_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.qa.provider import build_llm_provider

    monkeypatch.setattr("app.qa.service.build_llm_provider", build_llm_provider)
    user = _make_user()
    _override_user(user)
    qa_settings.llm_api_key = ""
    try:
        response = client.post("/qa/ask", json={"query": "equality"})
        assert response.status_code == 503
    finally:
        _clear_overrides()


def test_qa_invalid_top_k(client: TestClient) -> None:
    user = _make_user()
    _override_user(user)
    try:
        response = client.post(
            "/qa/ask",
            json={"query": "equality", "top_k": 99},
        )
        assert response.status_code == 422
    finally:
        _clear_overrides()


def test_qa_empty_retrieval_without_api_key(
    client: TestClient,
    qa_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.qa.provider import build_llm_provider

    monkeypatch.setattr("app.qa.service.build_llm_provider", build_llm_provider)
    qa_settings.llm_api_key = ""

    async def empty_hybrid(*_args, **_kwargs):
        return {
            "query": "missing",
            "mode": "hybrid",
            "fallback": None,
            "fallback_reason": None,
            "weights": {"vector": 0.7, "graph": 0.3},
            "score_type": "hybrid",
            "warnings": ["none matched"],
            "results": [],
        }

    monkeypatch.setattr("app.qa.service.hybrid_retrieve", empty_hybrid)
    user = _make_user()
    _override_user(user)
    try:
        response = client.post("/qa/ask", json={"query": "missing"})
        assert response.status_code == 200
        body = response.json()
        assert body["llm_called"] is False
        assert body["status"] == "insufficient_evidence"
        assert body["retrieval"]["warnings"] == ["none matched"]
    finally:
        _clear_overrides()


def test_qa_dense_only_fallback_calls_llm(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _make_user()
    _override_user(user)
    record = _records()[0]

    async def fallback_hybrid(*_args, **_kwargs):
        return {
            "query": "equality",
            "mode": "hybrid",
            "fallback": "dense_only",
            "fallback_reason": "neo4j_unavailable",
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

    monkeypatch.setattr("app.qa.service.hybrid_retrieve", fallback_hybrid)
    try:
        response = client.post("/qa/ask", json={"query": "equality"})
        assert response.status_code == 200
        body = response.json()
        assert body["llm_called"] is True
        assert body["retrieval"]["fallback"] == "dense_only"
        assert body["retrieval"]["fallback_reason"] == "neo4j_unavailable"
    finally:
        _clear_overrides()
