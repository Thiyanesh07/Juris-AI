"""Authenticated dense retrieval and admin index rebuild endpoints."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.graph.client import Neo4jClient
from app.models import User
from app.retrieval.embeddings import EmbeddingError
from app.retrieval.hybrid import hybrid_retrieve
from app.retrieval.index import IndexError
from app.retrieval.service import rebuild_index, retrieve
from app.schemas.hybrid import HybridRetrievalRequest, HybridRetrievalResponse
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search", response_model=RetrievalResponse)
async def search_evidence(
    payload: RetrievalRequest,
    _user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> RetrievalResponse:
    try:
        top_k = payload.top_k or settings.retrieval_default_top_k
        results = await asyncio.to_thread(retrieve, payload.query, top_k, settings)
        return RetrievalResponse(query=payload.query, results=results)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (EmbeddingError, IndexError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/hybrid", response_model=HybridRetrievalResponse)
async def hybrid_search_evidence(
    payload: HybridRetrievalRequest,
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> HybridRetrievalResponse:
    graph_client = Neo4jClient(settings)
    try:
        top_k = payload.top_k or settings.retrieval_default_top_k
        result = await hybrid_retrieve(
            session,
            graph_client,
            payload.query,
            top_k,
            settings,
        )
        return HybridRetrievalResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (EmbeddingError, IndexError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL is unavailable") from exc
    finally:
        await graph_client.close()


@router.post("/rebuild")
async def rebuild_dense_index(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    try:
        return await rebuild_index(session, settings)
    except (EmbeddingError, IndexError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
