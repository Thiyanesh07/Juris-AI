"""Health & Public Statistics Endpoints.

Provides application liveness, comprehensive component connectivity health checks
(PostgreSQL, Neo4j Aura, FAISS Vector Index, LLM Provider, Corpus metrics),
and public-safe production system statistics.
"""

from typing import Any, Literal
import asyncio

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_data_dir, get_settings
from app.db.health import ping_database
from app.db.session import get_session
from app.graph.client import Neo4jClient
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.retrieval.index import load_index

router = APIRouter(tags=["health"])

_SERVICE = "legalgraph-api"
_VERSION = "0.6.1"


class ComponentHealth(BaseModel):
    """Component connectivity status with details."""

    status: Literal["ok", "degraded", "unreachable", "unavailable"]
    detail: str | None = None
    metrics: dict[str, Any] | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """Overall application health with per-component detail."""

    status: Literal["ok", "degraded"]
    service: str
    version: str
    components: dict[str, ComponentHealth]


class DatabaseHealthResponse(BaseModel):
    """Database-only health report."""

    status: Literal["ok", "unavailable"]
    database: ComponentHealth


class PublicStatsResponse(BaseModel):
    """Verified non-sensitive production corpus and graph metrics."""

    total_documents: int
    ready_documents: int
    total_chunks: int
    graph_nodes: int
    graph_relationships: int
    vector_count: int
    vector_dimension: int
    embedding_model: str
    graph_labels: dict[str, int]
    graph_relationship_types: dict[str, int]


async def _check_database(session: AsyncSession) -> ComponentHealth:
    """Ping PostgreSQL."""
    try:
        await ping_database(session)
        doc_count = await session.scalar(select(func.count(Document.id))) or 0
        chunk_count = await session.scalar(select(func.count(Chunk.id))) or 0
        return ComponentHealth(
            status="ok",
            detail="PostgreSQL connected",
            metrics={"documents": doc_count, "chunks": chunk_count},
        )
    except Exception as exc:
        return ComponentHealth(status="unreachable", error=str(exc) or type(exc).__name__)


async def _check_neo4j(settings: Settings) -> ComponentHealth:
    """Check Neo4j Aura connectivity and node/relationship counts."""
    client = Neo4jClient(settings)
    try:
        await client.health()
        stats = await client.statistics()
        nodes_by_label = stats.get("nodes_by_label", {})
        rels_by_type = stats.get("relationships_by_type", {})
        total_nodes = sum(nodes_by_label.values())
        total_rels = sum(rels_by_type.values())
        return ComponentHealth(
            status="ok",
            detail=f"Neo4j Aura connected ({total_nodes:,} nodes, {total_rels:,} rels)",
            metrics={
                "total_nodes": total_nodes,
                "total_relationships": total_rels,
                "nodes_by_label": nodes_by_label,
                "relationships_by_type": rels_by_type,
            },
        )
    except Exception as exc:
        return ComponentHealth(status="unreachable", error=str(exc) or "Neo4j connection failed")
    finally:
        await client.close()


def _check_vector_index(settings: Settings) -> ComponentHealth:
    """Check FAISS index loading and vector counts."""
    try:
        data_dir = get_data_dir()
        index, metadata = load_index(data_dir, settings.vector_index_name)
        return ComponentHealth(
            status="ok",
            detail=f"FAISS index loaded ({index.ntotal:,} vectors, {index.d}d)",
            metrics={
                "vector_count": index.ntotal,
                "dimension": index.d,
                "index_type": metadata.get("index_type", "IndexFlatIP"),
                "embedding_model": metadata.get("embedding_model", settings.embedding_model_name),
            },
        )
    except Exception as exc:
        return ComponentHealth(status="unavailable", error=str(exc) or "Vector index unavailable")


def _check_llm(settings: Settings) -> ComponentHealth:
    """Check LLM provider configuration."""
    if settings.llm_api_key or settings.llm_provider in ("google_genai", "openai_compatible"):
        return ComponentHealth(
            status="ok",
            detail=f"LLM Provider configured ({settings.llm_provider}:{settings.llm_model})",
            metrics={"provider": settings.llm_provider, "model": settings.llm_model},
        )
    return ComponentHealth(status="unreachable", error="LLM API key not configured")


@router.get("/health", response_model=HealthResponse)
async def read_health(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Comprehensive multi-component health report."""
    database, neo4j = await asyncio.gather(
        _check_database(session),
        _check_neo4j(settings),
    )
    vector_index = await asyncio.to_thread(_check_vector_index, settings)
    llm = _check_llm(settings)

    all_ok = all(
        c.status == "ok"
        for c in (database, neo4j, vector_index, llm)
    )

    return HealthResponse(
        status="ok" if all_ok else "degraded",
        service=_SERVICE,
        version=_VERSION,
        components={
            "database": database,
            "neo4j": neo4j,
            "vector_index": vector_index,
            "llm": llm,
        },
    )


@router.get("/health/database", response_model=DatabaseHealthResponse)
async def read_database_health(session: AsyncSession = Depends(get_session)) -> Response:
    """Database connectivity health (503 when PostgreSQL is unreachable)."""
    database = await _check_database(session)
    body = DatabaseHealthResponse(
        status="ok" if database.status == "ok" else "unavailable", database=database
    )
    if body.status == "unavailable":
        return JSONResponse(status_code=503, content=body.model_dump(mode="json"))
    return JSONResponse(content=body.model_dump(mode="json"))


@router.get("/stats", response_model=PublicStatsResponse)
@router.get("/public/stats", response_model=PublicStatsResponse)
async def get_public_stats(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PublicStatsResponse:
    """Return verified non-sensitive production corpus and graph statistics."""
    total_docs = await session.scalar(select(func.count(Document.id))) or 0
    ready_docs = await session.scalar(select(func.count(Document.id)).where(Document.status == DocumentStatus.READY)) or 0
    total_chunks = await session.scalar(select(func.count(Chunk.id))) or 0

    client = Neo4jClient(settings)
    nodes_by_label: dict[str, int] = {}
    rels_by_type: dict[str, int] = {}
    total_nodes = 0
    total_rels = 0
    try:
        stats = await client.statistics()
        nodes_by_label = stats.get("nodes_by_label", {})
        rels_by_type = stats.get("relationships_by_type", {})
        total_nodes = sum(nodes_by_label.values())
        total_rels = sum(rels_by_type.values())
    except Exception:
        pass
    finally:
        await client.close()

    vector_count = 0
    vector_dim = 768
    model_name = settings.embedding_model_name
    try:
        index, meta = load_index(get_data_dir(), settings.vector_index_name)
        vector_count = index.ntotal
        vector_dim = index.d
        model_name = meta.get("embedding_model", model_name)
    except Exception:
        pass

    return PublicStatsResponse(
        total_documents=total_docs,
        ready_documents=ready_docs,
        total_chunks=total_chunks,
        graph_nodes=total_nodes,
        graph_relationships=total_rels,
        vector_count=vector_count,
        vector_dimension=vector_dim,
        embedding_model=model_name,
        graph_labels=nodes_by_label,
        graph_relationship_types=rels_by_type,
    )

