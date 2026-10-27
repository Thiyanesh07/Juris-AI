"""Phase 6 Isolated Ingestion Pipeline Test Suite.

Validates the complete document ingestion lifecycle in a safe, fully isolated
local environment:
- Zero-byte, malformed, encrypted, and unsupported files
- Extraction failures and expected document/job status transitions
- Vector-index failure and preservation of pre-existing test vectors
- Graph-population failure and documented recovery behavior
- Duplicate upload behavior and idempotency
- Reprocessing idempotency
- Upload-to-ready lifecycle and filesystem artifacts
- Retrieval of uploaded synthetic legal documents
- Citation-to-document/page traceability and PDF route behavior
- Cleanup and preservation of protected repository artifacts
"""

from __future__ import annotations

import io
from pathlib import Path
from uuid import UUID, uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document, ProcessingJob
from app.models.enums import DocumentStatus, DocumentType, ProcessingJobStage, ProcessingJobStatus
from app.retrieval.index import load_index
from tests.helpers import (
    make_encrypted_pdf,
    make_image_only_pdf,
    make_minimal_legal_pdf,
    make_truncated_pdf,
)
from tests.ingestion_harness import IsolatedIngestionHarness, ingestion_harness


# ── Helper for Rejection Assertions ───────────────────────────────────────────


async def _assert_zero_records_or_artifacts(
    session: AsyncSession,
    harness: IsolatedIngestionHarness,
) -> None:
    """Assert that no document, job, chunk, vector, or graph state was persisted."""
    doc_count = (await session.execute(select(func.count(Document.id)))).scalar_one()
    assert doc_count == 0, f"Expected 0 Document rows, found {doc_count}"

    job_count = (await session.execute(select(func.count(ProcessingJob.id)))).scalar_one()
    assert job_count == 0, f"Expected 0 ProcessingJob rows, found {job_count}"

    chunk_count = (await session.execute(select(func.count(Chunk.id)))).scalar_one()
    assert chunk_count == 0, f"Expected 0 Chunk rows, found {chunk_count}"

    assert len(harness.graph_client.replace_history) == 0, "Expected 0 graph write operations"

    faiss_file = harness.tmp_path / "indexes" / harness.test_index_name / "index.faiss"
    assert not faiss_file.exists(), "Expected FAISS index file to not exist"


# ── 1. File Validation Rejections ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_zero_byte_file_rejected(
    ingestion_harness: IsolatedIngestionHarness,
    client: TestClient,
    session: AsyncSession,
) -> None:
    """Uploading a 0-byte file must be rejected immediately without creating database records."""
    resp = ingestion_harness.upload_document(
        client=client,
        pdf_bytes=b"",
        title="Zero Byte Act",
        filename="empty.pdf",
    )
    assert resp.status_code == 400
    assert "uploaded file is empty" in resp.json()["detail"].lower()
    await _assert_zero_records_or_artifacts(session, ingestion_harness)


@pytest.mark.asyncio
async def test_upload_malformed_pdf_rejected(
    ingestion_harness: IsolatedIngestionHarness,
    client: TestClient,
    session: AsyncSession,
) -> None:
    """Corrupted/truncated PDF header must be rejected by validate_pdf with 400."""
    resp = ingestion_harness.upload_document(
        client=client,
        pdf_bytes=make_truncated_pdf(),
        title="Malformed Act",
        filename="corrupt.pdf",
    )
    assert resp.status_code == 400
    assert "invalid pdf" in resp.json()["detail"].lower()
    await _assert_zero_records_or_artifacts(session, ingestion_harness)


@pytest.mark.asyncio
async def test_upload_encrypted_pdf_rejected(
    ingestion_harness: IsolatedIngestionHarness,
    client: TestClient,
    session: AsyncSession,
) -> None:
    """Password-protected PDFs must be rejected by validator with 400."""
    resp = ingestion_harness.upload_document(
        client=client,
        pdf_bytes=make_encrypted_pdf(password="secret"),
        title="Encrypted Act",
        filename="encrypted.pdf",
    )
    assert resp.status_code == 400
    assert "password-protected" in resp.json()["detail"].lower()
    await _assert_zero_records_or_artifacts(session, ingestion_harness)


