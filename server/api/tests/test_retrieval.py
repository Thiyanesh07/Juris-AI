"""Unit tests for FAISS artefacts and retrieval mapping; no model download."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models import Document
from app.models.chunk import Chunk
from app.models.enums import DocumentType, ProcessingJobStage, ProcessingJobStatus
from app.models.processing_job import ProcessingJob
from app.retrieval.index import IndexError, load_index, save_index
from app.retrieval.service import build_embedder, rebuild_index, retrieve
from app.schemas.retrieval import RetrievalResponse

TEST_MODEL = "test-embedding-model"
TEST_POOLING = "attention_mask_mean_pooling"


class FakeEmbedder:
    pooling_method = TEST_POOLING
    normalization = "l2"

    def embed(self, texts: list[str]) -> np.ndarray:
        mapping = {"equality": [1.0, 0.0], "life": [0.0, 1.0]}
        return np.asarray([mapping.get(text, [0.5, 0.5]) for text in texts], dtype=np.float32)


def _configure_settings(settings: Settings, tmp_path: Path, *, index_name: str = "test") -> None:
    object.__setattr__(settings, "data_dir", str(tmp_path))
    object.__setattr__(settings, "vector_index_name", index_name)
    object.__setattr__(settings, "embedding_model_name", TEST_MODEL)


def _records() -> list[dict[str, object]]:
    return [
        {
            "chunk_id": "00000000-0000-0000-0000-000000000001",
            "document_id": "00000000-0000-0000-0000-000000000010",
            "document_version_id": None,
            "chunk_index": 0,
            "text": "equality",
            "page_start": 1,
            "page_end": 1,
            "hierarchy": {"provision": "Article 14"},
            "citation_ref": "Article 14",
            "source_url": None,
            "document_title": "Constitution",
        },
        {
            "chunk_id": "00000000-0000-0000-0000-000000000002",
            "document_id": "00000000-0000-0000-0000-000000000010",
            "document_version_id": None,
            "chunk_index": 1,
            "text": "life",
            "page_start": 2,
            "page_end": 2,
            "hierarchy": {"provision": "Article 21"},
            "citation_ref": "Article 21",
            "source_url": None,
            "document_title": "Constitution",
        },
    ]


def _save_test_index(tmp_path: Path, *, index_name: str = "test") -> None:
    save_index(
        data_dir=tmp_path,
        index_name=index_name,
        vectors=np.eye(2, dtype=np.float32),
        chunk_records=_records(),
        model_name=TEST_MODEL,
        pooling_method=TEST_POOLING,
        max_tokens=32,
    )


def test_faiss_artifact_round_trip_and_mapping(tmp_path: Path) -> None:
    _save_test_index(tmp_path)
    index, metadata = load_index(tmp_path, "test")
    assert index.ntotal == 2
    assert metadata["chunk_ids"][0].endswith("1")
    assert (tmp_path / "indexes" / "test" / "embeddings.npy").is_file()


def test_retrieval_returns_ranked_evidence(tmp_path: Path) -> None:
    settings = get_settings()
    _configure_settings(settings, tmp_path)
    _save_test_index(tmp_path)
    results = retrieve("equality", 2, settings, embedder=FakeEmbedder())
    assert [result["rank"] for result in results] == [1, 2]
    assert results[0]["hierarchy"]["provision"] == "Article 14"
    assert results[0]["score"] == pytest.approx(1.0)
    assert results[0]["chunk_index"] == 0


def test_retrieval_response_accepts_service_payload(tmp_path: Path) -> None:
    settings = get_settings()
    _configure_settings(settings, tmp_path)
    _save_test_index(tmp_path)
    results = retrieve("equality", 2, settings, embedder=FakeEmbedder())
    response = RetrievalResponse(query="equality", results=results)
    assert response.results[0].chunk_index == 0


def test_missing_index_and_invalid_top_k_are_explicit(tmp_path: Path) -> None:
    settings = get_settings()
    _configure_settings(settings, tmp_path)
    with pytest.raises(IndexError):
        load_index(tmp_path, "missing")
    with pytest.raises(ValueError):
        retrieve("equality", 0, settings, embedder=FakeEmbedder())
    with pytest.raises(ValueError, match="top_k"):
        retrieve("equality", settings.retrieval_max_top_k + 1, settings, embedder=FakeEmbedder())


def test_load_rejects_duplicate_or_stale_chunk_mapping(tmp_path: Path) -> None:
    _save_test_index(tmp_path)
    metadata_path = tmp_path / "indexes" / "test" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["chunk_ids"][1] = metadata["chunk_ids"][0]
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(IndexError, match="duplicate|mapping"):
        load_index(tmp_path, "test")


def test_load_rejects_corrupt_faiss_file(tmp_path: Path) -> None:
    _save_test_index(tmp_path)
    (tmp_path / "indexes" / "test" / "index.faiss").write_bytes(b"not-a-faiss-index")
    with pytest.raises(IndexError, match="corrupted"):
        load_index(tmp_path, "test")


def test_load_rejects_metadata_dimension_mismatch(tmp_path: Path) -> None:
    _save_test_index(tmp_path)
    metadata_path = tmp_path / "indexes" / "test" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["embedding_dimension"] = 999
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(IndexError, match="dimension"):
        load_index(tmp_path, "test")


def test_load_rejects_missing_chunk_evidence_fields(tmp_path: Path) -> None:
    _save_test_index(tmp_path)
    metadata_path = tmp_path / "indexes" / "test" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    del metadata["chunks"][0]["document_title"]
    del metadata["chunks"][0]["document_id"]
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(IndexError, match="missing required chunk fields"):
        load_index(tmp_path, "test")


def test_retrieve_rejects_query_dimension_mismatch(tmp_path: Path) -> None:
    settings = get_settings()
    _configure_settings(settings, tmp_path)
    _save_test_index(tmp_path)

    class WideEmbedder(FakeEmbedder):
        def embed(self, texts: list[str]) -> np.ndarray:
            return np.ones((len(texts), 4), dtype=np.float32)

    with pytest.raises(IndexError, match="dimension"):
        retrieve("equality", 1, settings, embedder=WideEmbedder())


def test_retrieve_rejects_embedder_model_mismatch(tmp_path: Path) -> None:
    settings = get_settings()
    _configure_settings(settings, tmp_path)
    _save_test_index(tmp_path)
    object.__setattr__(settings, "embedding_model_name", "other-model")
    with pytest.raises(IndexError, match="embedding model"):
        retrieve("equality", 1, settings, embedder=FakeEmbedder())


def test_retrieve_rejects_embedder_pooling_mismatch(tmp_path: Path) -> None:
    settings = get_settings()
    _configure_settings(settings, tmp_path)
    _save_test_index(tmp_path)

    class WrongPoolEmbedder(FakeEmbedder):
        pooling_method = "cls_pooling"

    with pytest.raises(IndexError, match="pooling"):
        retrieve("equality", 1, settings, embedder=WrongPoolEmbedder())


def test_build_embedder_reuses_cached_instance() -> None:
    from app.retrieval.service import _cached_embedder

    _cached_embedder.cache_clear()
    settings = get_settings()
    first = build_embedder(settings)
    second = build_embedder(settings)
    assert first is second


async def test_rebuild_index_empty_corpus_raises(session: AsyncSession, tmp_path: Path) -> None:
    settings = get_settings()
    _configure_settings(settings, tmp_path)
    with pytest.raises(IndexError, match="no chunks"):
        await rebuild_index(session, settings, embedder=FakeEmbedder())


async def test_rebuild_index_orders_rows_and_marks_jobs_completed(
    session: AsyncSession, tmp_path: Path
) -> None:
    settings = get_settings()
    _configure_settings(settings, tmp_path)
    doc = Document(title="Constitution", type=DocumentType.CONSTITUTION, source="test")
    session.add(doc)
    await session.flush()
    session.add_all(
        [
            Chunk(
                document_id=doc.id,
                chunk_index=1,
                text="life",
                char_count=4,
                hierarchy={"provision": "Article 21"},
                citation_ref="Article 21",
            ),
            Chunk(
                document_id=doc.id,
                chunk_index=0,
                text="equality",
                char_count=8,
                hierarchy={"provision": "Article 14"},
                citation_ref="Article 14",
            ),
        ]
    )
    await session.commit()

    summary = await rebuild_index(session, settings, embedder=FakeEmbedder())
    assert summary["chunk_count"] == 2
    assert summary["dimension"] == 2

    jobs = (
        await session.execute(select(ProcessingJob).where(ProcessingJob.document_id == doc.id))
    ).scalars().all()
    assert len(jobs) == 2
    assert all(job.status is ProcessingJobStatus.COMPLETED for job in jobs)
    assert {job.stage for job in jobs} == {
        ProcessingJobStage.EMBEDDING,
        ProcessingJobStage.VECTOR_INDEX,
    }

    hits = retrieve("equality", 2, settings, embedder=FakeEmbedder())
    assert hits[0]["citation_ref"] == "Article 14"
    assert hits[0]["chunk_index"] == 0
