"""Phase 4 Isolated End-to-End PDF Ingestion Verification Test.

Strictly verifies:
1. PostgreSQL document, chunk, and processing job records across all 8 stages:
   INGESTION -> EXTRACTION -> CHUNKING -> EMBEDDING -> VECTOR_INDEX ->
   ENTITY_EXTRACTION -> RELATION_EXTRACTION -> GRAPH_POPULATION.
2. 768-dimensional FAISS vectors and metadata in an isolated sandbox.
3. Neo4j graph payload containing document, chunk, entity, and citation nodes/edges.
4. Production index files (data/indexes/legal_chunks/*) and production data are
   strictly UNTOUCHED and byte-identical before and after the test.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
import numpy as np
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.ingestion.pipeline import run_pipeline
from app.models import Chunk, Document, ProcessingJob
from app.models.enums import DocumentStatus, DocumentType, ProcessingJobStage, ProcessingJobStatus
from app.retrieval.index import load_index
from tests.helpers import make_minimal_legal_pdf


def compute_file_sha256(path: Path) -> str | None:
    """Return SHA-256 hex digest of file if it exists, else None."""
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class IsolatedDeterministicEmbedder:
    """Deterministic InLegalBERT embedder producing unit-normalized 768-dim vectors."""

    def __init__(self, dimension: int = 768) -> None:
        self.dimension = dimension
        self.pooling_method = "attention_mask_mean_pooling"

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        vectors = []
        for i, text in enumerate(texts):
            # Seed-like deterministic vector based on text length and index
            vec = np.full(self.dimension, float(len(text) % 17 + i + 1), dtype=np.float32)
            norm = np.linalg.norm(vec)
            vectors.append(vec / (norm if norm > 0 else 1.0))
        return np.vstack(vectors)


class IsolatedGraphClient:
    """Mock Neo4j client capturing graph updates."""

    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []

    async def replace_document_graph(self, payload: dict[str, Any]) -> None:
        self.payloads.append(payload)


@pytest.mark.asyncio
async def test_isolated_pdf_ingestion_end_to_end(
    session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()

    # 1. Snapshot production index hashes before running
    project_root = Path(__file__).resolve().parent.parent.parent
    prod_index_dir = project_root / "data" / "indexes" / "legal_chunks"
    prod_faiss_path = prod_index_dir / "index.faiss"
    prod_meta_path = prod_index_dir / "metadata.json"
    prod_emb_path = prod_index_dir / "embeddings.npy"

    pre_hash_faiss = compute_file_sha256(prod_faiss_path)
    pre_hash_meta = compute_file_sha256(prod_meta_path)
    pre_hash_emb = compute_file_sha256(prod_emb_path)

    # 2. Sandbox data directory to tmp_path
    monkeypatch.setattr("app.ingestion.pipeline.get_data_dir", lambda: tmp_path)

    # 3. Create fresh legal document in test DB
    pdf_bytes = make_minimal_legal_pdf()
    doc = Document(
        title="Constitution of India (Articles 1-5 Ingestion Test)",
        type=DocumentType.CONSTITUTION,
        source="Legislative Department",
        status=DocumentStatus.REGISTERED,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    # 4. Execute pipeline with isolated embedder and graph client
    embedder = IsolatedDeterministicEmbedder(dimension=768)
    graph_client = IsolatedGraphClient()

    chunks = await run_pipeline(
        document_id=doc.id,
        pdf_bytes=pdf_bytes,
        db=session,
        settings=settings,
        embedder=embedder,
        graph_client=graph_client,
    )

    # ── Assertions: 1. Pipeline Execution & PostgreSQL Records ────────────────
    assert len(chunks) > 0

    await session.refresh(doc)
    assert doc.status == DocumentStatus.READY

    # Verify Chunk records in DB
    chunk_records = (
        await session.scalars(select(Chunk).where(Chunk.document_id == doc.id).order_by(Chunk.chunk_index.asc()))
    ).all()
    assert len(chunk_records) == len(chunks)
    for c in chunk_records:
        assert len(c.text.strip()) > 0
        assert c.char_count > 0
        assert c.chunk_index >= 0

    # Verify all 8 ProcessingJob records
    jobs_res = await session.scalars(
        select(ProcessingJob).where(ProcessingJob.document_id == doc.id).order_by(ProcessingJob.created_at.asc())
    )
    jobs = {j.stage: j for j in jobs_res.all()}
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
        assert stage in jobs
        job = jobs[stage]
        assert job.status == ProcessingJobStatus.COMPLETED
        assert job.error is None
        assert job.created_at is not None
        assert job.updated_at is not None

    # ── Assertions: 2. 768-Dimensional FAISS Vector Index in Sandbox ──────────
    sandbox_index, sandbox_metadata = load_index(tmp_path, settings.vector_index_name)
    assert sandbox_index.ntotal == len(chunks)
    assert sandbox_index.d == 768
    assert sandbox_metadata["embedding_dimension"] == 768
    assert len(sandbox_metadata["chunks"]) == len(chunks)
    assert sandbox_metadata["chunks"][0]["document_id"] == str(doc.id)

    # ── Assertions: 3. Neo4j Graph Data Payload ───────────────────────────────
    assert len(graph_client.payloads) == 1
    graph_payload = graph_client.payloads[0]
    assert graph_payload["document_id"] == str(doc.id)
    assert len(graph_payload["chunks"]) == len(chunks)
    assert len(graph_payload["entity_nodes"]) > 0
    assert len(graph_payload["supported_by"]) > 0

    # ── Assertions: 4. Production Assets Unmodified & Intact ──────────────────
    post_hash_faiss = compute_file_sha256(prod_faiss_path)
    post_hash_meta = compute_file_sha256(prod_meta_path)
    post_hash_emb = compute_file_sha256(prod_emb_path)

    assert post_hash_faiss == pre_hash_faiss, "Production FAISS index was mutated!"
    assert post_hash_meta == pre_hash_meta, "Production metadata.json was mutated!"
    assert post_hash_emb == pre_hash_emb, "Production embeddings.npy was mutated!"
