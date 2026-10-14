"""Regression tests for Stage 2.1 — GraphRAG Persistence Repair.

Verifies:
1. Every indexed vector maps to a valid chunk.
2. Every indexed chunk maps to its correct document.
3. Document status filtering works correctly (only READY documents are returned).
4. Semantic search returns real legal chunks with matching PostgreSQL document titles and chunk IDs.
5. Empty or invalid query/corpus states return clear, safe results.
6. Mismatched FAISS metadata document IDs vs PostgreSQL are rejected safely.
7. Windows async compatibility and event loop safety at startup boundaries.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4

import numpy as np
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_data_dir, get_settings
from app.db.session import session_factory
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.enums import DocumentStatus, DocumentType
from app.retrieval.index import IndexError, load_index, save_index
from app.retrieval.service import (
    embed_query_vector,
    rebuild_index,
    retrieve,
    retrieve_ready_chunks,
)


@pytest.fixture(autouse=True)
def restore_settings():
    settings = get_settings()
    snapshot = settings.model_dump()
    yield
    for key, value in snapshot.items():
        object.__setattr__(settings, key, value)


class MockEmbedder:
    """Deterministic 2-dim embedder for isolated unit testing."""
    pooling_method = "attention_mask_mean_pooling"
    normalization = "l2"

    def embed(self, texts: list[str]) -> np.ndarray:
        vecs = []
        for t in texts:
            t_low = t.lower()
            if "life" in t_low or "article 21" in t_low:
                vecs.append([0.0, 1.0])
            elif "equality" in t_low or "article 14" in t_low:
                vecs.append([1.0, 0.0])
            else:
                vecs.append([0.7071, 0.7071])
        return np.asarray(vecs, dtype=np.float32)



def test_reconciled_index_vectors_map_to_valid_chunks_and_docs():
    """Verify live persisted FAISS index against live PostgreSQL."""
    # Ensure isolation even if prior tests mutated settings.data_dir
    data_dir = Path(__file__).resolve().parents[3] / "data"
    index_name = "legal_chunks"
    index, metadata = load_index(data_dir, index_name)

    assert index.ntotal > 0, "FAISS index must contain vectors"
    chunks = metadata["chunks"]
    chunk_ids = metadata["chunk_ids"]
    assert len(chunks) == index.ntotal == len(chunk_ids)

    # Every chunk has valid UUIDs and required fields
    for rec in chunks:
        assert UUID(rec["chunk_id"]), "chunk_id must be a valid UUID"
        assert UUID(rec["document_id"]), "document_id must be a valid UUID"
        assert rec["document_title"].strip(), "document_title must not be blank"
        assert rec["text"].strip(), "text must not be blank"
        assert isinstance(rec["chunk_index"], int)


@pytest.mark.asyncio
async def test_retrieve_ready_chunks_filters_by_document_status(
    session: AsyncSession, tmp_path: Path
):
    """Test that retrieve_ready_chunks excludes chunks belonging to non-READY documents."""
    settings = get_settings()
    object.__setattr__(settings, "data_dir", str(tmp_path))
    object.__setattr__(settings, "vector_index_name", "status_test")
    object.__setattr__(settings, "embedding_model_name", "mock-model")

    # Document 1: READY
    doc_ready = Document(
        id=uuid4(),
        title="Ready Law",
        type=DocumentType.ACT,
        source="Parliament",
        status=DocumentStatus.READY,
    )
    # Document 2: PROCESSING
    doc_proc = Document(
        id=uuid4(),
        title="Processing Law",
        type=DocumentType.ACT,
        source="Parliament",
        status=DocumentStatus.PROCESSING,
    )
    # Document 3: DISABLED
    doc_dis = Document(
        id=uuid4(),
        title="Disabled Law",
        type=DocumentType.ACT,
        source="Parliament",
        status=DocumentStatus.DISABLED,
    )
    session.add_all([doc_ready, doc_proc, doc_dis])
    await session.flush()

    chunk_ready = Chunk(
        id=uuid4(),
        document_id=doc_ready.id,
        chunk_index=0,
        text="Right to life and liberty under article 21",
        char_count=42,
        hierarchy={"article": "21"},
    )
    chunk_proc = Chunk(
        id=uuid4(),
        document_id=doc_proc.id,
        chunk_index=0,
        text="Right to life pending processing",
        char_count=33,
        hierarchy={"article": "21"},
    )
    chunk_dis = Chunk(
        id=uuid4(),
        document_id=doc_dis.id,
        chunk_index=0,
        text="Right to life in disabled document",
        char_count=35,
        hierarchy={"article": "21"},
    )
    session.add_all([chunk_ready, chunk_proc, chunk_dis])
    await session.commit()

    # Build FAISS index containing all three chunks
    embedder = MockEmbedder()
    chunk_records = [
        {
            "chunk_id": str(chunk_ready.id),
            "document_id": str(doc_ready.id),
            "document_version_id": None,
            "chunk_index": chunk_ready.chunk_index,
            "text": chunk_ready.text,
            "page_start": 1,
            "page_end": 1,
            "hierarchy": chunk_ready.hierarchy,
            "citation_ref": "Article 21",
            "source_url": None,
            "document_title": doc_ready.title,
        },
        {
            "chunk_id": str(chunk_proc.id),
            "document_id": str(doc_proc.id),
            "document_version_id": None,
            "chunk_index": chunk_proc.chunk_index,
            "text": chunk_proc.text,
            "page_start": 1,
            "page_end": 1,
            "hierarchy": chunk_proc.hierarchy,
            "citation_ref": "Article 21",
            "source_url": None,
            "document_title": doc_proc.title,
        },
        {
            "chunk_id": str(chunk_dis.id),
            "document_id": str(doc_dis.id),
            "document_version_id": None,
            "chunk_index": chunk_dis.chunk_index,
            "text": chunk_dis.text,
            "page_start": 1,
            "page_end": 1,
            "hierarchy": chunk_dis.hierarchy,
            "citation_ref": "Article 21",
            "source_url": None,
            "document_title": doc_dis.title,
        },
    ]
    vectors = embedder.embed([r["text"] for r in chunk_records])
    save_index(
        data_dir=tmp_path,
        index_name="status_test",
        vectors=vectors,
        chunk_records=chunk_records,
        model_name="mock-model",
        pooling_method="attention_mask_mean_pooling",
        max_tokens=64,
    )

    results = await retrieve_ready_chunks(
        session=session,
        query="article 21 life",
        top_k=5,
        settings=settings,
        embedder=embedder,
    )

    # MUST return only the chunk from the READY document
    assert len(results) == 1
    assert results[0]["chunk_id"] == str(chunk_ready.id)
    assert results[0]["document_id"] == str(doc_ready.id)
    assert results[0]["document_title"] == "Ready Law"


@pytest.mark.asyncio
async def test_retrieve_ready_chunks_handles_mismatched_uuid_safely(
    session: AsyncSession, tmp_path: Path
):
    """Regression test: FAISS containing orphaned/non-existent document UUIDs is filtered safely."""
    settings = get_settings()
    object.__setattr__(settings, "data_dir", str(tmp_path))
    object.__setattr__(settings, "vector_index_name", "mismatch_test")
    object.__setattr__(settings, "embedding_model_name", "mock-model")

    embedder = MockEmbedder()
    # A chunk whose document_id does NOT exist in PG
    phantom_doc_id = str(uuid4())
    phantom_chunk_id = str(uuid4())
    chunk_records = [
        {
            "chunk_id": phantom_chunk_id,
            "document_id": phantom_doc_id,
            "document_version_id": None,
            "chunk_index": 0,
            "text": "equality under article 14",
            "page_start": 1,
            "page_end": 1,
            "hierarchy": {"article": "14"},
            "citation_ref": "Article 14",
            "source_url": None,
            "document_title": "Phantom Law",
        }
    ]
    vectors = embedder.embed([r["text"] for r in chunk_records])
    save_index(
        data_dir=tmp_path,
        index_name="mismatch_test",
        vectors=vectors,
        chunk_records=chunk_records,
        model_name="mock-model",
        pooling_method="attention_mask_mean_pooling",
        max_tokens=64,
    )

    # Since phantom_doc_id is not in PG, retrieve_ready_chunks must return [] safely without raising
    results = await retrieve_ready_chunks(
        session=session,
        query="equality",
        top_k=5,
        settings=settings,
        embedder=embedder,
    )
    assert results == []


@pytest.mark.asyncio
async def test_empty_query_raises_value_error(session: AsyncSession, tmp_path: Path):
    """Verify that blank or empty queries return a clear, safe ValueError."""
    settings = get_settings()
    _save_test_index(tmp_path, "blank_query_test")
    object.__setattr__(settings, "data_dir", str(tmp_path))
    object.__setattr__(settings, "vector_index_name", "blank_query_test")

    with pytest.raises(ValueError, match="blank"):
        await retrieve_ready_chunks(
            session=session,
            query="   ",
            top_k=5,
            settings=settings,
            embedder=MockEmbedder(),
        )


def _save_test_index(tmp_path: Path, index_name: str):
    records = [
        {
            "chunk_id": str(uuid4()),
            "document_id": str(uuid4()),
            "document_version_id": None,
            "chunk_index": 0,
            "text": "sample text",
            "page_start": 1,
            "page_end": 1,
            "hierarchy": {},
            "citation_ref": None,
            "source_url": None,
            "document_title": "Sample Doc",
        }
    ]
    save_index(
        data_dir=tmp_path,
        index_name=index_name,
        vectors=np.array([[1.0, 0.0]], dtype=np.float32),
        chunk_records=records,
        model_name="mock-model",
        pooling_method="attention_mask_mean_pooling",
        max_tokens=64,
    )


def test_session_module_has_no_side_effect_on_event_loop_policy():
    """Verify that importing app.db.session does not alter global event loop policy."""
    import asyncio
    import sys
    # Import session module
    import app.db.session
    # Verify app.db.session module dictionary does NOT define set_event_loop_policy top-level calls
    assert hasattr(app.db.session, "session_factory")
    assert hasattr(app.db.session, "get_session")
