"""Authenticated legal QA endpoint grounded on hybrid GraphRAG retrieval."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.graph.client import Neo4jClient
from app.models import User
from app.qa.provider import (
    LLMProviderMalformedResponse,
    LLMProviderTimeout,
    LLMProviderUnavailable,
)
from app.qa.service import QAInvalidModelOutputError, ask_legal_question
from app.retrieval.embeddings import EmbeddingError
from app.retrieval.index import IndexError
from app.schemas.qa import QAAskRequest, QAAskResponse

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/ask", response_model=QAAskResponse)
async def ask_legal_qa(
    payload: QAAskRequest,
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> QAAskResponse:
    if payload.top_k is not None and payload.top_k > settings.retrieval_max_top_k:
        raise HTTPException(
            status_code=422,
            detail=f"top_k must be between 1 and {settings.retrieval_max_top_k}",
        )

    graph_client = Neo4jClient(settings)
    try:
        return await ask_legal_question(
            session,
            graph_client,
            payload.query,
            payload.top_k,
            settings,
            mode=payload.mode or "COMPREHENSIVE",
            retrieval_strategy=payload.retrieval_strategy or "hybrid",
            graph_depth=payload.graph_depth,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LLMProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMProviderMalformedResponse as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMProviderTimeout as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except QAInvalidModelOutputError as exc:
        raise HTTPException(status_code=502, detail="Invalid model output") from exc
    except (EmbeddingError, IndexError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL is unavailable") from exc
    finally:
        await graph_client.close()