@pytest.mark.asyncio
async def test_upload_unsupported_media_type_rejected(
    ingestion_harness: IsolatedIngestionHarness,
    client: TestClient,
    session: AsyncSession,
) -> None:
    """Uploading non-PDF MIME types must be rejected with HTTP 415."""
    resp = client.post(
        "/documents/upload",
        params={"title": "Plain Text Doc", "type": "ACT"},
        files={"file": ("notes.txt", io.BytesIO(b"Ordinary text"), "text/plain")},
    )
    assert resp.status_code == 415
    assert "only pdf files are accepted" in resp.json()["detail"].lower()
    await _assert_zero_records_or_artifacts(session, ingestion_harness)


@pytest.mark.asyncio
async def test_upload_scanned_image_only_pdf_rejected(
    ingestion_harness: IsolatedIngestionHarness,
    client: TestClient,
    session: AsyncSession,
) -> None:
    """Image-only PDFs (no text layer) must be rejected with 400."""
    resp = ingestion_harness.upload_document(
        client=client,
        pdf_bytes=make_image_only_pdf(),
        title="Scanned Act",
        filename="scanned.pdf",
    )
    assert resp.status_code == 400
    assert "image-only" in resp.json()["detail"].lower()
    await _assert_zero_records_or_artifacts(session, ingestion_harness)


# ── 2. Extraction Failures and Status Transitions ─────────────────────────────


