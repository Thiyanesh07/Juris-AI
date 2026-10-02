"""Evaluation runs API — admin-only read access to ``evaluation_runs`` (Phase 7C.1)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.db.session import get_session
from app.models import EvaluationRun, User
from app.schemas.evaluation import EvaluationRunSchema, PaginatedEvaluationRuns

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get(
    "",
    response_model=PaginatedEvaluationRuns,
    summary="List evaluation runs",
)
async def list_evaluation_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> PaginatedEvaluationRuns:
    """Return a paginated list of evaluation runs (newest first)."""
    count_query = select(func.count()).select_from(EvaluationRun)
    total = (await session.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    runs = (
        await session.execute(
            select(EvaluationRun)
            .order_by(EvaluationRun.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).scalars().all()

    return PaginatedEvaluationRuns(
        items=[EvaluationRunSchema.model_validate(run) for run in runs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{evaluation_id}",
    response_model=EvaluationRunSchema,
    summary="Get one evaluation run",
)
async def get_evaluation_run(
    evaluation_id: UUID,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> EvaluationRunSchema:
    run = await session.get(EvaluationRun, evaluation_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation run not found",
        )
    return EvaluationRunSchema.model_validate(run)


@router.post(
    "/run",
    response_model=EvaluationRunSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger reproducible benchmark run",
)
async def trigger_evaluation_run(
    name: str = Query("GraphRAG Strategy Comparison Benchmark"),
    top_k: int = Query(5, ge=1, le=20),
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> EvaluationRunSchema:
    """Execute reproducible evaluation benchmark across retrieval strategies."""
    from app.services.evaluation_runner import run_evaluation_benchmark
    eval_run = await run_evaluation_benchmark(
        session=session,
        name=name,
        top_k=top_k,
    )
    return EvaluationRunSchema.model_validate(eval_run)
