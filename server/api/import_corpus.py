import asyncio
from datetime import datetime, date
import json
import logging
from pathlib import Path
import sys
from uuid import UUID

from sqlalchemy import select

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.config import get_data_dir
from app.db.session import session_factory
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.chunk import Chunk
from app.models.enums import DocumentStatus, DocumentType
from app.ingestion.corpus_pipeline import document_id_to_uuid

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("import_corpus")


def _clean_str(val: str | None) -> str | None:
    if val is None:
        return None
    return val.replace("\x00", "")


def _clean_dict(val: dict | None) -> dict:
    if not val:
        return {}
    cleaned = {}
    for k, v in val.items():
        k_clean = k.replace("\x00", "") if isinstance(k, str) else k
        if isinstance(v, str):
            cleaned[k_clean] = v.replace("\x00", "")
        elif isinstance(v, dict):
            cleaned[k_clean] = _clean_dict(v)
        else:
            cleaned[k_clean] = v
    return cleaned


async def import_corpus() -> dict[str, int]:
    data_dir = get_data_dir()
    corpus_root = data_dir / "legal_corpus_v1"
    metadata_file = corpus_root / "metadata" / "documents.json"
    versions_file = corpus_root / "metadata" / "versions.json"
    chunks_dir = corpus_root / "processed" / "chunks"

    if not metadata_file.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_file}")

    with open(metadata_file, "r", encoding="utf-8") as f:
        docs_meta = json.load(f)["documents"]

    versions_meta = {}
    if versions_file.exists():
        with open(versions_file, "r", encoding="utf-8") as f:
            versions_meta = json.load(f)["versions"]

    imported_docs = 0
    updated_docs = 0
    imported_versions = 0
    imported_chunks = 0

    async with session_factory() as session:
        for doc_key, item in docs_meta.items():
            doc_uuid = UUID(item["uuid"]) if "uuid" in item else document_id_to_uuid(doc_key)

            doc_stmt = select(Document).where(Document.id == doc_uuid)
            document = await session.scalar(doc_stmt)

            doc_type_str = item.get("document_type", "other").lower()
            try:
                doc_type = DocumentType(doc_type_str)
            except ValueError:
                doc_type = DocumentType.OTHER

            # Process chunks
            chunk_file = chunks_dir / f"{doc_key}.json"
            has_chunks = chunk_file.exists()
            target_status = DocumentStatus.READY if has_chunks else DocumentStatus.REGISTERED

            if document is None:
                document = Document(
                    id=doc_uuid,
                    title=_clean_str(item.get("title", doc_key)) or doc_key,
                    type=doc_type,
                    source=_clean_str(item.get("issuing_authority")) or "Legal Corpus",
                    source_url=_clean_str(item.get("citation")),
                    file_hash=_clean_str(item.get("checksum")),
                    file_path=_clean_str(item.get("source_file") or item.get("source_path")),
                    status=target_status,
                )
                session.add(document)
                await session.flush()
                imported_docs += 1
                logger.info("Imported document: %s (%s, status=%s)", document.title, document.id, target_status.value)
            else:
                if document.status != target_status:
                    document.status = target_status
                    await session.flush()
                    updated_docs += 1
                    logger.info("Updated status to %s for document: %s (%s)", target_status.value, document.title, document.id)

            # DocumentVersion
            ver_info = versions_meta.get(doc_key, {})
            ver_str = str(ver_info.get("version", "1.0"))
            eff_from_str = ver_info.get("effective_from")
            eff_from = None
            if eff_from_str:
                try:
                    eff_from = datetime.strptime(eff_from_str, "%Y-%m-%d").date()
                except ValueError:
                    eff_from = date(1970, 1, 1)
            if eff_from is None:
                eff_from = date(1970, 1, 1)

            ver_stmt = select(DocumentVersion).where(
                DocumentVersion.document_id == document.id,
                DocumentVersion.version == ver_str,
            )
            version_obj = await session.scalar(ver_stmt)

            if version_obj is None:
                version_obj = DocumentVersion(
                    id=document_id_to_uuid(f"{doc_key}:version:{ver_str}"),
                    document_id=document.id,
                    version=ver_str,
                    effective_from=eff_from,
                    effective_to=None,
                )
                session.add(version_obj)
                await session.flush()
                imported_versions += 1

            if not has_chunks:
                logger.warning("No chunk file found for doc: %s at %s", doc_key, chunk_file)
                continue


            with open(chunk_file, "r", encoding="utf-8") as f:
                chunks_data = json.load(f)

            existing_indices_stmt = select(Chunk.chunk_index).where(Chunk.document_id == document.id)
            existing_indices = set((await session.execute(existing_indices_stmt)).scalars().all())

            doc_chunk_count = 0
            for c in chunks_data:
                chunk_index = c["chunk_index"]
                if chunk_index in existing_indices:
                    continue

                chunk_id_str = c.get("chunk_id")
                chunk_uuid = UUID(chunk_id_str) if chunk_id_str else document_id_to_uuid(f"{doc_key}:chunk:{chunk_index}")

                chunk_obj = Chunk(
                    id=chunk_uuid,
                    document_id=document.id,
                    document_version_id=version_obj.id,
                    chunk_index=chunk_index,
                    text=_clean_str(c["text"]) or "",
                    char_count=c["char_count"],
                    page_start=c.get("page_start"),
                    page_end=c.get("page_end"),
                    hierarchy=_clean_dict(c.get("hierarchy")),
                    citation_ref=_clean_str(c.get("citation_ref")),
                )
                session.add(chunk_obj)
                imported_chunks += 1
                doc_chunk_count += 1

            if doc_chunk_count > 0:
                logger.info("Added %d chunks for document %s", doc_chunk_count, doc_key)

        await session.commit()


    stats = {
        "documents_imported": imported_docs,
        "documents_updated": updated_docs,
        "versions_imported": imported_versions,
        "chunks_imported": imported_chunks,
    }
    logger.info("Import completed successfully: %s", json.dumps(stats))
    return stats


async def main() -> None:
    stats = await import_corpus()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
