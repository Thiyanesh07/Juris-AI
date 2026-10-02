"""Saved Research API Routes (Phase 16).

Allows authenticated users to bookmark and manage saved research sessions.
Ownership checks are strictly enforced.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.history import _to_session_response
from app.auth.dependencies import get_current_user
from app.db.session import get_session
from app.models import ResearchQuery, ResearchSession, SavedResearch, User
from app.schemas.history import SavedResearchCreateRequest, SavedResearchResponse
from app.services.audit import log_audit_event

router = APIRouter(prefix="/research/saved", tags=["saved_research"])


@router.post("", response_model=SavedResearchResponse, status_code=status.HTTP_201_CREATED)
async def create_saved_research(
    body: SavedResearchCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SavedResearchResponse:
    """Bookmark/save a research session for the current user."""
    res_session = await session.scalar(
        select(ResearchSession)
        .where(ResearchSession.id == body.session_id, ResearchSession.user_id == current_user.id)
        .options(selectinload(ResearchSession.queries).selectinload(ResearchQuery.answers))
    )
    if not res_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research session not found")

    existing = await session.scalar(
        select(SavedResearch).where(
            SavedResearch.user_id == current_user.id, SavedResearch.session_id == body.session_id
        )
    )
    if existing:
        return SavedResearchResponse(
            id=existing.id,
            user_id=existing.user_id,
            session_id=existing.session_id,
            title=body.title or res_session.title,
            created_at=existing.created_at,
            session=_to_session_response(res_session, is_saved=True),
        )

    saved = SavedResearch(
        user_id=current_user.id,
        session_id=body.session_id,
    )
    session.add(saved)
    await session.commit()
    await session.refresh(saved)

    await log_audit_event(
        session,
        category="SAVED_RESEARCH",
        action="CREATE",
        result="SUCCESS",
        severity="INFO",
        actor_id=current_user.id,
        target_resource=f"saved_research:{saved.id}",
        description=f"Saved research session {res_session.id} ({res_session.title})",
    )

    return SavedResearchResponse(
        id=saved.id,
        user_id=saved.user_id,
        session_id=saved.session_id,
        title=body.title or res_session.title,
        created_at=saved.created_at,
        session=_to_session_response(res_session, is_saved=True),
    )


@router.get("", response_model=list[SavedResearchResponse])
async def list_saved_research(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SavedResearchResponse]:
    """List all saved research bookmarks for the current user."""
    query = (
        select(SavedResearch)
        .where(SavedResearch.user_id == current_user.id)
        .options(
            selectinload(SavedResearch.session)
            .selectinload(ResearchSession.queries)
            .selectinload(ResearchQuery.answers)
        )
        .order_by(SavedResearch.created_at.desc())
    )
    saved_items = (await session.scalars(query)).all()

    results: list[SavedResearchResponse] = []
    for s in saved_items:
        sess_resp = _to_session_response(s.session, is_saved=True) if s.session else None
        title = s.session.title if s.session else "Saved Research"
        results.append(
            SavedResearchResponse(
                id=s.id,
                user_id=s.user_id,
                session_id=s.session_id,
                title=title,
                created_at=s.created_at,
                session=sess_resp,
            )
        )

    return results


@router.get("/{saved_id}", response_model=SavedResearchResponse)
async def get_saved_research(
    saved_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SavedResearchResponse:
    """Retrieve details for a single saved research bookmark (ownership enforced)."""
    query = (
        select(SavedResearch)
        .where(SavedResearch.id == saved_id, SavedResearch.user_id == current_user.id)
        .options(
            selectinload(SavedResearch.session)
            .selectinload(ResearchSession.queries)
            .selectinload(ResearchQuery.answers)
        )
    )
    saved = await session.scalar(query)
    if not saved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved research item not found")

    sess_resp = _to_session_response(saved.session, is_saved=True) if saved.session else None
    title = saved.session.title if saved.session else "Saved Research"

    return SavedResearchResponse(
        id=saved.id,
        user_id=saved.user_id,
        session_id=saved.session_id,
        title=title,
        created_at=saved.created_at,
        session=sess_resp,
    )


@router.delete("/{saved_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_research(
    saved_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Remove a saved research bookmark (ownership enforced)."""
    saved = await session.scalar(
        select(SavedResearch).where(
            SavedResearch.id == saved_id, SavedResearch.user_id == current_user.id
        )
    )
    if not saved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved research item not found")

    await session.delete(saved)
    await session.commit()
