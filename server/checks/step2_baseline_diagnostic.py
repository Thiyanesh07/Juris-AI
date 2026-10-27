import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import select, func, text
from app.core.config import get_data_dir, get_settings
from app.db.session import engine, session_factory
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.document_version import DocumentVersion
from app.models.enums import DocumentStatus


async def run_diagnostics():
    print("=" * 60)
    print("STEP 2 BASELINE DIAGNOSTICS")
    print("=" * 60)

    # 1. PostgreSQL connection & Alembic migration status
    try:
        async with engine.connect() as conn:
            pg_version = await conn.scalar(text("SELECT version();"))
            print(f"1. PostgreSQL Connection: SUCCESS")
            print(f"   Database Engine: {pg_version.split(',')[0]}")

            def get_alembic_heads(sync_conn):
                context = MigrationContext.configure(sync_conn)
                current_rev = context.get_current_revision()
                alembic_cfg = Config("alembic.ini")
                script = ScriptDirectory.from_config(alembic_cfg)
                heads = script.get_heads()
                return current_rev, heads

            current_rev, heads = await conn.run_sync(get_alembic_heads)
            print(f"   Alembic Current Revision: {current_rev}")
            print(f"   Alembic Head Revision(s): {heads}")
            print(f"   Schema Up-To-Date: {current_rev in heads}")
    except Exception as e:
        print(f"1. PostgreSQL Connection: FAILED ({e})")
        return

    # 2. Document counts grouped by status
    async with session_factory() as s:
        status_stmt = select(Document.status, func.count(Document.id)).group_by(Document.status)
        status_rows = (await s.execute(status_stmt)).all()
        doc_total = sum(c for _, c in status_rows)
        print(f"\n2. Document Counts Grouped by Status (Total: {doc_total}):")
        for st, cnt in sorted(status_rows, key=lambda x: str(x[0])):
            print(f"   - {st.value if hasattr(st, 'value') else st}: {cnt}")

        # 3. Chunk counts and document references in PostgreSQL
        chunk_total = await s.scalar(select(func.count(Chunk.id)))
        chunk_doc_distinct = await s.scalar(select(func.count(func.distinct(Chunk.document_id))))
        orphan_chunks = await s.scalar(
            select(func.count(Chunk.id)).where(~Chunk.document_id.in_(select(Document.id)))
        )
        print(f"\n3. PostgreSQL Chunk Counts:")
        print(f"   - Total Chunks: {chunk_total}")
        print(f"   - Distinct Document IDs referenced: {chunk_doc_distinct}")
        print(f"   - Orphan Chunks (no parent doc): {orphan_chunks}")

        # Fetch all PG doc IDs and chunk IDs
        pg_docs = (await s.execute(select(Document.id, Document.title, Document.status))).all()
        pg_doc_map = {str(d.id): {"title": d.title, "status": d.status} for d in pg_docs}
        pg_chunk_rows = (await s.execute(select(Chunk.id, Chunk.document_id))).all()
        pg_chunk_map = {str(c.id): str(c.document_id) for c in pg_chunk_rows}

    # 4. FAISS index vector count and metadata count
    settings = get_settings()
    data_dir = get_data_dir()
    index_dir = data_dir / "indexes" / settings.vector_index_name
    print(f"\n4. FAISS Index Directory: {index_dir}")
    meta_path = index_dir / "metadata.json"
    index_path = index_dir / "index.faiss"
    emb_path = index_dir / "embeddings.npy"

    if not index_path.exists() or not meta_path.exists():
        print("   FAISS index files missing!")
        return

    import faiss
    import numpy as np

    index = faiss.read_index(str(index_path))
    faiss_ntotal = index.ntotal
    meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
    meta_chunks = meta_data.get("chunks", [])
    meta_chunk_ids = meta_data.get("chunk_ids", [])
    emb_shape = np.load(str(emb_path)).shape if emb_path.exists() else None

    print(f"   - Index vector count (ntotal): {faiss_ntotal}")
    print(f"   - Embeddings matrix shape: {emb_shape}")
    print(f"   - Metadata chunk records: {len(meta_chunks)}")
    print(f"   - Metadata chunk_ids list: {len(meta_chunk_ids)}")

    # 5. Matching Document IDs
    faiss_doc_ids = set()
    malformed_faiss_doc_ids = set()
    for ch in meta_chunks:
        doc_id_val = ch.get("document_id")
        try:
            UUID(str(doc_id_val))
            faiss_doc_ids.add(str(doc_id_val))
        except (ValueError, TypeError):
            malformed_faiss_doc_ids.add(str(doc_id_val))

    matching_doc_ids = faiss_doc_ids.intersection(set(pg_doc_map.keys()))
    print(f"\n5. FAISS Metadata Document IDs:")
    print(f"   - Unique document IDs in FAISS: {len(faiss_doc_ids)}")
    print(f"   - Malformed (non-UUID) document IDs: {len(malformed_faiss_doc_ids)} ({list(malformed_faiss_doc_ids)[:5]})")
    print(f"   - Matching PG Document IDs: {len(matching_doc_ids)}")
    print(f"   - FAISS Doc IDs NOT in PG: {len(faiss_doc_ids - set(pg_doc_map.keys()))}")

    # 6. Matching Chunk IDs
    faiss_chunk_ids = set()
    malformed_faiss_chunk_ids = set()
    for ch in meta_chunks:
        chunk_id_val = ch.get("chunk_id")
        try:
            UUID(str(chunk_id_val))
            faiss_chunk_ids.add(str(chunk_id_val))
        except (ValueError, TypeError):
            malformed_faiss_chunk_ids.add(str(chunk_id_val))

    matching_chunk_ids = faiss_chunk_ids.intersection(set(pg_chunk_map.keys()))
    print(f"\n6. FAISS Metadata Chunk IDs:")
    print(f"   - Unique chunk IDs in FAISS: {len(faiss_chunk_ids)}")
    print(f"   - Malformed chunk IDs: {len(malformed_faiss_chunk_ids)}")
    print(f"   - Matching PG Chunk IDs: {len(matching_chunk_ids)}")
    print(f"   - FAISS Chunk IDs NOT in PG: {len(faiss_chunk_ids - set(pg_chunk_map.keys()))}")

    # 7. Check if matching IDs refer to documents in READY status
    ready_pg_doc_ids = {did for did, d in pg_doc_map.items() if d["status"] == DocumentStatus.READY}
    matching_ready_docs = matching_doc_ids.intersection(ready_pg_doc_ids)
    print(f"\n7. Matching Document Status Check:")
    print(f"   - Total READY Documents in PG: {len(ready_pg_doc_ids)}")
    print(f"   - Matching FAISS Documents with READY status: {len(matching_ready_docs)}")

    # 8. Check for duplicates, orphaned, or malformed
    print(f"\n8. Duplicate & Consistency Checks:")
    print(f"   - Duplicate chunk IDs in FAISS chunk_ids: {len(meta_chunk_ids) - len(set(meta_chunk_ids))}")
    print(f"   - Chunk IDs in FAISS chunks != chunk_ids: {[c['chunk_id'] for c in meta_chunks] != meta_chunk_ids}")

    # Sample comparison between FAISS and PG
    print(f"\nSample Inspection:")
    sample_faiss_ch = meta_chunks[0] if meta_chunks else {}
    print(f"   FAISS Sample Chunk [0]:")
    print(f"     chunk_id: {sample_faiss_ch.get('chunk_id')}")
    print(f"     document_id: {sample_faiss_ch.get('document_id')}")
    print(f"     document_title: {sample_faiss_ch.get('document_title')}")
    print(f"     chunk_index: {sample_faiss_ch.get('chunk_index')}")

    sample_pg_chunk = list(pg_chunk_map.items())[0] if pg_chunk_map else None
    if sample_pg_chunk:
        pg_cid, pg_did = sample_pg_chunk
        print(f"   PG Sample Chunk [0]:")
        print(f"     chunk_id: {pg_cid}")
        print(f"     document_id: {pg_did} ({pg_doc_map.get(pg_did, {}).get('title')})")


if __name__ == "__main__":
    asyncio.run(run_diagnostics())
