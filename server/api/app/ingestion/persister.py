"""File-system persister for ingestion pipeline outputs.

Directory layout under ``<data_dir>/``:
  raw/<document_id>/original.pdf          ← byte-for-byte copy of uploaded PDF
  processed/<document_id>/pages.jsonl     ← one JSON object per page
  processed/<document_id>/structure.json  ← document-level metadata & hierarchy summary
  chunks/<document_id>/chunks.jsonl       ← one JSON object per chunk

All writes are atomic: files are written to a temp path then renamed so that a
concurrent reader never sees a partially written file.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any
from uuid import UUID

from app.ingestion.chunker import ChunkResult
from app.ingestion.extractor import PageRecord


def _atomic_write_text(path: Path, content: str) -> None:
    """Write *content* to *path* atomically (temp → rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write *data* to *path* atomically (temp → rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    ) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def save_raw_pdf(data_dir: Path, document_id: UUID, pdf_bytes: bytes) -> Path:
    """Save the original PDF bytes and return the destination path."""
    dest = data_dir / "raw" / str(document_id) / "original.pdf"
    _atomic_write_bytes(dest, pdf_bytes)
    return dest


def save_pages(data_dir: Path, document_id: UUID, pages: list[PageRecord]) -> Path:
    """Persist page records as JSONL."""
    dest = data_dir / "processed" / str(document_id) / "pages.jsonl"
    lines: list[str] = []
    for page in pages:
        obj: dict[str, Any] = {
            "page_number": page.page_number,
            "text": page.text,
            "block_count": len(page.blocks),
        }
        lines.append(json.dumps(obj, ensure_ascii=False))
    _atomic_write_text(dest, "\n".join(lines) + "\n")
    return dest


def save_structure(
    data_dir: Path,
    document_id: UUID,
    metadata: dict[str, Any],
) -> Path:
    """Persist document-level structure metadata as JSON."""
    dest = data_dir / "processed" / str(document_id) / "structure.json"
    _atomic_write_text(dest, json.dumps(metadata, ensure_ascii=False, indent=2))
    return dest


def save_chunks(
    data_dir: Path,
    document_id: UUID,
    document_version_id: UUID | None,
    chunks: list[ChunkResult],
) -> Path:
    """Persist chunks as JSONL and return the destination path."""
    dest = data_dir / "chunks" / str(document_id) / "chunks.jsonl"
    lines: list[str] = []
    for ch in chunks:
        obj: dict[str, Any] = {
            "chunk_index": ch.chunk_index,
            "document_id": str(document_id),
            "document_version_id": str(document_version_id) if document_version_id else None,
            "page_start": ch.page_start,
            "page_end": ch.page_end,
            "hierarchy": ch.hierarchy,
            "citation_ref": ch.citation_ref,
            "char_count": ch.char_count,
            "text": ch.text,
        }
        lines.append(json.dumps(obj, ensure_ascii=False))
    _atomic_write_text(dest, "\n".join(lines) + "\n")
    return dest


def delete_document_files(data_dir: Path, document_id: UUID) -> None:
    """Remove all filesystem artefacts for *document_id* (used during reprocess)."""
    for subdir in ("raw", "processed", "chunks"):
        target = data_dir / subdir / str(document_id)
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
