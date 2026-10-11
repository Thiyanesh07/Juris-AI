"""Integration tests for ingestion jobs foundation (Phase 3 Step 1).

Tests:
- Authentication & RBAC for GET /documents/jobs and POST /documents/{id}/archive.
- Pagination, stage filtering, status filtering, and document_id filtering on GET /documents/jobs.
- Joined document metadata (title, type, status) and persisted errors.
- Document archiving (disable) and restoration (restore to READY).
- Re-process concurrency conflict (409 Conflict when already PROCESSING).
- Startup recovery function marking orphaned RUNNING jobs and documents as FAILED.
"""

from __future__ import annotations

import io
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.ingestion.recovery import INTERRUPTED_JOB_ERROR, recover_interrupted_jobs
from app.main import app
from app.models import Document, ProcessingJob, User
from app.models.enums import (
    DocumentStatus,
    DocumentType,
    ProcessingJobStage,
    ProcessingJobStatus,
    UserRole,
)


def _make_user(email: str = "user@test.com", role: UserRole = UserRole.USER) -> User:
    return User(id=uuid4(), email=email, name="Test User", role=role)


def _override_user(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


def _override_admin(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_admin] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_admin, None)


# ── GET /documents/jobs Auth & RBAC ───────────────────────────────────────────


def test_list_jobs_requires_auth(client: TestClient) -> None:
    _clear_overrides()
    resp = client.get("/documents/jobs")
    assert resp.status_code == 401


def test_list_jobs_requires_admin(client: TestClient) -> None:
    _clear_overrides()
    user = _make_user(role=UserRole.USER)
    _override_user(user)
    try:
        resp = client.get("/documents/jobs")
        assert resp.status_code == 403
    finally:
        _clear_overrides()


# ── GET /documents/jobs Pagination, Filtering & Metadata ──────────────────────


