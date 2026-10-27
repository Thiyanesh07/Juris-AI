import asyncio
import sys
from sqlalchemy import select, func, text

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.db.session import session_factory
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.chunk import Chunk
from app.models.enums import DocumentStatus


async def verify():
    async with session_factory() as s:
        doc_count = await s.scalar(select(func.count(Document.id)))
        ready_count = await s.scalar(select(func.count(Document.id)).where(Document.status == DocumentStatus.READY))
        version_count = await s.scalar(select(func.count(DocumentVersion.id)))
        chunk_count = await s.scalar(select(func.count(Chunk.id)))

        # Check for orphan chunks (document_id not in documents)
        orphan_doc_chunks = await s.scalar(
            select(func.count(Chunk.id)).where(
                ~Chunk.document_id.in_(select(Document.id))
            )
        )

        # Check for duplicate chunks (same document_id and chunk_index)
        dup_chunks_query = text(
            "SELECT COUNT(*) FROM (SELECT document_id, chunk_index FROM chunks GROUP BY document_id, chunk_index HAVING COUNT(*) > 1) d"
        )
        dup_res = await s.execute(dup_chunks_query)
        dup_chunks = dup_res.scalar()

        print(f"PostgreSQL Verification Summary:")
        print(f"  Total Documents: {doc_count}")
        print(f"  READY Documents: {ready_count}")
        print(f"  Total Versions:  {version_count}")
        print(f"  Total Chunks:    {chunk_count}")
        print(f"  Orphan Chunks:   {orphan_doc_chunks}")
        print(f"  Duplicate Chunks:{dup_chunks}")

if __name__ == "__main__":
    asyncio.run(verify())
