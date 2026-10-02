"""Audit Log API Routes (Phase 16).

Provides read-only, paginated access to persistent operational and security audit logs.
Audit records are append-only.
"""

from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.db.session import get_session
from app.models import SystemEvent, User
from app.schemas.audit import AuditEventResponse, PaginatedAuditResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=PaginatedAuditResponse)
async def list_audit_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = Query(None, description="Filter by category (e.g., AUTHENTICATION, USER_MANAGEMENT, VALIDATION, SETTINGS)"),
    result: str | None = Query(None, description="Filter by result: SUCCESS, FAILURE, WARNING"),
    severity: str | None = Query(None, description="Filter by severity: INFO, WARNING, ERROR"),
    actor_id: UUID | None = Query(None, description="Filter by actor user ID"),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> PaginatedAuditResponse:
    """List system audit log events with filtering and pagination."""
    query = select(SystemEvent).options(selectinload(SystemEvent.actor))
    count_query = select(func.count(SystemEvent.id))

    filters = []
    if category:
        c = f"{category.upper()}_%"
        filters.append(SystemEvent.event_type.like(c))
    if actor_id:
        filters.append(SystemEvent.actor_id == actor_id)

    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    total = await session.scalar(count_query) or 0
    offset = (page - 1) * page_size
    events = (await session.scalars(query.order_by(SystemEvent.created_at.desc()).offset(offset).limit(page_size))).all()

    items = []
    for e in events:
        resp = AuditEventResponse(
            id=e.id,
            event_type=e.event_type,
            actor_id=e.actor_id,
            actor_email=e.actor.email if e.actor else None,
            event_metadata=e.event_metadata,
            created_at=e.created_at,
        )
        items.append(resp)

    return PaginatedAuditResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{event_id}", response_model=AuditEventResponse)
async def get_audit_event(
    event_id: UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> AuditEventResponse:
    """Retrieve details for a specific audit log event."""
    query = select(SystemEvent).where(SystemEvent.id == event_id).options(selectinload(SystemEvent.actor))
    e = await session.scalar(query)
    if not e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit event not found")

    return AuditEventResponse(
        id=e.id,
        event_type=e.event_type,
        actor_id=e.actor_id,
        actor_email=e.actor.email if e.actor else None,
        event_metadata=e.event_metadata,
        created_at=e.created_at,
    )