async def test_list_jobs_pagination_and_metadata(
    client: TestClient, session: AsyncSession
) -> None:
    admin = _make_user(role=UserRole.ADMIN)
    _override_admin(admin)

    try:
        # Create document
        doc = Document(
            title="Evidence Act 1872",
            type=DocumentType.ACT,
            source="India Code",
            status=DocumentStatus.READY,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        # Create processing jobs
        job1 = ProcessingJob(
            document_id=doc.id,
            stage=ProcessingJobStage.INGESTION,
            status=ProcessingJobStatus.COMPLETED,
        )
        job2 = ProcessingJob(
            document_id=doc.id,
            stage=ProcessingJobStage.CHUNKING,
            status=ProcessingJobStatus.FAILED,
            error="Failed to parse statutory hierarchy on page 14",
        )
        session.add_all([job1, job2])
        await session.commit()

        # Query all jobs
        resp = client.get("/documents/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        assert len(data["items"]) >= 2

        # Check job2 has joined metadata and error
        failed_job = next(j for j in data["items"] if j["id"] == str(job2.id))
        assert failed_job["document_id"] == str(doc.id)
        assert failed_job["document_title"] == "Evidence Act 1872"
        assert failed_job["document_type"] == "act"
        assert failed_job["document_status"] == "ready"
        assert failed_job["stage"] == "chunking"
        assert failed_job["status"] == "failed"
        assert failed_job["error"] == "Failed to parse statutory hierarchy on page 14"
        assert "created_at" in failed_job
        assert "updated_at" in failed_job

        # Test pagination
        resp_paged = client.get("/documents/jobs?page=1&page_size=1")
        assert resp_paged.status_code == 200
        paged_data = resp_paged.json()
        assert paged_data["page"] == 1
        assert paged_data["page_size"] == 1
        assert len(paged_data["items"]) == 1

        # Test status filter
        resp_status = client.get("/documents/jobs?status=FAILED")
        assert resp_status.status_code == 200
        status_items = resp_status.json()["items"]
        assert all(j["status"] == "failed" for j in status_items)
        assert any(j["id"] == str(job2.id) for j in status_items)

        # Test stage filter
        resp_stage = client.get("/documents/jobs?stage=INGESTION")
        assert resp_stage.status_code == 200
        stage_items = resp_stage.json()["items"]
        assert all(j["stage"] == "ingestion" for j in stage_items)

        # Test document_id filter
        resp_doc = client.get(f"/documents/jobs?document_id={doc.id}")
        assert resp_doc.status_code == 200
        doc_items = resp_doc.json()["items"]
        assert all(j["document_id"] == str(doc.id) for j in doc_items)

        # Test invalid filters return 400
        bad_status = client.get("/documents/jobs?status=UNKNOWN_STATUS")
        assert bad_status.status_code == 400
        assert "Invalid status" in bad_status.json()["detail"]

        bad_stage = client.get("/documents/jobs?stage=UNKNOWN_STAGE")
        assert bad_stage.status_code == 400
        assert "Invalid stage" in bad_stage.json()["detail"]

    finally:
        _clear_overrides()


# ── Archive, Disable & Restore Endpoints ─────────────────────────────────────


def test_archive_requires_admin(client: TestClient) -> None:
    _clear_overrides()
    resp = client.post(f"/documents/{uuid4()}/archive")
    assert resp.status_code == 401

    user = _make_user(role=UserRole.USER)
    _override_user(user)
    try:
        resp = client.post(f"/documents/{uuid4()}/archive")
        assert resp.status_code == 403
    finally:
        _clear_overrides()


async def test_archive_and_restore_document(
    client: TestClient, session: AsyncSession
) -> None:
    admin = _make_user(role=UserRole.ADMIN)
    _override_admin(admin)

    try:
        doc = Document(
            title="Contract Act 1872",
            type=DocumentType.ACT,
            source="India Code",
            status=DocumentStatus.READY,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        # 1. Archive document
        resp_arch = client.post(f"/documents/{doc.id}/archive")
        assert resp_arch.status_code == 200
        data_arch = resp_arch.json()
        assert data_arch["status"] == "disabled"

        # Verify DB persistence
        await session.refresh(doc)
        assert doc.status == DocumentStatus.DISABLED

        # 2. Test restore when document has NOT completed all 8 stages:
        # Must restore to FAILED to prevent incompletely indexed document from becoming READY
        resp_res_incomplete = client.post(f"/documents/{doc.id}/restore")
        assert resp_res_incomplete.status_code == 200
        assert resp_res_incomplete.json()["status"] == "failed"
        await session.refresh(doc)
        assert doc.status == DocumentStatus.FAILED

        # 3. Add all 8 completed stages for the document
        for stage in ProcessingJobStage:
            session.add(
                ProcessingJob(
                    document_id=doc.id,
                    stage=stage,
                    status=ProcessingJobStatus.COMPLETED,
                )
            )
        doc.status = DocumentStatus.DISABLED
        await session.commit()

        # 4. Restore document when all 8 stages are COMPLETED:
        # Must restore to READY
        resp_res_complete = client.post(f"/documents/{doc.id}/restore")
        assert resp_res_complete.status_code == 200
        assert resp_res_complete.json()["status"] == "ready"
        await session.refresh(doc)
        assert doc.status == DocumentStatus.READY

        # 5. Non-existent document returns 404
        non_existent_id = uuid4()
        assert client.post(f"/documents/{non_existent_id}/archive").status_code == 404
        assert client.post(f"/documents/{non_existent_id}/restore").status_code == 404

    finally:
        _clear_overrides()


# ── Reprocess Concurrency Conflict ───────────────────────────────────────────


async def test_reprocess_conflict_when_already_processing(
    client: TestClient, session: AsyncSession
) -> None:
    admin = _make_user(role=UserRole.ADMIN)
    _override_admin(admin)

    try:
        doc = Document(
            title="Concurrent Processing Act",
            type=DocumentType.ACT,
            source="India Code",
            status=DocumentStatus.PROCESSING,
            file_path="dummy/path.pdf",
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        resp = client.post(f"/documents/{doc.id}/reprocess")
        assert resp.status_code == 409
        assert "currently being processed" in resp.json()["detail"]

    finally:
        _clear_overrides()


# ── Startup Recovery for Interrupted RUNNING Jobs ─────────────────────────────


async def test_recover_interrupted_jobs(session: AsyncSession) -> None:
    # Set up interrupted document and running job
    interrupted_doc = Document(
        title="Interrupted Law",
        type=DocumentType.ACT,
        source="India Code",
        status=DocumentStatus.PROCESSING,
    )
    # Set up finished document and completed job
    healthy_doc = Document(
        title="Healthy Law",
        type=DocumentType.ACT,
        source="India Code",
        status=DocumentStatus.READY,
    )
    session.add_all([interrupted_doc, healthy_doc])
    await session.commit()
    await session.refresh(interrupted_doc)
    await session.refresh(healthy_doc)

    running_job = ProcessingJob(
        document_id=interrupted_doc.id,
        stage=ProcessingJobStage.GRAPH_POPULATION,
        status=ProcessingJobStatus.RUNNING,
    )
    completed_job = ProcessingJob(
        document_id=healthy_doc.id,
        stage=ProcessingJobStage.GRAPH_POPULATION,
        status=ProcessingJobStatus.COMPLETED,
    )
    pending_job = ProcessingJob(
        document_id=healthy_doc.id,
        stage=ProcessingJobStage.EXTRACTION,
        status=ProcessingJobStatus.PENDING,
    )
    session.add_all([running_job, completed_job, pending_job])
    await session.commit()
    await session.refresh(running_job)
    await session.refresh(completed_job)
    await session.refresh(pending_job)

    # Execute recovery
    recovered_count = await recover_interrupted_jobs(session)
    assert recovered_count >= 1

    # Verify state of interrupted job and document
    await session.refresh(running_job)
    await session.refresh(interrupted_doc)
    assert running_job.status == ProcessingJobStatus.FAILED
    assert running_job.error == INTERRUPTED_JOB_ERROR
    assert interrupted_doc.status == DocumentStatus.FAILED

    # Verify healthy records remained untouched
    await session.refresh(completed_job)
    await session.refresh(pending_job)
    await session.refresh(healthy_doc)
    assert completed_job.status == ProcessingJobStatus.COMPLETED
    assert completed_job.error is None
    assert pending_job.status == ProcessingJobStatus.PENDING
    assert healthy_doc.status == DocumentStatus.READY

    # Idempotent second execution
    assert await recover_interrupted_jobs(session) == 0
