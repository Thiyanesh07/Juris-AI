"""Integration tests for POST /retrieval/hybrid."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.graph.client import GraphError
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


def _make_user(role: UserRole = UserRole.USER) -> User:
    return User(id=uuid4(), email="user@test.com", name="Test", role=role)


def _override_user(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def retrieval_settings(tmp_path: Path) -> Settings:
    settings = get_settings()
    _configure_settings(settings, tmp_path)
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
def patch_settings(retrieval_settings: Settings):
    app.dependency_overrides[get_settings] = lambda: retrieval_settings
    yield
    app.dependency_overrides.pop(get_settings, None)


@pytest.fixture(autouse=True)
def patch_embedder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.retrieval.service.build_embedder", lambda _settings: FakeEmbedder())


def test_hybrid_requires_authentication(client: TestClient) -> None:
    _clear_overrides()
    try:
        response = client.post("/retrieval/hybrid", json={"query": "equality"})
        assert response.status_code == 401
    finally:
        _clear_overrides()


def test_hybrid_blank_query_rejected(client: TestClient) -> None:
    user = _make_user()
    _override_user(user)
    try:
        response = client.post("/retrieval/hybrid", json={"query": "   "})
        assert response.status_code == 422
    finally:
        _clear_overrides()


def test_hybrid_invalid_top_k(client: TestClient) -> None:
    user = _make_user()
    _override_user(user)
    try:
        response = client.post(
            "/retrieval/hybrid",
            json={"query": "equality", "top_k": 99},
        )
        assert response.status_code == 422
    finally:
        _clear_overrides()


def test_hybrid_valid_schema(client: TestClient) -> None:
    user = _make_user()
    _override_user(user)
    try:
        response = client.post(
            "/retrieval/hybrid",
            json={"query": "equality", "top_k": 2},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["mode"] == "hybrid"
        assert body["weights"]["vector"] == 0.7
        assert len(body["results"]) <= 2
        if body["results"]:
            item = body["results"][0]
            assert "hybrid_score" in item
            assert "dense_score" in item
            assert "graph_score" in item
            assert "evidence_sources" in item
    finally:
        _clear_overrides()


def test_dense_search_unchanged(client: TestClient) -> None:
    user = _make_user()
    _override_user(user)
    try:
        response = client.post(
            "/retrieval/search",
            json={"query": "equality", "top_k": 2},
        )
        assert response.status_code == 200
        body = response.json()
        assert "score" in body["results"][0]
        assert "hybrid_score" not in body["results"][0]
    finally:
        _clear_overrides()


def test_hybrid_postgres_failure_returns_503(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    user = _make_user()
    _override_user(user)

    async def failing_loader(*_args, **_kwargs):
        raise SQLAlchemyError("db down")

    monkeypatch.setattr("app.retrieval.hybrid.load_chunks_by_ids", failing_loader)
    try:
        response = client.post("/retrieval/hybrid", json={"query": "equality", "top_k": 2})
        assert response.status_code == 503
    finally:
        _clear_overrides()


def test_hybrid_missing_index_returns_503(client: TestClient, tmp_path: Path) -> None:
    settings = get_settings()
    _configure_settings(settings, tmp_path, index_name="absent")
    app.dependency_overrides[get_settings] = lambda: settings
    user = _make_user()
    _override_user(user)
    try:
        response = client.post("/retrieval/hybrid", json={"query": "equality"})
        assert response.status_code == 503
    finally:
        _clear_overrides()
        app.dependency_overrides.pop(get_settings, None)


def test_hybrid_neo4j_failure_dense_fallback(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _make_user()
    _override_user(user)

    async def failing_expand(self, seed_ids: list[str], max_paths: int) -> list[dict]:
        raise GraphError("down")

    monkeypatch.setattr(
        "app.graph.client.Neo4jClient.expand_supported_chunks",
        failing_expand,
    )
    try:
        response = client.post("/retrieval/hybrid", json={"query": "equality", "top_k": 2})
        assert response.status_code == 200
        body = response.json()
        assert body["fallback"] == "dense_only"
        assert body["fallback_reason"] == "neo4j_unavailable"
        assert all(item["graph_score"] == 0 for item in body["results"])
    finally:
        _clear_overrides()


def test_hybrid_default_top_k(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    user = _make_user()
    _override_user(user)
    captured: dict[str, int] = {}

    async def fake_hybrid(session, graph_client, query, top_k, settings, embedder=None):
        captured["top_k"] = top_k
        return {
            "query": query,
            "mode": "hybrid",
            "fallback": None,
            "fallback_reason": None,
            "weights": {
                "vector": settings.hybrid_vector_weight,
                "graph": settings.hybrid_graph_weight,
            },
            "score_type": (
                "hybrid = vector_weight * clamp(cosine, 0, 1) + graph_weight * graph_support"
            ),
            "warnings": [],
            "results": [],
        }

    monkeypatch.setattr("app.api.routes.retrieval.hybrid_retrieve", fake_hybrid)
    try:
        response = client.post("/retrieval/hybrid", json={"query": "equality"})
        assert response.status_code == 200
        assert captured["top_k"] == 5
    finally:
        _clear_overrides()


def test_hybrid_rejects_client_graph_overrides(client: TestClient) -> None:
    user = _make_user()
    _override_user(user)
    try:
        response = client.post(
            "/retrieval/hybrid",
            json={"query": "equality", "top_k": 2, "dense_weight": 0.9, "max_hops": 4},
        )
        assert response.status_code == 422
    finally:
        _clear_overrides()
