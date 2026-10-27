"""Isolated Ingestion Test Harness for Juris AI (Phase 6).

Provides an end-to-end HTTP-level testing framework that exercises the real
FastAPI routes (/documents/upload, /documents/{id}, /documents/{id}/jobs,
/documents/{id}/chunks, /documents/{id}/pdf, /documents/{id}/reprocess,
/documents/{id}/retry-graph, and /retrieval/search).

Strict isolation invariants:
- Storage is pinned to a dedicated ephemeral pytest tmp_path.
- Vector index name is pinned to 'phase6_test_chunks' (never 'legal_chunks').
- In-memory graph double (FakeNeo4jClient) is used for all graph interactions.
- Local deterministic 768-dim embedder is used to prevent any external API calls.
- Protected repository FAISS and corpus artifacts are verified before and after each run.
"""

from __future__ import annotations

import asyncio
import io
import time
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.core.config import Settings, get_settings
from app.graph.client import GraphError
from app.main import app
from app.models import Chunk, Document, ProcessingJob, User
from app.models.enums import DocumentStatus, DocumentType, UserRole
from tests.fake_neo4j import FakeNeo4jClient
from tests.isolation_preflight import (
    IsolationViolationError,
    ProtectedArtifactGuard,
    verify_storage_safety,
)


class IsolatedDeterministicEmbedder:
    """Deterministic InLegalBERT embedder producing unit-normalized 768-dim vectors.

    Produces consistent vectors based on text hash/length so that semantic search
    and FAISS indexing execute realistically without relying on external servers.
    """

    def __init__(self, dimension: int = 768) -> None:
        self.dimension = dimension
        self.pooling_method = "attention_mask_mean_pooling"
        self.normalization = "l2"

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        vectors = []
        for text in texts:
            # Deterministic pseudo-vector derived from characters in text
            seed_val = sum(ord(c) for c in text[:100]) % 997 + 1
            raw = np.zeros(self.dimension, dtype=np.float32)
            # Create a sparse yet distinct pattern
            for i in range(min(len(text), self.dimension)):
                raw[i] = float(ord(text[i]) % 17 + 1)
            raw[0] += float(seed_val)
            norm = np.linalg.norm(raw)
            vectors.append(raw / (norm if norm > 0 else 1.0))
        return np.vstack(vectors)


class TrackableFakeNeo4jClient(FakeNeo4jClient):
    """Fake Neo4j client with call tracking and configurable failure simulation."""

    def __init__(self, should_fail_on_replace: bool = False, failure_error: Exception | None = None) -> None:
        super().__init__()
        self.should_fail_on_replace = should_fail_on_replace
        self.failure_error = failure_error or GraphError("Simulated Neo4j cluster failure")
        self.replace_history: list[dict[str, Any]] = []

    async def replace_document_graph(self, payload: dict[str, Any]) -> None:
        if self.should_fail_on_replace:
            raise self.failure_error
        self.replace_history.append(payload)
        await super().replace_document_graph(payload)


