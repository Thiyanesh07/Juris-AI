"""Phase 4 Regression & Verification Tests: Admin Operations and Consistency.

Verifies:
1. Ingestion/Document search works across all pages (database-level filtering and pagination).
2. Document type filtering and status filtering.
3. Ingestion jobs search by title/job ID and global status counts aggregation.
4. Health endpoints bounded timeouts, sanitized error details, and no credential leakage.
5. LLM provider distinguishes configured state from verified live state.
6. Public stats and health routes availability under both root and /api/v1 compatibility prefixes.
7. Authorization boundaries between unauthenticated/user and admin roles.
"""

from __future__ import annotations

import io
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.health import _sanitize_error, _check_llm
from app.auth.dependencies import get_current_user, require_admin
from app.core.config import Settings
from app.main import app
from app.models import Document, User
from app.models.enums import (
    DocumentStatus,
    DocumentType,
    ProcessingJobStage,
    ProcessingJobStatus,
    UserRole,
)
from app.models.processing_job import ProcessingJob


def _make_admin_user() -> User:
    return User(id=uuid4(), email="admin@jurisai.test", name="Admin User", role=UserRole.ADMIN)


def _override_admin(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_admin] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_admin, None)


@pytest.mark.asyncio
async def test_sanitize_error_masks_credentials() -> None:
    """Ensure credentials, passwords, and tokens in exception strings are sanitized."""
    sensitive_exc = ValueError(
        "Connection failed to postgresql://postgres_user:my_secret_password_123@db.prod.internal:5432/juris_prod?sslmode=require"
    )
    sanitized = _sanitize_error(sensitive_exc)
    assert "my_secret_password_123" not in sanitized
    assert "postgresql://postgres_user:***@db.prod.internal:5432" in sanitized

    token_exc = RuntimeError("Aura auth failed with token=aura_secret_token_abc and key=xyz")
    sanitized_token = _sanitize_error(token_exc)
    assert "aura_secret_token_abc" not in sanitized_token
    assert "token=***" in sanitized_token


def test_llm_status_marks_unverified_live() -> None:
    """Ensure LLM provider check marks configured state as not verified live."""
    settings = Settings(
        llm_provider="google_genai",
        llm_model="gemini-2.5-pro",
        llm_api_key="mock-key-for-test",
    )
    health = _check_llm(settings)
    assert health.status == "ok"
    assert "Configured" in (health.detail or "")
    assert health.metrics is not None
    assert health.metrics.get("verified_live") is False


def test_health_and_stats_routes_mounted_at_v1(client: TestClient) -> None:
    """Ensure /health, /stats, and /api/v1 equivalents are accessible."""
    resp_root_health = client.get("/health")
    assert resp_root_health.status_code == 200
    assert "components" in resp_root_health.json()

    resp_v1_health = client.get("/api/v1/health")
    assert resp_v1_health.status_code == 200
    assert "components" in resp_v1_health.json()

    resp_root_stats = client.get("/stats")
    assert resp_root_stats.status_code == 200
    assert "total_documents" in resp_root_stats.json()

    resp_v1_stats = client.get("/api/v1/stats")
    assert resp_v1_stats.status_code == 200
    assert "total_documents" in resp_v1_stats.json()

    resp_v1_public_stats = client.get("/api/v1/public/stats")
    assert resp_v1_public_stats.status_code == 200
    assert "total_documents" in resp_v1_public_stats.json()


