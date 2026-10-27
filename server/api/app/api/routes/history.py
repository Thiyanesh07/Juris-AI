"""User Research History API Routes (Phase 16).

Provides persistent user research session history with ownership validation and pagination.
Users can only access their own history.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_session
from app.models import ResearchAnswer, ResearchQuery, ResearchSession, SavedResearch, User
from app.schemas.history import (
    PaginatedHistoryResponse,
    ResearchAnswerSummary,
    ResearchCitationSummary,
    ResearchHistoryItemResponse,
    ResearchQuerySummary,
)

router = APIRouter(prefix="/research/history", tags=["research_history"])


def _canonical_mode(val: str | None) -> str:
    if not val:
        return "COMPREHENSIVE"
    v = str(val).strip().upper()
    if v in ("COMPREHENSIVE", "CONSTITUTIONAL", "STATUTORY", "CASE_LAW"):
        return v
    if v in ("HYBRID", "VECTOR_ONLY", "GRAPH_ONLY"):
        return "COMPREHENSIVE"
    return "COMPREHENSIVE"


def _to_session_response(s: ResearchSession, is_saved: bool = False) -> ResearchHistoryItemResponse:
    queries_summary: list[ResearchQuerySummary] = []
    latest_mode = "COMPREHENSIVE"

    for q in getattr(s, "queries", []):
        answers_summary: list[ResearchAnswerSummary] = []
        for a in getattr(q, "answers", []):
            val_stat = (
                a.validation_status.value
                if hasattr(a.validation_status, "value")
                else str(a.validation_status)
            )
            raw_mode = getattr(a, "mode", "COMPREHENSIVE")
            a_mode = _canonical_mode(raw_mode)
            latest_mode = a_mode

            cit_summaries = []
            for c in getattr(a, "citations", []):
                cid = getattr(c, "chunk_id", None)
                mkr = getattr(c, "marker", None)
                stable_id = f"cit_{cid}_{mkr}" if cid and mkr else str(c.id)
                ver_status = (
                    "VERIFIED"
                    if val_stat == "validated"
                    else "PARTIALLY_VERIFIED"
                    if val_stat == "warning"
                    else "UNVERIFIED"
                )
                cit_summaries.append(
                    ResearchCitationSummary(
                        id=c.id,
                        citation=c.citation,
                        relevance=c.relevance,
                        source_type=c.source_type,
                        document_id=c.document_id,
                        chunk_id=cid,
                        marker=mkr,
                        page_start=getattr(c, "page_start", None),
                        page_end=getattr(c, "page_end", None),
                        citation_ref=getattr(c, "citation_ref", None),
                        pdf_url=getattr(c, "pdf_url", None),
                        document_title=c.source_type,
                        verification_status=ver_status,
                        stable_id=stable_id,
                    )
                )

            evidence_items = getattr(a, "evidence_json", None) or []
            graph_data = getattr(a, "graph_json", None)
            reasoning_steps = getattr(a, "reasoning_steps_json", None) or []
            citation_validation = getattr(a, "citation_validation_json", None)

            answers_summary.append(
                ResearchAnswerSummary(
                    id=a.id,
                    answer=a.answer,
                    validation_status=val_stat,
                    created_at=a.created_at,
                    mode=a_mode,
                    citations=cit_summaries,
                    evidence=evidence_items,
                    graph=graph_data,
                    reasoning_steps=reasoning_steps,
                    citation_validation=citation_validation,
                )
            )
        queries_summary.append(
            ResearchQuerySummary(
                id=q.id,
                question=q.question,
                created_at=q.created_at,
                answers=answers_summary,
            )
        )

    return ResearchHistoryItemResponse(
        id=s.id,
        title=s.title,
        created_at=s.created_at,
        updated_at=s.updated_at,
        mode=latest_mode,
        queries=queries_summary,
        saved=is_saved,
    )


@router.get("", response_model=PaginatedHistoryResponse)
async def list_research_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PaginatedHistoryResponse:
    """Retrieve paginated research session history for current user."""
    query = (
        select(ResearchSession)
        .where(ResearchSession.user_id == current_user.id)
        .options(
            selectinload(ResearchSession.queries)
            .selectinload(ResearchQuery.answers)
            .selectinload(ResearchAnswer.citations)
        )
    )
    count_query = select(func.count(ResearchSession.id)).where(ResearchSession.user_id == current_user.id)

    total = await session.scalar(count_query) or 0
    offset = (page - 1) * page_size
    sessions = (await session.scalars(query.order_by(ResearchSession.created_at.desc()).offset(offset).limit(page_size))).all()

    # Find saved session IDs for user
    saved_ids = set(
        await session.scalars(
            select(SavedResearch.session_id).where(SavedResearch.user_id == current_user.id)
        )
    )

    items = [_to_session_response(s, is_saved=(s.id in saved_ids)) for s in sessions]

    return PaginatedHistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{session_id}", response_model=ResearchHistoryItemResponse)
async def get_research_history_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ResearchHistoryItemResponse:
    """Retrieve a single research session history item (ownership enforced)."""
    query = (
        select(ResearchSession)
        .where(ResearchSession.id == session_id, ResearchSession.user_id == current_user.id)
        .options(
            selectinload(ResearchSession.queries)
            .selectinload(ResearchQuery.answers)
            .selectinload(ResearchAnswer.citations)
        )
    )
    res = await session.scalar(query)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research session not found")

    is_saved = bool(
        await session.scalar(
            select(SavedResearch).where(
                SavedResearch.user_id == current_user.id, SavedResearch.session_id == session_id
            )
        )
    )

    return _to_session_response(res, is_saved=is_saved)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_research_history_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a research session from user history (ownership enforced)."""
    s = await session.scalar(
        select(ResearchSession).where(
            ResearchSession.id == session_id, ResearchSession.user_id == current_user.id
        )
    )
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research session not found")

    await session.delete(s)
    await session.commit()
