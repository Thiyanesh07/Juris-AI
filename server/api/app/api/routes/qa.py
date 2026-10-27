"""Authenticated legal QA endpoint grounded on hybrid GraphRAG retrieval."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.graph.client import Neo4jClient
from app.models import Citation, Document, ResearchAnswer, ResearchQuery, ResearchSession, User
from app.models.enums import ValidationStatus
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

    # Ensure user exists in database session (handles mocked auth in test harnesses)
    user_in_db = await session.scalar(select(User.id).where(User.id == _user.id))
    if not user_in_db:
        existing_by_email = await session.scalar(select(User).where(User.email == _user.email))
        if existing_by_email:
            _user = existing_by_email
        else:
            session.add(_user)
            await session.flush()

    # 1. Resolve or validate research session
    research_session: ResearchSession | None = None
    if payload.session_id is not None:
        research_session = await session.scalar(
            select(ResearchSession).where(ResearchSession.id == payload.session_id)
        )
        if not research_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Research session not found",
            )
        if research_session.user_id != _user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this research session",
            )
    else:
        title = payload.query.strip().split("\n")[0][:120] or "Research Session"
        research_session = ResearchSession(
            user_id=_user.id,
            title=title,
        )
        session.add(research_session)
        await session.flush()

    graph_client = Neo4jClient(settings)
    try:
        response = await ask_legal_question(
            session,
            graph_client,
            payload.query,
            payload.top_k,
            settings,
            mode=payload.mode or "COMPREHENSIVE",
            retrieval_strategy=payload.retrieval_strategy or "hybrid",
            graph_depth=payload.graph_depth,
        )

        # 2. Persist query, answer, and citations
        rq = ResearchQuery(
            session_id=research_session.id,
            question=payload.query.strip(),
        )
        session.add(rq)
        await session.flush()

        if response.status == "insufficient_evidence":
            val_status = ValidationStatus.FAILED
        elif response.citation_validation and (
            not response.citation_validation.grounded or response.citation_validation.warnings
        ):
            val_status = ValidationStatus.WARNING
        else:
            val_status = ValidationStatus.VALIDATED

        answer_text = response.answer or "Insufficient evidence to answer this question."
        ev_dump = [
            e.model_dump(mode="json") if hasattr(e, "model_dump") else e
            for e in (response.evidence or [])
        ]
        graph_dump = (
            response.graph.model_dump(mode="json")
            if response.graph and hasattr(response.graph, "model_dump")
            else response.graph
        )
        steps_dump = [
            s.model_dump(mode="json") if hasattr(s, "model_dump") else s
            for s in (response.reasoning_steps or [])
        ]
        val_dump = (
            response.citation_validation.model_dump(mode="json")
            if response.citation_validation and hasattr(response.citation_validation, "model_dump")
            else response.citation_validation
        )

        ra = ResearchAnswer(
            query_id=rq.id,
            answer=answer_text,
            validation_status=val_status,
            mode=str(payload.mode or "COMPREHENSIVE"),
            evidence_json=ev_dump,
            graph_json=graph_dump,
            reasoning_steps_json=steps_dump,
            citation_validation_json=val_dump,
        )
        session.add(ra)
        await session.flush()

        for c in response.citations:
            valid_doc_id = None
            if c.document_id:
                doc_exists = await session.scalar(
                    select(Document.id).where(Document.id == c.document_id)
                )
                if doc_exists:
                    valid_doc_id = c.document_id
            cit_label = f"[{c.marker}] {c.document_title}"
            if c.citation_ref:
                cit_label += f" ({c.citation_ref})"
            cit = Citation(
                answer_id=ra.id,
                document_id=valid_doc_id,
                chunk_id=c.chunk_id,
                marker=c.marker,
                page_start=c.page_start,
                page_end=c.page_end,
                citation=cit_label,
                citation_ref=c.citation_ref,
                pdf_url=c.pdf_url,
                relevance=1.0,
                source_type=(c.document_title or "DOCUMENT")[:64],
            )
            session.add(cit)

        await session.commit()
        response.session_id = research_session.id
        return response
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