@pytest.mark.asyncio
async def test_document_cross_page_search_and_pagination(
    client: TestClient, session: AsyncSession
) -> None:
    """Verify document search operates across all pages, preserving counts and filters."""
    admin = _make_admin_user()
    _override_admin(admin)

    try:
        # Seed test documents
        docs = [
            Document(
                title="Code of Criminal Procedure 1973",
                type=DocumentType.ACT,
                source="test_upload",
                status=DocumentStatus.READY,
            ),
            Document(
                title="Code of Civil Procedure 1908",
                type=DocumentType.ACT,
                source="test_upload",
                status=DocumentStatus.READY,
            ),
            Document(
                title="Indian Evidence Act 1872",
                type=DocumentType.ACT,
                source="test_upload",
                status=DocumentStatus.READY,
            ),
            Document(
                title="Kesavananda Bharati Judgment",
                type=DocumentType.JUDGMENT,
                source="test_upload",
                status=DocumentStatus.READY,
            ),
        ]
        session.add_all(docs)
        await session.commit()

        # 1. Search across pages for "Procedure" with page_size=1
        resp_p1 = client.get(
            "/documents",
            params={"search": "Procedure", "page": 1, "page_size": 1},
        )
        assert resp_p1.status_code == 200
        data_p1 = resp_p1.json()
        assert data_p1["total"] == 2
        assert len(data_p1["items"]) == 1
        assert "Procedure" in data_p1["items"][0]["title"]

        # 2. Page 2 returns the second matching item
        resp_p2 = client.get(
            "/documents",
            params={"search": "Procedure", "page": 2, "page_size": 1},
        )
        assert resp_p2.status_code == 200
        data_p2 = resp_p2.json()
        assert data_p2["total"] == 2
        assert len(data_p2["items"]) == 1
        assert "Procedure" in data_p2["items"][0]["title"]
        assert data_p2["items"][0]["id"] != data_p1["items"][0]["id"]

        # 3. Type filter + search
        resp_type = client.get(
            "/documents",
            params={"type": "JUDGMENT", "search": "Kesavananda"},
        )
        assert resp_type.status_code == 200
        data_type = resp_type.json()
        assert data_type["total"] == 1
        assert data_type["items"][0]["type"] in (DocumentType.JUDGMENT, "judgment")

        # 4. Search with no matches returns empty list cleanly
        resp_empty = client.get(
            "/documents",
            params={"search": "NonExistentActXYZ"},
        )
        assert resp_empty.status_code == 200
        data_empty = resp_empty.json()
        assert data_empty["total"] == 0
        assert data_empty["items"] == []

    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_processing_jobs_search_and_global_counts(
    client: TestClient, session: AsyncSession
) -> None:
    """Verify processing jobs search and true system-wide status counts."""
    admin = _make_admin_user()
    _override_admin(admin)

    try:
        # Seed documents and processing jobs
        doc1 = Document(
            title="Arbitration and Conciliation Act",
            type=DocumentType.ACT,
            source="test_upload",
            status=DocumentStatus.READY,
        )
        doc2 = Document(
            title="Insolvency and Bankruptcy Code",
            type=DocumentType.ACT,
            source="test_upload",
            status=DocumentStatus.PROCESSING,
        )
        session.add_all([doc1, doc2])
        await session.flush()

        job1 = ProcessingJob(
            document_id=doc1.id,
            status=ProcessingJobStatus.COMPLETED,
            stage=ProcessingJobStage.GRAPH_POPULATION,
        )
        job2 = ProcessingJob(
            document_id=doc2.id,
            status=ProcessingJobStatus.RUNNING,
            stage=ProcessingJobStage.EMBEDDING,
        )
        session.add_all([job1, job2])
        await session.commit()

        # 1. Fetch jobs and verify global counts dictionary
        resp = client.get("/documents/jobs", params={"page": 1, "page_size": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert "counts" in data
        assert data["counts"].get("completed") == 1
        assert data["counts"].get("running") == 1

        # 2. Search jobs by document title
        resp_search = client.get("/documents/jobs", params={"search": "Arbitration"})
        assert resp_search.status_code == 200
        data_search = resp_search.json()
        assert data_search["total"] == 1
        assert data_search["items"][0]["document_title"] == "Arbitration and Conciliation Act"
        # Counts still represent global status counts
        assert data_search["counts"].get("completed") == 1
        assert data_search["counts"].get("running") == 1

    finally:
        _clear_overrides()


def test_admin_authorization_boundary(client: TestClient) -> None:
    """Ensure unauthenticated callers cannot access admin documents endpoints."""
    _clear_overrides()
    resp = client.get("/documents")
    assert resp.status_code in (401, 403)

    resp_jobs = client.get("/documents/jobs")
    assert resp_jobs.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_operation_archive_and_restore_flows(
    client: TestClient, session: AsyncSession
) -> None:
    """Check 1: Verify archive and restore operation flows for success and error states."""
    admin = _make_admin_user()
    _override_admin(admin)

    try:
        # Create a document
        doc = Document(
            title="Telecommunications Act 2023",
            type=DocumentType.ACT,
            source="test_upload",
            status=DocumentStatus.READY,
        )
        session.add(doc)
        await session.commit()

        # 1. Archive document -> confirmed success
        res_archive = client.post(f"/documents/{doc.id}/archive")
        assert res_archive.status_code == 200
        data_arch = res_archive.json()
        assert data_arch["status"] == DocumentStatus.DISABLED.value

        # 2. Restore document -> confirmed success
        res_restore = client.post(f"/documents/{doc.id}/restore")
        assert res_restore.status_code == 200
        data_rest = res_restore.json()
        assert data_rest["status"] in (DocumentStatus.READY.value, DocumentStatus.FAILED.value)

        # 3. Archive non-existent document -> explicit 404, never shows success
        bad_id = uuid4()
        res_bad_arch = client.post(f"/documents/{bad_id}/archive")
        assert res_bad_arch.status_code == 404
        assert "not found" in res_bad_arch.json()["detail"].lower()

        # 4. Restore non-existent document -> explicit 404
        res_bad_rest = client.post(f"/documents/{bad_id}/restore")
        assert res_bad_rest.status_code == 404
        assert "not found" in res_bad_rest.json()["detail"].lower()

        # 5. Reprocess non-existent document -> explicit 404, never shows success
        res_bad_reproc = client.post(f"/documents/{bad_id}/reprocess")
        assert res_bad_reproc.status_code == 404
        assert "not found" in res_bad_reproc.json()["detail"].lower()

    finally:
        _clear_overrides()


def test_landing_metrics_api_contract(client: TestClient) -> None:
    """Check 2: Verify /stats schema precisely fulfills the fields consumed by metrics-section.tsx."""
    resp = client.get("/stats")
    assert resp.status_code == 200
    data = resp.json()

    # Exact fields required by AnimatedCounter and metrics-section.tsx
    assert "graph_nodes" in data and isinstance(data["graph_nodes"], int)
    assert "graph_relationships" in data and isinstance(data["graph_relationships"], int)
    assert "vector_count" in data and isinstance(data["vector_count"], int)
    assert "total_documents" in data and isinstance(data["total_documents"], int)

    # Alternate endpoint route
    resp_pub = client.get("/public/stats")
    assert resp_pub.status_code == 200
    data_pub = resp_pub.json()
    assert data_pub["total_documents"] == data["total_documents"]


@pytest.mark.asyncio
async def test_global_ingestion_metrics_multipage_and_filters(
    client: TestClient, session: AsyncSession
) -> None:
    """Check 3: Verify processing job counts are computed system-wide across all pages and filters."""
    admin = _make_admin_user()
    _override_admin(admin)

    try:
        # Create 3 documents
        d1 = Document(title="Act Alpha", type=DocumentType.ACT, source="test", status=DocumentStatus.READY)
        d2 = Document(title="Act Beta", type=DocumentType.ACT, source="test", status=DocumentStatus.READY)
        d3 = Document(title="Act Gamma", type=DocumentType.ACT, source="test", status=DocumentStatus.READY)
        session.add_all([d1, d2, d3])
        await session.flush()

        # Seed 12 jobs: 4 pending, 4 running, 4 completed
        jobs = []
        for d in [d1, d2, d3]:
            for _ in range(4):
                jobs.append(ProcessingJob(document_id=d.id, status=ProcessingJobStatus.PENDING, stage=ProcessingJobStage.INGESTION))
                jobs.append(ProcessingJob(document_id=d.id, status=ProcessingJobStatus.RUNNING, stage=ProcessingJobStage.EMBEDDING))
                jobs.append(ProcessingJob(document_id=d.id, status=ProcessingJobStatus.COMPLETED, stage=ProcessingJobStage.GRAPH_POPULATION))
            break  # 12 jobs for d1
        session.add_all(jobs)
        await session.commit()

        # Verify page 1: page_size=4 (first page of 3)
        res_p1 = client.get("/documents/jobs", params={"page": 1, "page_size": 4})
        assert res_p1.status_code == 200
        p1_data = res_p1.json()
        assert p1_data["total"] == 12
        assert len(p1_data["items"]) == 4
        assert p1_data["counts"]["pending"] == 4
        assert p1_data["counts"]["running"] == 4
        assert p1_data["counts"]["completed"] == 4

        # Verify page 2: page_size=4 (second page of 3)
        res_p2 = client.get("/documents/jobs", params={"page": 2, "page_size": 4})
        assert res_p2.status_code == 200
        p2_data = res_p2.json()
        assert p2_data["total"] == 12
        assert len(p2_data["items"]) == 4
        # Counts MUST remain constant across pages
        assert p2_data["counts"]["pending"] == 4
        assert p2_data["counts"]["running"] == 4
        assert p2_data["counts"]["completed"] == 4

        # Verify filter by status=RUNNING: total is 4, but global counts reflect all 12
        res_flt = client.get("/documents/jobs", params={"status": "RUNNING", "page": 1, "page_size": 10})
        assert res_flt.status_code == 200
        flt_data = res_flt.json()
        assert flt_data["total"] == 4
        assert len(flt_data["items"]) == 4
        assert flt_data["counts"]["pending"] == 4
        assert flt_data["counts"]["running"] == 4
        assert flt_data["counts"]["completed"] == 4

        # Verify search by title
        res_search = client.get("/documents/jobs", params={"search": "Act Alpha", "page": 1, "page_size": 10})
        assert res_search.status_code == 200
        s_data = res_search.json()
        assert s_data["total"] == 12
        assert s_data["counts"]["pending"] == 4

    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_health_timeout_bounds_and_degraded_state(client: TestClient) -> None:
    """Check 4: Verify health check bounded timeouts produce honest degraded results and mask secrets."""
    import asyncio
    from app.api.routes.health import _check_database

    class MockHangingSession:
        async def execute(self, *args: object, **kwargs: object) -> None:
            await asyncio.sleep(6.0)

        async def scalar(self, *args: object, **kwargs: object) -> None:
            await asyncio.sleep(6.0)

    # 1. Verify timeout triggers within 5s
    res = await _check_database(MockHangingSession())
    assert res.status == "unreachable"
    assert "timed out" in (res.error or "")

    # 2. Verify overall health endpoint reflects degraded state
    from app.db.session import get_session

    async def override_failing_session():
        yield MockHangingSession()

    app.dependency_overrides[get_session] = override_failing_session
    try:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["components"]["database"]["status"] == "unreachable"
    finally:
        app.dependency_overrides.pop(get_session, None)
