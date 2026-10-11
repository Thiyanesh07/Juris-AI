"""Regression tests for Phase 4 Step 8: FAISS Save Safety & CLI Retrieval Eligibility.

Covers:
1. Serialization failure cleans temporary files and leaves the original destination files intact.
2. Replacement failure preserves the original exception and never deletes unrelated destination files.
3. CLI query excludes non-READY and missing-document chunks.
4. Empty eligible results are handled cleanly without exceptions.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

import numpy as np
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli import _query
from app.core.config import Settings, get_settings
from app.models.document import Document
from app.models.enums import DocumentStatus, DocumentType
from app.retrieval.index import (
    IndexError,
    load_index,
    save_index,
)


# ── Test Helpers & Doubles ───────────────────────────────────────────────────


class FakeEmbedder:
    pooling_method = "attention_mask_mean_pooling"
    normalization = "l2"

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors: list[list[float]] = []
        for text in texts:
            if "equality" in text.lower():
                vectors.append([1.0, 0.0])
            else:
                vectors.append([0.0, 1.0])
        return np.asarray(vectors, dtype=np.float32)


def _make_chunk_record(
    chunk_id: UUID, doc_id: UUID, text: str, index: int, title: str | None = None
) -> dict:
    return {
        "chunk_id": str(chunk_id),
        "document_id": str(doc_id),
        "document_version_id": None,
        "chunk_index": index,
        "text": text,
        "page_start": 1,
        "page_end": 1,
        "hierarchy": {"section": "Test"},
        "citation_ref": f"Doc {index}",
        "source_url": None,
        "document_title": title or f"Test Document {index}",
    }


def _save_initial_index(dir_path: Path, index_name: str = "test") -> list[dict]:
    doc_id = uuid4()
    chunks = [
        _make_chunk_record(uuid4(), doc_id, "equality under law", 0),
        _make_chunk_record(uuid4(), doc_id, "protection of life", 1),
    ]
    vectors = np.eye(2, dtype=np.float32)
    save_index(
        data_dir=dir_path,
        index_name=index_name,
        vectors=vectors,
        chunk_records=chunks,
        model_name="test-model",
        pooling_method="attention_mask_mean_pooling",
        max_tokens=64,
    )
    return chunks


# ── Test 1: Serialization Failure Cleans Temp Files ──────────────────────────


def test_serialization_failure_cleans_temporary_files_and_preserves_destinations(
    tmp_path: Path,
) -> None:
    """When serialization (faiss.write_index or np.save) fails:

    1. Temporary files are safely cleaned up from disk.
    2. Any existing destination files remain completely intact.
    3. The original serialization exception is preserved and re-raised.
    """
    index_name = "test_cleanup"
    index_dir = tmp_path / "indexes" / index_name

    # Step A: Establish valid pre-existing destination files
    _save_initial_index(tmp_path, index_name)
    assert (index_dir / "index.faiss").is_file()
    assert (index_dir / "embeddings.npy").is_file()
    assert (index_dir / "metadata.json").is_file()

    orig_faiss_bytes = (index_dir / "index.faiss").read_bytes()
    orig_npy_bytes = (index_dir / "embeddings.npy").read_bytes()
    orig_json_bytes = (index_dir / "metadata.json").read_bytes()

    # Step B: Attempt a save where faiss.write_index fails
    new_doc_id = uuid4()
    new_chunks = [_make_chunk_record(uuid4(), new_doc_id, "new content", 0)]
    new_vectors = np.array([[1.0, 0.0]], dtype=np.float32)

    with patch("faiss.write_index", side_effect=IOError("Simulated disk error during FAISS serialization")):
        with pytest.raises(IOError, match="Simulated disk error during FAISS serialization"):
            save_index(
                data_dir=tmp_path,
                index_name=index_name,
                vectors=new_vectors,
                chunk_records=new_chunks,
                model_name="test-model",
                pooling_method="attention_mask_mean_pooling",
                max_tokens=64,
            )

    # Verify no orphaned temporary files remain in index directory
    all_files = list(index_dir.iterdir())
    temp_files = [f for f in all_files if f.name not in {"index.faiss", "embeddings.npy", "metadata.json"}]
    assert temp_files == [], f"Found orphaned temporary files: {temp_files}"

    # Verify original destination files were preserved intact
    assert (index_dir / "index.faiss").read_bytes() == orig_faiss_bytes
    assert (index_dir / "embeddings.npy").read_bytes() == orig_npy_bytes
    assert (index_dir / "metadata.json").read_bytes() == orig_json_bytes

    # Verify index remains loadable and valid
    loaded_index, loaded_meta = load_index(tmp_path, index_name)
    assert loaded_index.ntotal == 2


def test_serialization_failure_on_initial_creation_leaves_no_temp_files(
    tmp_path: Path,
) -> None:
    """When serialization fails during initial index creation (no destination files exist yet),

    all temporary files are deleted and no orphans remain.
    """
    index_name = "fresh_index"
    index_dir = tmp_path / "indexes" / index_name

    new_doc_id = uuid4()
    new_chunks = [_make_chunk_record(uuid4(), new_doc_id, "brand new text", 0)]
    new_vectors = np.array([[1.0, 0.0]], dtype=np.float32)

    with patch("numpy.save", side_effect=RuntimeError("Simulated numpy serialization failure")):
        with pytest.raises(RuntimeError, match="Simulated numpy serialization failure"):
            save_index(
                data_dir=tmp_path,
                index_name=index_name,
                vectors=new_vectors,
                chunk_records=new_chunks,
                model_name="test-model",
                pooling_method="attention_mask_mean_pooling",
                max_tokens=64,
            )

    # Only empty index_dir or no files should exist
    if index_dir.exists():
        assert list(index_dir.iterdir()) == []


# ── Test 2: Replacement Failure Preserves Exception & Destination Files ───────


def test_replacement_failure_preserves_exception_and_leaves_unrelated_destinations(
    tmp_path: Path,
) -> None:
    """When a file replacement fails midway (e.g. on embeddings.npy):

    1. The original replacement exception is preserved.
    2. Remaining temporary files are safely deleted.
    3. Destination files are never deleted by cleanup.
    4. Subsequent load detects that files are out of sync rather than silently corrupt.
    """
    index_name = "test_replace_failure"
    index_dir = tmp_path / "indexes" / index_name

    _save_initial_index(tmp_path, index_name)
    orig_json_bytes = (index_dir / "metadata.json").read_bytes()

    new_doc_id = uuid4()
    new_chunks = [
        _make_chunk_record(uuid4(), new_doc_id, "chunk alpha", 0),
        _make_chunk_record(uuid4(), new_doc_id, "chunk beta", 1),
        _make_chunk_record(uuid4(), new_doc_id, "chunk gamma", 2),
    ]
    new_vectors = np.array([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]], dtype=np.float32)

    real_replace = Path.replace

    def selective_replace(self: Path, target: Path) -> Path:
        if target.name == "embeddings.npy":
            raise PermissionError("Simulated OS lock/permission failure replacing embeddings.npy")
        return real_replace(self, target)

    with patch.object(Path, "replace", selective_replace):
        with pytest.raises(PermissionError, match="replacing embeddings.npy"):
            save_index(
                data_dir=tmp_path,
                index_name=index_name,
                vectors=new_vectors,
                chunk_records=new_chunks,
                model_name="test-model",
                pooling_method="attention_mask_mean_pooling",
                max_tokens=64,
            )

    # Verify temporary files were removed
    all_files = list(index_dir.iterdir())
    temp_files = [f for f in all_files if f.name not in {"index.faiss", "embeddings.npy", "metadata.json"}]
    assert temp_files == [], f"Found orphaned temporary files after replacement failure: {temp_files}"

    # Verify unrelated destination file (metadata.json) was not deleted
    assert (index_dir / "metadata.json").is_file()
    assert (index_dir / "metadata.json").read_bytes() == orig_json_bytes

    # Consistency risk validation: index.faiss was replaced with 3 vectors, but metadata still has 2.
    # Verify that load_index rejects this safely instead of serving corrupted data:
    with pytest.raises(IndexError, match="Vector index and chunk metadata are out of sync"):
        load_index(tmp_path, index_name)


# ── Test 3: CLI Query Enforces Document.status == READY ───────────────────────


async def test_cli_query_excludes_non_ready_and_missing_documents(
    session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The developer CLI 'query' command must only return chunks whose document

    in PostgreSQL has status == READY. Non-READY (FAILED, PROCESSING, DISABLED)
    and missing documents must be strictly excluded.
    """
    ready_doc_id = uuid4()
    failed_doc_id = uuid4()
    processing_doc_id = uuid4()
    missing_doc_id = uuid4()

    index_name = "test_cli_index"
    test_settings = Settings(
        database_url=get_settings().database_url,
        vector_index_name=index_name,
        retrieval_default_top_k=10,
        retrieval_max_top_k=20,
    )

    # Seed PostgreSQL with documents of various statuses
    doc_ready = Document(
        id=ready_doc_id,
        title="Ready Legal Document",
        type=DocumentType.ACT,
        source="test",
        status=DocumentStatus.READY,
    )
    doc_failed = Document(
        id=failed_doc_id,
        title="Failed Legal Document",
        type=DocumentType.RULE,
        source="test",
        status=DocumentStatus.FAILED,
    )
    doc_processing = Document(
        id=processing_doc_id,
        title="Processing Legal Document",
        type=DocumentType.STATUTE,
        source="test",
        status=DocumentStatus.PROCESSING,
    )
    session.add_all([doc_ready, doc_failed, doc_processing])
    await session.commit()

    # Index chunks for ALL documents (including missing_doc_id)
    chunks = [
        _make_chunk_record(
            uuid4(),
            ready_doc_id,
            "equality before the law in constitution",
            0,
            title="Ready Legal Document",
        ),
        _make_chunk_record(uuid4(), failed_doc_id, "equality in failed rules text", 1),
        _make_chunk_record(uuid4(), processing_doc_id, "equality in processing ordinance", 2),
        _make_chunk_record(uuid4(), missing_doc_id, "equality in deleted document", 3),
    ]
    # All vectors have identical direction so all 4 match the query
    vectors = np.tile([1.0, 0.0], (4, 1)).astype(np.float32)

    save_index(
        data_dir=tmp_path,
        index_name=index_name,
        vectors=vectors,
        chunk_records=chunks,
        model_name=test_settings.embedding_model_name,
        pooling_method="attention_mask_mean_pooling",
        max_tokens=64,
    )

    # Intercept session_factory, settings, embedder, and data_dir
    class MockSessionFactory:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr("app.cli.session_factory", lambda: MockSessionFactory())
    monkeypatch.setattr("app.cli.get_settings", lambda: test_settings)
    monkeypatch.setattr("app.retrieval.service.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("app.retrieval.service.build_embedder", lambda _: FakeEmbedder())

    captured_stdout = io.StringIO()
    with patch("sys.stdout", captured_stdout):
        exit_code = await _query(query="equality", top_k=5)

    assert exit_code == 0
    raw_output = captured_stdout.getvalue().strip()
    results = json.loads(raw_output)

    # Exactly 1 chunk must be returned (from the READY document)
    assert len(results) == 1
    assert results[0]["document_id"] == str(ready_doc_id)
    assert results[0]["document_title"] == "Ready Legal Document"
    assert results[0]["rank"] == 1

    # Verify no chunks from failed, processing, or missing documents
    returned_doc_ids = {r["document_id"] for r in results}
    assert str(failed_doc_id) not in returned_doc_ids
    assert str(processing_doc_id) not in returned_doc_ids
    assert str(missing_doc_id) not in returned_doc_ids


# ── Test 4: Empty Eligible Results Handled Cleanly ────────────────────────────


async def test_cli_query_empty_eligible_results_handled_cleanly(
    session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the FAISS index contains matches but NONE belong to READY documents

    in PostgreSQL, CLI query returns 0 and outputs empty JSON array [].
    """
    failed_doc_id = uuid4()
    doc_failed = Document(
        id=failed_doc_id,
        title="Failed Legal Document Only",
        type=DocumentType.ACT,
        source="test",
        status=DocumentStatus.FAILED,
    )
    session.add(doc_failed)
    await session.commit()

    chunks = [
        _make_chunk_record(uuid4(), failed_doc_id, "equality before law only in failed doc", 0),
    ]
    vectors = np.array([[1.0, 0.0]], dtype=np.float32)

    index_name = "test_empty_eligible"
    test_settings = Settings(
        database_url=get_settings().database_url,
        vector_index_name=index_name,
        retrieval_default_top_k=5,
        retrieval_max_top_k=20,
    )

    save_index(
        data_dir=tmp_path,
        index_name=index_name,
        vectors=vectors,
        chunk_records=chunks,
        model_name=test_settings.embedding_model_name,
        pooling_method="attention_mask_mean_pooling",
        max_tokens=64,
    )

    class MockSessionFactory:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr("app.cli.session_factory", lambda: MockSessionFactory())
    monkeypatch.setattr("app.cli.get_settings", lambda: test_settings)
    monkeypatch.setattr("app.retrieval.service.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("app.retrieval.service.build_embedder", lambda _: FakeEmbedder())

    captured_stdout = io.StringIO()
    with patch("sys.stdout", captured_stdout):
        exit_code = await _query(query="equality", top_k=5)

    assert exit_code == 0
    raw_output = captured_stdout.getvalue().strip()
    assert raw_output == "[]"