@pytest.mark.asyncio
async def test_extraction_failure_document_and_job_status(
    ingestion_harness: IsolatedIngestionHarness,
    client: TestClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simulated extraction failure must mark EXTRACTION job and Document as FAILED."""
    def failing_extract_pages(*args, **kwargs):
        raise RuntimeError("Simulated PDF text stream decoding failure")

    monkeypatch.setattr("app.ingestion.pipeline.extract_pages", failing_extract_pages)

    pdf_bytes = make_minimal_legal_pdf()
    resp = ingestion_harness.upload_document(
        client=client,
        pdf_bytes=pdf_bytes,
        title="Extraction Failure Test",
    )
    assert resp.status_code == 202
    doc_id = UUID(resp.json()["document_id"])

    # Document should have completed background processing and reached FAILED
    doc = await ingestion_harness.await_document_status(session, doc_id, DocumentStatus.FAILED)
    assert doc.status == DocumentStatus.FAILED

    # Verify job records
    jobs = await ingestion_harness.get_jobs_from_db(session, doc_id)
    jobs_by_stage = {j.stage: j for j in jobs}

    assert jobs_by_stage[ProcessingJobStage.INGESTION].status == ProcessingJobStatus.COMPLETED
    assert jobs_by_stage[ProcessingJobStage.EXTRACTION].status == ProcessingJobStatus.FAILED
    assert "decoding failure" in (jobs_by_stage[ProcessingJobStage.EXTRACTION].error or "")

    # Subsequent stages must not be completed
    assert ProcessingJobStage.CHUNKING not in jobs_by_stage or jobs_by_stage[ProcessingJobStage.CHUNKING].status != ProcessingJobStatus.COMPLETED

    # No chunks should be in the database
    chunks = await ingestion_harness.get_chunks_from_db(session, doc_id)
    assert len(chunks) == 0


# ── 3. Vector-Index Failure and Vector Preservation ───────────────────────────


@pytest.mark.asyncio
async def test_vector_index_failure_preserves_preexisting_vectors(
    ingestion_harness: IsolatedIngestionHarness,
    client: TestClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Downstream vector index failure on a new document must preserve pre-existing vectors."""
    # Step 1: Ingest Document 1 successfully
    pdf1 = make_minimal_legal_pdf()
    resp1 = ingestion_harness.upload_document(
        client=client,
        pdf_bytes=pdf1,
        title="Baseline Legal Act",
        filename="act1.pdf",
    )
    assert resp1.status_code == 202
    doc1_id = UUID(resp1.json()["document_id"])
    doc1 = await ingestion_harness.await_document_status(session, doc1_id, DocumentStatus.READY)
    assert doc1.status == DocumentStatus.READY

    # Verify baseline index was created
    idx_before, meta_before = load_index(ingestion_harness.tmp_path, ingestion_harness.test_index_name)
    initial_vector_count = idx_before.ntotal
    assert initial_vector_count > 0
    assert len(meta_before["chunks"]) == initial_vector_count

    # Step 2: Ingest Document 2 with simulated FAISS update failure
    # Modify second PDF slightly by title so it has unique file_hash
    pdf2 = make_minimal_legal_pdf()

    real_update_index = __import__("app.retrieval.index", fromlist=["update_index_incremental"]).update_index_incremental

    async def conditional_fail_update(**kwargs):
        if kwargs.get("document_id") != str(doc1_id):
            raise RuntimeError("Simulated FAISS index update failure")
        return await real_update_index(**kwargs)

    monkeypatch.setattr("app.ingestion.pipeline.update_index_incremental", conditional_fail_update)

    # Use unique title/content
    resp2 = ingestion_harness.upload_document(
        client=client,
        pdf_bytes=pdf2 + b"\n%extra_comment",
        title="Second Failing Act",
        filename="act2.pdf",
    )
    assert resp2.status_code == 202
    doc2_id = UUID(resp2.json()["document_id"])

    doc2 = await ingestion_harness.await_document_status(session, doc2_id, DocumentStatus.FAILED)
    assert doc2.status == DocumentStatus.FAILED

    jobs2 = await ingestion_harness.get_jobs_from_db(session, doc2_id)
    jobs2_by_stage = {j.stage: j for j in jobs2}
    assert jobs2_by_stage[ProcessingJobStage.VECTOR_INDEX].status == ProcessingJobStatus.FAILED

    # Step 3: Verify pre-existing Document 1 index is completely intact
    idx_after, meta_after = load_index(ingestion_harness.tmp_path, ingestion_harness.test_index_name)
    assert idx_after.ntotal == initial_vector_count
    assert len(meta_after["chunks"]) == initial_vector_count
    assert meta_after["chunks"][0]["document_id"] == str(doc1_id)


# ── 4. Graph Population Failure and Recovery Behavior ─────────────────────────


@pytest.mark.asyncio
async def test_graph_population_failure_and_retry_recovery(
    ingestion_harness: IsolatedIngestionHarness,
    client: TestClient,
    session: AsyncSession,
) -> None:
    """Graph failure preserves dense chunks and allows successful retry via /retry-graph."""
    # Step 1: Configure graph client to simulate failure
    ingestion_harness.graph_client.should_fail_on_replace = True

    pdf_bytes = make_minimal_legal_pdf()
    resp = ingestion_harness.upload_document(
        client=client,
        pdf_bytes=pdf_bytes,
        title="Graph Resilience Act",
    )
    assert resp.status_code == 202
    doc_id = UUID(resp.json()["document_id"])

    # Document should reach FAILED because graph population failed
    doc = await ingestion_harness.await_document_status(session, doc_id, DocumentStatus.FAILED)
    assert doc.status == DocumentStatus.FAILED

    jobs = await ingestion_harness.get_jobs_from_db(session, doc_id)
    jobs_by_stage = {j.stage: j for j in jobs}
    assert jobs_by_stage[ProcessingJobStage.GRAPH_POPULATION].status == ProcessingJobStatus.FAILED

    # Chunks and vectors MUST be preserved (architectural invariant)
    chunks = await ingestion_harness.get_chunks_from_db(session, doc_id)
    assert len(chunks) > 0

    idx, meta = load_index(ingestion_harness.tmp_path, ingestion_harness.test_index_name)
    assert idx.ntotal == len(chunks)

    # Step 2: Heal graph client and trigger retry-graph endpoint
    ingestion_harness.graph_client.should_fail_on_replace = False

    retry_resp = client.post(f"/documents/{doc_id}/retry-graph")
    assert retry_resp.status_code == 200
    retry_body = retry_resp.json()
    assert retry_body["success"] is True
    assert retry_body["document_id"] == str(doc_id)

    # Verify graph payload was recorded
    assert len(ingestion_harness.graph_client.replace_history) > 0
    latest_payload = ingestion_harness.graph_client.replace_history[-1]
    assert latest_payload["document_id"] == str(doc_id)
    assert len(latest_payload["chunks"]) == len(chunks)


# ── 5. Duplicate Upload Behavior ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_duplicate_upload_behavior(
    ingestion_harness: IsolatedIngestionHarness,
    client: TestClient,
    session: AsyncSession,
) -> None:
    """Uploading the exact same file twice must return duplicate=True on the second upload."""
    pdf_bytes = make_minimal_legal_pdf()

    # First upload
    resp1 = ingestion_harness.upload_document(
        client=client,
        pdf_bytes=pdf_bytes,
        title="Initial Act",
    )
    assert resp1.status_code == 202
    data1 = resp1.json()
    assert data1["duplicate"] is False
    doc_id1 = UUID(data1["document_id"])

    # Await first ingestion to complete
    doc1 = await ingestion_harness.await_document_status(session, doc_id1, DocumentStatus.READY)
    assert doc1.status == DocumentStatus.READY
    assert doc1.file_hash is not None

    # Second upload with identical bytes
    resp2 = ingestion_harness.upload_document(
        client=client,
        pdf_bytes=pdf_bytes,
        title="Attempted Duplicate Act",
    )
    assert resp2.status_code == 202
    data2 = resp2.json()
    assert data2["duplicate"] is True
    assert data2["document_id"] == str(doc_id1)
    assert "already exists" in data2["message"].lower()

    # Verify only 1 document exists in the DB
    doc_count = (await session.execute(select(func.count()).select_from(Document))).scalar_one()
    assert doc_count == 1


