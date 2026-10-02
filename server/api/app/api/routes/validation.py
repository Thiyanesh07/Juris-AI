"""Validation Queue API Routes (Phase 16).

Provides human-in-the-loop review capabilities for extracted legal entities, triples, citations,
and document metadata.
"""

from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.db.session import get_session
from app.models import User, ValidationItem
from app.schemas.validation import (
    BulkApproveRequest,
    PaginatedValidationResponse,
    ValidationItemResponse,
    ValidationRejectRequest,
)
from app.services.audit import log_audit_event

router = APIRouter(prefix="/validation", tags=["validation"])


@router.get("", response_model=PaginatedValidationResponse)
async def list_validation_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status", description="Filter by status: PENDING, APPROVED, REJECTED"),
    item_type: str | None = Query(None, description="Filter by item type: ENTITY, RELATIONSHIP, CITATION, DOCUMENT_METADATA"),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> PaginatedValidationResponse:
    """List validation queue items with pagination and status/type filters."""
    query = select(ValidationItem)
    count_query = select(func.count(ValidationItem.id))

    filters = []
    if status_filter:
        filters.append(ValidationItem.status == status_filter.upper())
    if item_type:
        filters.append(ValidationItem.item_type == item_type.upper())

    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    total = await session.scalar(count_query) or 0
    offset = (page - 1) * page_size
    items = (await session.scalars(query.order_by(ValidationItem.created_at.desc()).offset(offset).limit(page_size))).all()

    return PaginatedValidationResponse(
        items=[ValidationItemResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{item_id}", response_model=ValidationItemResponse)
async def get_validation_item(
    item_id: UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> ValidationItemResponse:
    """Retrieve details for a specific validation item."""
    item = await session.get(ValidationItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation item not found")
    return ValidationItemResponse.model_validate(item)


@router.post("/{item_id}/approve", response_model=ValidationItemResponse)
async def approve_validation_item(
    item_id: UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> ValidationItemResponse:
    """Approve a validation queue item."""
    item = await session.get(ValidationItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation item not found")

    item.status = "APPROVED"
    item.reviewer_id = current_user.id
    item.decision_timestamp = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(item)

    await log_audit_event(
        session,
        category="VALIDATION",
        action="APPROVE",
        result="SUCCESS",
        severity="INFO",
        actor_id=current_user.id,
        target_resource=f"validation_item:{item.id}",
        description=f"Approved validation item {item.id} ({item.item_type})",
        after_state={"status": "APPROVED", "reviewer_id": str(current_user.id)},
    )

    return ValidationItemResponse.model_validate(item)


@router.post("/{item_id}/reject", response_model=ValidationItemResponse)
async def reject_validation_item(
    item_id: UUID,
    body: ValidationRejectRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> ValidationItemResponse:
    """Reject a validation queue item with a reason."""
    item = await session.get(ValidationItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation item not found")

    item.status = "REJECTED"
    item.rejection_note = body.rejection_note.strip()
    item.reviewer_id = current_user.id
    item.decision_timestamp = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(item)

    await log_audit_event(
        session,
        category="VALIDATION",
        action="REJECT",
        result="SUCCESS",
        severity="INFO",
        actor_id=current_user.id,
        target_resource=f"validation_item:{item.id}",
        description=f"Rejected validation item {item.id} ({item.item_type}): {item.rejection_note}",
        after_state={
            "status": "REJECTED",
            "reviewer_id": str(current_user.id),
            "rejection_note": item.rejection_note,
        },
    )

    return ValidationItemResponse.model_validate(item)


@router.post("/bulk-approve", status_code=status.HTTP_200_OK)
async def bulk_approve_validation_items(
    body: BulkApproveRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    """Bulk approve multiple pending validation items."""
    now = datetime.now(timezone.utc)
    approved_count = 0

    for item_id in body.item_ids:
        item = await session.get(ValidationItem, item_id)
        if item and item.status == "PENDING":
            item.status = "APPROVED"
            item.reviewer_id = current_user.id
            item.decision_timestamp = now
            approved_count += 1

    await session.commit()

    await log_audit_event(
        session,
        category="VALIDATION",
        action="BULK_APPROVE",
        result="SUCCESS",
        severity="INFO",
        actor_id=current_user.id,
        target_resource="validation_items",
        description=f"Bulk approved {approved_count} validation items",
        extra_metadata={"approved_count": approved_count, "requested_ids": [str(i) for i in body.item_ids]},
    )

    return {"approved_count": approved_count}
