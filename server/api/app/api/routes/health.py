"""Health endpoints: application liveness plus PostgreSQL connectivity.

``GET /health`` is always HTTP 200 while the process is up (liveness); the
overall status becomes "degraded" and ``components.database`` reports the
failure if PostgreSQL is unreachable. ``GET /health/database`` reflects
database connectivity as a 200/503 for orchestration tooling.
"""

from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.health import ping_database
from app.db.session import get_session

router = APIRouter(tags=["health"])

_SERVICE = "legalgraph-api"
_VERSION = "0.1.0"


class DatabaseComponent(BaseModel):
    """Database connectivity component."""

    status: Literal["ok", "unreachable"]
    error: str | None = None


class HealthResponse(BaseModel):
    """Overall application health with per-component detail."""

    status: Literal["ok", "degraded"]
    service: Literal["legalgraph-api"]
    version: str
    components: dict[str, DatabaseComponent]


class DatabaseHealthResponse(BaseModel):
    """Database-only health report."""

    status: Literal["ok", "unavailable"]
    database: DatabaseComponent


async def _check_database(session: AsyncSession) -> DatabaseComponent:
    """Ping PostgreSQL, converting any failure into an unreachable component."""
    try:
        await ping_database(session)
    except Exception as exc:  # health must never raise on database failure
        error = str(exc) or type(exc).__name__
        return DatabaseComponent(status="unreachable", error=error)
    return DatabaseComponent(status="ok")


@router.get("/health", response_model=HealthResponse)
async def read_health(session: AsyncSession = Depends(get_session)) -> HealthResponse:
    """Application health (liveness + component overview)."""
    database = await _check_database(session)
    return HealthResponse(
        status="ok" if database.status == "ok" else "degraded",
        service=_SERVICE,
        version=_VERSION,
        components={"database": database},
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