# ── 6. Reprocessing and Idempotency ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_reprocess_document_idempotency(
    ingestion_harness: IsolatedIngestionHarness,
    client: TestClient,
    session: AsyncSession,
) -> None:
    """Reprocessing a document must replace chunks and vectors cleanly without duplication."""
    pdf_bytes = make_minimal_legal_pdf()

    # Initial ingestion
    resp = ingestion_harness.upload_document(
        client=client,
        pdf_bytes=pdf_bytes,
        title="Reprocess Target Act",
    )
    assert resp.status_code == 202
    doc_id = UUID(resp.json()["document_id"])
    doc = await ingestion_harness.await_document_status(session, doc_id, DocumentStatus.READY)
    assert doc.status == DocumentStatus.READY

    initial_chunks = await ingestion_harness.get_chunks_from_db(session, doc_id)
    initial_chunk_count = len(initial_chunks)
    assert initial_chunk_count > 0

    idx_before, _ = load_index(ingestion_harness.tmp_path, ingestion_harness.test_index_name)
    assert idx_before.ntotal == initial_chunk_count

    # Trigger reprocess endpoint
    reprocess_resp = client.post(f"/documents/{doc_id}/reprocess")
    assert reprocess_resp.status_code == 202

    # Await reprocess completion
    doc_after = await ingestion_harness.await_document_status(session, doc_id, DocumentStatus.READY)
    assert doc_after.status == DocumentStatus.READY

    # Verify chunk count has NOT doubled
    chunks_after = await ingestion_harness.get_chunks_from_db(session, doc_id)
    assert len(chunks_after) == initial_chunk_count

    # Verify FAISS index vector count has NOT doubled
    idx_after, _ = load_index(ingestion_harness.tmp_path, ingestion_harness.test_index_name)
    assert idx_after.ntotal == initial_chunk_count


# ── 7. Full Upload-to-Ready Lifecycle and Artifacts ───────────────────────────


