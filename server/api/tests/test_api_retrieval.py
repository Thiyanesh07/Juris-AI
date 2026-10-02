"""Integration tests for /retrieval API endpoints."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user, require_admin
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

# Reuse document API auth override helpers pattern.


def _make_user(role: UserRole = UserRole.USER) -> User:
    return User(id=uuid4(), email="user@test.com", name="Test", role=role)


def _override_user(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


def _override_admin(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_admin] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_admin, None)


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


def test_search_requires_authentication(client: TestClient) -> None:
    _clear_overrides()
    try:
        response = client.post("/retrieval/search", json={"query": "equality"})
        assert response.status_code == 401
    finally:
        _clear_overrides()


def test_rebuild_requires_admin(client: TestClient) -> None:
    _clear_overrides()
    user = _make_user(UserRole.USER)
    _override_user(user)
    try:
        response = client.post("/retrieval/rebuild")
        assert response.status_code == 403
    finally:
        _clear_overrides()


def test_search_returns_evidence_with_chunk_index(client: TestClient) -> None:
    user = _make_user()
    _override_user(user)
    try:
        response = client.post(
            "/retrieval/search",
            json={"query": "equality", "top_k": 2},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["query"] == "equality"
        assert len(body["results"]) == 2
        assert body["results"][0]["chunk_index"] == 0
        assert body["results"][0]["citation_ref"] == "Article 14"
    finally:
        _clear_overrides()


def test_search_missing_index_returns_503(client: TestClient, tmp_path: Path) -> None:
    settings = get_settings()
    _configure_settings(settings, tmp_path, index_name="absent")
    app.dependency_overrides[get_settings] = lambda: settings
    user = _make_user()
    _override_user(user)
    try:
        response = client.post("/retrieval/search", json={"query": "equality"})
        assert response.status_code == 503
        assert "rebuild" in response.json()["detail"].lower()
    finally:
        _clear_overrides()
        app.dependency_overrides.pop(get_settings, None)
