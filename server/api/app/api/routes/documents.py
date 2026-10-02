"""Documents API — upload, list, detail, chunks, jobs, and reprocess endpoints (G03).

Authentication:
  - Upload / Reprocess: admin only  (require_admin)
  - Read endpoints:     any authenticated user  (get_current_user)
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.ingestion.pipeline import IngestionError, run_pipeline
from app.models import User
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.enums import DocumentStatus, DocumentType
from app.models.processing_job import ProcessingJob
from app.schemas.documents import (
    ChunkSchema,
    DocumentDetail,
    DocumentSummary,
    DocumentUploadResponse,
    PaginatedChunks,
    PaginatedDocuments,
    ProcessingJobSchema,
    ReprocessResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


# ── Upload ─────────────────────────────────────────────────────────────────────


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a legal PDF for ingestion",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Query(..., description="Human-readable title for the document"),
    doc_type: str = Query(
        "OTHER",
        alias="type",
        description="DocumentType enum value",
    ),
    source: str = Query("upload", description="Source identifier"),
    source_url: str | None = Query(None, description="Canonical URL of the source"),
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> DocumentUploadResponse:
    """Accept a PDF upload, register it, and kick off background ingestion."""

    # Validate file content type (loose check — validation does the real check)
    if file.content_type not in ("application/pdf", "application/octet-stream", None):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are accepted",
        )

    pdf_bytes = await file.read()

    if len(pdf_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_upload_bytes // (1024 * 1024)} MB limit",
        )

    if len(pdf_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    # Validate doc_type
    try:
        document_type = DocumentType[doc_type.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid document type: {doc_type!r}. "
                f"Valid values: {[e.name for e in DocumentType]}"
            ),
        ) from None

    # Idempotency: check if same file_hash already exists
    import hashlib

    file_hash = hashlib.sha256(pdf_bytes).hexdigest()
    existing_result = await session.execute(
        select(Document).where(Document.file_hash == file_hash)
    )
    existing = existing_result.scalar_one_or_none()

    if existing is not None:
        return DocumentUploadResponse(
            document_id=existing.id,
            message="Document with this content already exists",
            status=existing.status.value,
            duplicate=True,
        )

    # Register new document
    doc = Document(
        title=title,
        type=document_type,
        source=source,
        source_url=source_url,
        status=DocumentStatus.REGISTERED,
    )
    session.add(doc)
    await session.flush()
    document_id = doc.id
    await session.commit()

    # Run pipeline in background
    async def _run_bg() -> None:
        from app.db.session import session_factory

        async with session_factory() as bg_session:
            try:
                await run_pipeline(
                    document_id=document_id,
                    pdf_bytes=pdf_bytes,
                    db=bg_session,
                    settings=settings,
                )
            except IngestionError as exc:
                logger.error("Ingestion failed for %s at stage %s: %s", document_id, exc.stage, exc)
            except Exception as exc:  # noqa: BLE001
                logger.error("Unexpected error ingesting %s: %s", document_id, exc)

    background_tasks.add_task(_run_bg)

    return DocumentUploadResponse(
        document_id=document_id,
        message="Document accepted for processing",
        status=DocumentStatus.PROCESSING.value,
        duplicate=False,
    )


# ── List ───────────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=PaginatedDocuments,
    summary="List registered legal documents",
)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PaginatedDocuments:
    """Return a paginated list of registered documents."""
    query = select(Document)
    count_query = select(func.count()).select_from(Document)

    if status_filter:
        try:
            ds = DocumentStatus[status_filter.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status_filter!r}",
            ) from None
        query = query.where(Document.status == ds)
        count_query = count_query.where(Document.status == ds)

    total = (await session.execute(count_query)).scalar_one()
    offset = (page - 1) * page_size
    docs = (
        await session.execute(
            query.order_by(Document.created_at.desc()).offset(offset).limit(page_size)
        )
    ).scalars().all()

    return PaginatedDocuments(
        items=[DocumentSummary.model_validate(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Detail ─────────────────────────────────────────────────────────────────────


@router.get(
    "/{document_id}",
    response_model=DocumentDetail,
    summary="Get document details",
)
async def get_document(
    document_id: UUID,
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DocumentDetail:
    doc = await session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentDetail.model_validate(doc)


# ── Chunks ─────────────────────────────────────────────────────────────────────


@router.get(
    "/{document_id}/chunks",
    response_model=PaginatedChunks,
    summary="List chunks for a document",
)
async def get_chunks(
    document_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PaginatedChunks:
    # Ensure document exists
    doc = await session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    count_q = select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id)
    total = (await session.execute(count_q)).scalar_one()

    offset = (page - 1) * page_size
    chunk_rows = (
        await session.execute(
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
            .offset(offset)
            .limit(page_size)
        )
    ).scalars().all()

    return PaginatedChunks(
        items=[ChunkSchema.model_validate(ch) for ch in chunk_rows],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Processing Jobs ────────────────────────────────────────────────────────────


@router.get(
    "/{document_id}/jobs",
    response_model=list[ProcessingJobSchema],
    summary="List processing jobs for a document",
)
async def get_jobs(
    document_id: UUID,
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ProcessingJobSchema]:
    doc = await session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    jobs = (
        await session.execute(
            select(ProcessingJob)
            .where(ProcessingJob.document_id == document_id)
            .order_by(ProcessingJob.created_at)
        )
    ).scalars().all()

    return [ProcessingJobSchema.model_validate(j) for j in jobs]


# ── Reprocess ──────────────────────────────────────────────────────────────────


@router.post(
    "/{document_id}/reprocess",
    response_model=ReprocessResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Reprocess a document (admin only)",
)
async def reprocess_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ReprocessResponse:
    """Re-run the full ingestion pipeline using the already-stored raw PDF."""
    doc = await session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if not doc.file_path:
        raise HTTPException(
            status_code=400,
            detail="No raw PDF on disk — upload the file first",
        )

    from app.core.config import get_data_dir
    from app.ingestion.persister import delete_document_files

    data_dir = get_data_dir()
    raw_path = data_dir / "raw" / str(document_id) / "original.pdf"

    if not raw_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Raw PDF file not found on disk",
        )

    pdf_bytes = raw_path.read_bytes()
    doc_id = doc.id

    async def _run_bg() -> None:
        from app.db.session import session_factory

        async with session_factory() as bg_session:
            # Clean FS artefacts except raw PDF
            delete_document_files(data_dir, doc_id)
            # Restore raw PDF
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(pdf_bytes)
            try:
                await run_pipeline(
                    document_id=doc_id,
                    pdf_bytes=pdf_bytes,
                    db=bg_session,
                    settings=settings,
                )
            except IngestionError as exc:
                logger.error("Reprocess failed for %s at %s: %s", doc_id, exc.stage, exc)
            except Exception as exc:  # noqa: BLE001
                logger.error("Reprocess error for %s: %s", doc_id, exc)

    background_tasks.add_task(_run_bg)
    return ReprocessResponse(document_id=doc_id)
