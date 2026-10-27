"""Integration & Route tests for InLegalBERT FastAPI Embedding Microservice."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app, embedder


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model"] == "law-ai/InLegalBERT"
    assert data["dimension"] == 768
    assert "model_loaded" in data


def test_embed_missing_api_key_when_configured(client, monkeypatch):
    monkeypatch.setenv("EMBEDDING_API_KEY", "secret-test-key")
    response = client.post("/embed", json={"texts": ["Article 21 protects fundamental rights."]})
    assert response.status_code == 401
    assert "Invalid or missing API key" in response.json()["detail"]


def test_embed_invalid_api_key_when_configured(client, monkeypatch):
    monkeypatch.setenv("EMBEDDING_API_KEY", "secret-test-key")
    headers = {"X-API-Key": "wrong-key"}
    response = client.post("/embed", json={"texts": ["Article 21 protects fundamental rights."]}, headers=headers)
    assert response.status_code == 401


def test_embed_valid_api_key_header(client, monkeypatch):
    monkeypatch.setenv("EMBEDDING_API_KEY", "secret-test-key")
    headers = {"X-API-Key": "secret-test-key"}

    fake_vecs = [[0.1] * 768, [0.2] * 768]
    with patch.object(embedder, "embed", return_value=fake_vecs):
        response = client.post(
            "/embed",
            json={"texts": ["Article 21 of Constitution", "Section 66A IT Act"]},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["dimension"] == 768
        assert len(data["embeddings"]) == 2
        assert len(data["embeddings"][0]) == 768


def test_embed_bearer_token_authentication(client, monkeypatch):
    monkeypatch.setenv("EMBEDDING_API_KEY", "secret-test-key")
    headers = {"Authorization": "Bearer secret-test-key"}

    fake_vecs = [[0.05] * 768]
    with patch.object(embedder, "embed", return_value=fake_vecs):
        response = client.post(
            "/embed",
            json={"texts": ["Basic Structure Doctrine"]},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["count"] == 1


def test_embed_validation_empty_list(client):
    response = client.post("/embed", json={"texts": []})
    assert response.status_code == 422


def test_embed_validation_blank_string(client):
    response = client.post("/embed", json={"texts": ["  "]})
    assert response.status_code == 422


def test_embed_validation_invalid_type(client):
    response = client.post("/embed", json={"texts": [12345]})
    assert response.status_code == 422


def test_embed_batch_ordering_preservation(client):
    """Verify response returns embeddings in identical batch order to input texts."""
    fake_vecs = [
        [1.0] + [0.0] * 767,
        [0.0, 1.0] + [0.0] * 766,
        [0.0, 0.0, 1.0] + [0.0] * 765,
    ]
    with patch.object(embedder, "embed", return_value=fake_vecs):
        response = client.post(
            "/embed",
            json={"texts": ["Query A", "Query B", "Query C"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert data["embeddings"][0][0] == 1.0
        assert data["embeddings"][1][1] == 1.0
        assert data["embeddings"][2][2] == 1.0