class IsolatedIngestionHarness:
    """Manages an isolated end-to-end ingestion environment for test execution."""

    def __init__(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        admin_user: User | None = None,
        embedder: Any | None = None,
        graph_client: TrackableFakeNeo4jClient | None = None,
        test_index_name: str = "phase6_test_chunks",
    ) -> None:
        self.tmp_path = tmp_path
        self.monkeypatch = monkeypatch
        self.test_index_name = test_index_name
        self.artifact_guard = ProtectedArtifactGuard()

        # Enforce storage safety gate
        verify_storage_safety(tmp_path, vector_index_name=test_index_name)

        # Isolated user fixtures
        self.admin_user = admin_user or User(
            id=uuid4(),
            email="admin@isolated-test.juris.ai",
            name="Isolated Admin",
            role=UserRole.ADMIN,
        )
        self.regular_user = User(
            id=uuid4(),
            email="user@isolated-test.juris.ai",
            name="Isolated User",
            role=UserRole.USER,
        )

        # Isolated service doubles
        self.embedder = embedder or IsolatedDeterministicEmbedder(dimension=768)
        self.graph_client = graph_client or TrackableFakeNeo4jClient()

        # Construct and validate isolated settings instance
        base_settings = get_settings()
        self.settings = base_settings.model_copy(
            update={
                "data_dir": str(tmp_path),
                "vector_index_name": test_index_name,
                "app_env": "test",
                "embedding_model_name": "law-ai/InLegalBERT",
                "rate_limit_enabled": False,
            }
        )

        # Activate sandbox overrides
        self._activate_overrides()

    def _activate_overrides(self) -> None:
        # Dependency overrides for FastAPI
        app.dependency_overrides[get_settings] = lambda: self.settings
        app.dependency_overrides[get_current_user] = lambda: self.admin_user
        app.dependency_overrides[require_admin] = lambda: self.admin_user

        # Data directory overrides across all relevant namespaces
        self.monkeypatch.setattr("app.core.config.get_data_dir", lambda: self.tmp_path)
        self.monkeypatch.setattr("app.ingestion.pipeline.get_data_dir", lambda: self.tmp_path)
        self.monkeypatch.setattr("app.api.routes.documents.get_data_dir", lambda: self.tmp_path)
        self.monkeypatch.setattr("app.retrieval.service.get_data_dir", lambda: self.tmp_path)

        # In-memory graph client override
        self.monkeypatch.setattr("app.ingestion.pipeline.Neo4jClient", lambda *args, **kwargs: self.graph_client)
        self.monkeypatch.setattr("app.graph.population.Neo4jClient", lambda *args, **kwargs: self.graph_client)
        self.monkeypatch.setattr("app.graph.client.Neo4jClient", lambda *args, **kwargs: self.graph_client)
        self.monkeypatch.setattr("app.retrieval.hybrid.Neo4jClient", lambda *args, **kwargs: self.graph_client)

        # Deterministic embedder override
        self.monkeypatch.setattr("app.retrieval.service.build_embedder", lambda *args, **kwargs: self.embedder)
        self.monkeypatch.setattr("app.ingestion.pipeline.build_embedder", lambda *args, **kwargs: self.embedder)

    def deactivate(self) -> None:
        """Deactivate overrides and assert zero mutation of protected assets."""
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_admin, None)
        self.artifact_guard.verify()

    def upload_document(
        self,
        client: TestClient,
        pdf_bytes: bytes,
        title: str = "Test Legal Act",
        filename: str = "test.pdf",
        doc_type: str = "ACT",
        source: str = "isolated-test",
        source_url: str | None = None,
        as_admin: bool = True,
    ) -> Any:
        """Execute POST /documents/upload and process background task synchronously."""
        if not as_admin:
            app.dependency_overrides[require_admin] = lambda: self.regular_user

        try:
            params: dict[str, Any] = {
                "title": title,
                "type": doc_type,
                "source": source,
            }
            if source_url:
                params["source_url"] = source_url

            return client.post(
                "/documents/upload",
                params=params,
                files={"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
            )
        finally:
            if not as_admin:
                app.dependency_overrides[require_admin] = lambda: self.admin_user

    async def get_document_from_db(self, session: AsyncSession, document_id: UUID) -> Document | None:
        return await session.get(Document, document_id)

    async def get_jobs_from_db(self, session: AsyncSession, document_id: UUID) -> list[ProcessingJob]:
        res = await session.execute(
            select(ProcessingJob)
            .where(ProcessingJob.document_id == document_id)
            .order_by(ProcessingJob.created_at.asc())
        )
        return list(res.scalars().all())

    async def get_chunks_from_db(self, session: AsyncSession, document_id: UUID) -> list[Chunk]:
        res = await session.execute(
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index.asc())
        )
        return list(res.scalars().all())

    async def await_document_status(
        self,
        session: AsyncSession,
        document_id: UUID,
        expected_status: DocumentStatus | list[DocumentStatus],
        timeout_seconds: float = 10.0,
    ) -> Document:
        """Poll document status until it reaches the expected terminal status or times out."""
        targets = [expected_status] if isinstance(expected_status, DocumentStatus) else expected_status
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout_seconds:
            doc = await self.get_document_from_db(session, document_id)
            if doc is not None and doc.status in targets:
                return doc
            await asyncio.sleep(0.05)

        doc = await self.get_document_from_db(session, document_id)
        current_status = doc.status if doc else None
        raise TimeoutError(
            f"Document {document_id} did not reach {targets} within {timeout_seconds}s (current status: {current_status})"
        )


@pytest.fixture
def ingestion_harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Fixture yielding a clean, isolated ingestion test harness."""
    harness = IsolatedIngestionHarness(tmp_path=tmp_path, monkeypatch=monkeypatch)
    try:
        yield harness
    finally:
        harness.deactivate()
