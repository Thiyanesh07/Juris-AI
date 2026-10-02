"""Reproducible filesystem persistence for the Phase 1 FAISS index."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.retrieval.embeddings import EmbeddingError


class IndexError(RuntimeError):
    """The vector index is absent, stale, or unusable."""


def index_directory(data_dir: Path, index_name: str) -> Path:
    return data_dir / "indexes" / index_name


def save_index(
    *,
    data_dir: Path,
    index_name: str,
    vectors: Any,
    chunk_records: list[dict[str, Any]],
    model_name: str,
    pooling_method: str,
    max_tokens: int,
) -> Path:
    """Build and atomically persist an ``IndexFlatIP`` plus its row mapping."""
    try:
        import faiss
        import numpy as np
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise EmbeddingError("FAISS and NumPy are required; run `uv sync`.") from exc
    matrix = np.asarray(vectors, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[0] != len(chunk_records) or matrix.shape[0] == 0:
        raise IndexError("Index vectors and chunk mapping must be non-empty and have matching rows")
    if not np.isfinite(matrix).all():
        raise IndexError("Embedding matrix contains non-finite values")
    directory = index_directory(data_dir, index_name)
    directory.mkdir(parents=True, exist_ok=True)
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    metadata = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "index_type": "IndexFlatIP",
        "metric": "inner_product_cosine_on_l2_normalized_vectors",
        "embedding_model": model_name,
        "embedding_dimension": int(matrix.shape[1]),
        "pooling_method": pooling_method,
        "normalization": "l2",
        "max_tokens": max_tokens,
        "chunk_ids": [record["chunk_id"] for record in chunk_records],
        "chunks": chunk_records,
    }
    with tempfile.NamedTemporaryFile(dir=directory, suffix=".faiss", delete=False) as tmp:
        tmp_index = Path(tmp.name)
    with tempfile.NamedTemporaryFile(dir=directory, suffix=".npy", delete=False) as tmp:
        tmp_vectors = Path(tmp.name)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=directory, suffix=".json", delete=False
    ) as tmp:
        json.dump(metadata, tmp, ensure_ascii=False, indent=2)
        tmp_metadata = Path(tmp.name)
    faiss.write_index(index, str(tmp_index))
    np.save(str(tmp_vectors), matrix)
    tmp_index.replace(directory / "index.faiss")
    tmp_vectors.replace(directory / "embeddings.npy")
    tmp_metadata.replace(directory / "metadata.json")
    return directory


_REQUIRED_CHUNK_FIELDS = (
    "chunk_id",
    "document_id",
    "document_title",
    "text",
    "chunk_index",
    "hierarchy",
)


def _validate_mapping(metadata: dict[str, Any], vector_count: int) -> None:
    """Reject incomplete, duplicate, malformed, or stale row mappings."""
    chunk_ids = metadata.get("chunk_ids")
    chunks = metadata.get("chunks")
    if not isinstance(chunk_ids, list) or not isinstance(chunks, list):
        raise IndexError("Vector index metadata has no valid chunk mapping")
    if vector_count != len(chunk_ids) or vector_count != len(chunks):
        raise IndexError("Vector index and chunk metadata are out of sync")
    if len(set(chunk_ids)) != len(chunk_ids):
        raise IndexError("Vector index metadata contains duplicate chunk IDs")
    record_ids: list[str] = []
    for record in chunks:
        if not isinstance(record, dict) or not isinstance(record.get("chunk_id"), str):
            raise IndexError("Vector index metadata contains a missing chunk ID")
        try:
            UUID(record["chunk_id"])
        except ValueError as exc:
            raise IndexError("Vector index metadata contains an invalid chunk ID") from exc
        missing = [field for field in _REQUIRED_CHUNK_FIELDS if field not in record]
        if missing:
            raise IndexError("Vector index metadata is missing required chunk fields")
        if not isinstance(record.get("document_id"), str):
            raise IndexError("Vector index metadata contains an invalid document ID")
        try:
            UUID(record["document_id"])
        except ValueError as exc:
            raise IndexError("Vector index metadata contains an invalid document ID") from exc
        title = record.get("document_title")
        if not isinstance(title, str) or not title.strip():
            raise IndexError("Vector index metadata is missing required chunk fields")
        if not isinstance(record.get("text"), str) or not record["text"].strip():
            raise IndexError("Vector index metadata is missing required chunk fields")
        if not isinstance(record.get("chunk_index"), int):
            raise IndexError("Vector index metadata is missing required chunk fields")
        if not isinstance(record.get("hierarchy"), dict):
            raise IndexError("Vector index metadata is missing required chunk fields")
        record_ids.append(record["chunk_id"])
    if chunk_ids != record_ids:
        raise IndexError("Vector index row mapping does not match chunk metadata")


def load_index(data_dir: Path, index_name: str) -> tuple[Any, dict[str, Any]]:
    try:
        import faiss
    except ImportError as exc:  # pragma: no cover
        raise EmbeddingError("FAISS is required; run `uv sync`.") from exc
    directory = index_directory(data_dir, index_name)
    index_path, metadata_path = directory / "index.faiss", directory / "metadata.json"
    if not index_path.is_file() or not metadata_path.is_file():
        raise IndexError("No vector index is available. An administrator must rebuild it.")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        index = faiss.read_index(str(index_path))
    except Exception as exc:
        raise IndexError("Vector index artifacts are corrupted") from exc
    if metadata.get("index_type") != "IndexFlatIP":
        raise IndexError("Unsupported or incomplete vector index metadata")
    _validate_mapping(metadata, index.ntotal)
    if index.d != metadata.get("embedding_dimension"):
        raise IndexError("Vector index dimension does not match metadata")
    return index, metadata


def validate_query_embedding(query_vector: Any, index: Any) -> None:
    if query_vector.shape[1] != index.d:
        raise IndexError("Query embedding dimension does not match the loaded vector index")


def search_index_rows(
    index: Any,
    metadata: dict[str, Any],
    query_vector: Any,
    top_k: int,
) -> list[dict[str, Any]]:
    """Return FAISS hits with 1-based rank, cosine score, chunk_id, and faiss_row."""
    scores, ids = index.search(query_vector, min(top_k, index.ntotal))
    hits: list[dict[str, Any]] = []
    for rank, (score, row) in enumerate(zip(scores[0], ids[0], strict=True), start=1):
        if row < 0:
            continue
        faiss_row = int(row)
        hits.append(
            {
                "rank": rank,
                "score": float(score),
                "chunk_id": metadata["chunks"][faiss_row]["chunk_id"],
                "faiss_row": faiss_row,
            }
        )
    return hits


def load_embeddings_matrix(data_dir: Path, index_name: str) -> Any:
    """Load the persisted L2-normalized embedding matrix aligned with FAISS rows."""
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover
        raise EmbeddingError("NumPy is required; run `uv sync`.") from exc
    path = index_directory(data_dir, index_name) / "embeddings.npy"
    if not path.is_file():
        raise IndexError("Vector index embeddings matrix is missing")
    matrix = np.load(str(path))
    if matrix.ndim != 2:
        raise IndexError("Vector index embeddings matrix is invalid")
    return matrix


def chunk_id_row_map(metadata: dict[str, Any]) -> dict[str, int]:
    return {chunk_id: index for index, chunk_id in enumerate(metadata["chunk_ids"])}


def cosine_for_chunk_ids(
    query_vector: Any,
    chunk_ids: list[str],
    *,
    metadata: dict[str, Any],
    embeddings: Any,
) -> dict[str, float]:
    """Inner product cosines for chunk IDs present in the index (vectors are L2-normalized)."""
    import numpy as np

    row_by_id = chunk_id_row_map(metadata)
    query = np.asarray(query_vector, dtype=np.float32).reshape(-1)
    scores: dict[str, float] = {}
    for chunk_id in chunk_ids:
        row = row_by_id.get(chunk_id)
        if row is None:
            continue
        scores[chunk_id] = float(np.dot(query, embeddings[int(row)]))
    return scores


def validate_index_embedder_settings(
    metadata: dict[str, Any],
    *,
    model_name: str,
    pooling_method: str,
    normalization: str,
) -> None:
    """Refuse search when on-disk index settings disagree with the active embedder."""
    if metadata.get("embedding_model") != model_name:
        raise IndexError(
            "Vector index embedding model does not match the configured embedder"
        )
    if metadata.get("pooling_method") != pooling_method:
        raise IndexError(
            "Vector index pooling method does not match the configured embedder"
        )
    if metadata.get("normalization") != normalization:
        raise IndexError(
            "Vector index normalization does not match the configured embedder"
        )