@pytest.mark.asyncio
async def test_upload_to_ready_lifecycle_and_artefacts(
    ingestion_harness: IsolatedIngestionHarness,
    client: TestClient,
    session: AsyncSession,
) -> None:
    """End-to-end verification of all 8 pipeline stages and on-disk sandbox artifacts."""
    pdf_bytes = make_minimal_legal_pdf()

    resp = ingestion_harness.upload_document(
        client=client,
        pdf_bytes=pdf_bytes,
        title="Constitution of India (Articles 1-5)",
        doc_type="CONSTITUTION",
        source="Legislative Department",
        source_url="https://legislative.gov.in/constitution-of-india",
    )
    assert resp.status_code == 202
    doc_id = UUID(resp.json()["document_id"])

    # 1. Document status should reach READY
    doc = await ingestion_harness.await_document_status(session, doc_id, DocumentStatus.READY)
    assert doc.status == DocumentStatus.READY
    assert doc.type == DocumentType.CONSTITUTION
    assert doc.file_hash is not None

    # 2. All 8 ProcessingJob stages must be COMPLETED
    jobs = await ingestion_harness.get_jobs_from_db(session, doc_id)
    assert len(jobs) == 8
    required_stages = [
        ProcessingJobStage.INGESTION,
        ProcessingJobStage.EXTRACTION,
        ProcessingJobStage.CHUNKING,
        ProcessingJobStage.EMBEDDING,
        ProcessingJobStage.VECTOR_INDEX,
        ProcessingJobStage.ENTITY_EXTRACTION,
        ProcessingJobStage.RELATION_EXTRACTION,
        ProcessingJobStage.GRAPH_POPULATION,
    ]
    for stage in required_stages:
        matching = [j for j in jobs if j.stage == stage]
        assert len(matching) == 1, f"Missing job for stage {stage}"
        assert matching[0].status == ProcessingJobStatus.COMPLETED
        assert matching[0].error is None

    # 3. Chunks in DB
    chunks = await ingestion_harness.get_chunks_from_db(session, doc_id)
    assert len(chunks) > 0
    for ch in chunks:
        assert len(ch.text) > 0
        assert ch.char_count == len(ch.text)

    # 4. On-disk files in tmp_path sandbox
    tmp_path = ingestion_harness.tmp_path
    raw_pdf = tmp_path / "raw" / str(doc_id) / "original.pdf"
    assert raw_pdf.is_file()
    assert raw_pdf.read_bytes() == pdf_bytes

    pages_file = tmp_path / "processed" / str(doc_id) / "pages.jsonl"
    assert pages_file.is_file()

    structure_file = tmp_path / "processed" / str(doc_id) / "structure.json"
    assert structure_file.is_file()

    chunks_file = tmp_path / "chunks" / str(doc_id) / "chunks.jsonl"
    assert chunks_file.is_file()

    faiss_file = tmp_path / "indexes" / ingestion_harness.test_index_name / "index.faiss"
    assert faiss_file.is_file()

    meta_file = tmp_path / "indexes" / ingestion_harness.test_index_name / "metadata.json"
    assert meta_file.is_file()

    emb_file = tmp_path / "indexes" / ingestion_harness.test_index_name / "embeddings.npy"
    assert emb_file.is_file()

    # 5. In-memory graph double verified
    assert len(ingestion_harness.graph_client.replace_history) == 1
    graph_payload = ingestion_harness.graph_client.replace_history[0]
    assert graph_payload["document_id"] == str(doc_id)
    assert len(graph_payload["chunks"]) == len(chunks)


# ── 8. Retrieval and Citation Traceability ────────────────────────────────────


@pytest.mark.asyncio
async def test_retrieval_and_citation_traceability(
    ingestion_harness: IsolatedIngestionHarness,
    client: TestClient,
    session: AsyncSession,
) -> None:
    """Verifies that an ingested legal document can be retrieved and citations trace to PDF."""
    pdf_bytes = make_minimal_legal_pdf()

    upload_resp = ingestion_harness.upload_document(
        client=client,
        pdf_bytes=pdf_bytes,
        title="Constitution of India",
        doc_type="CONSTITUTION",
    )
    assert upload_resp.status_code == 202
    doc_id = UUID(upload_resp.json()["document_id"])
    await ingestion_harness.await_document_status(session, doc_id, DocumentStatus.READY)

    # Search for terms contained in the uploaded document
    search_resp = client.post(
        "/retrieval/search",
        json={"query": "India, that is Bharat, shall be a Union of States", "top_k": 3},
    )
    assert search_resp.status_code == 200
    search_body = search_resp.json()
    assert len(search_body["results"]) > 0

    top_hit = search_body["results"][0]
    assert top_hit["document_id"] == str(doc_id)
    assert "Bharat" in top_hit["text"] or "Union of States" in top_hit["text"]

    # Verify citation fields
    assert top_hit.get("page_start") is not None
    assert top_hit.get("page_start") >= 1
    assert top_hit.get("citation_ref") in ("Part I", "Article 1", "Constitution") or "Part" in (top_hit.get("citation_ref") or "")

    # Verify PDF route serves the source document
    pdf_resp = client.get(f"/documents/{doc_id}/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert len(pdf_resp.content) == len(pdf_bytes)

    # Verify invalid document ID returns 404
    missing_resp = client.get(f"/documents/{uuid4()}/pdf")
    assert missing_resp.status_code == 404


# ── 9. Protected Repository Artifact Preservation ─────────────────────────────


def test_protected_repository_artifacts_unmodified(
    ingestion_harness: IsolatedIngestionHarness,
) -> None:
    """Asserts that all protected production FAISS indices and corpus files remain untouched."""
    # Calling verify() on ProtectedArtifactGuard checks current hash against initial snapshot
    ingestion_harness.artifact_guard.verify()
