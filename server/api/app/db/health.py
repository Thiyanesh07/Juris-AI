"""Lightweight database connectivity check used by the health endpoints."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def ping_database(session: AsyncSession) -> None:
    """Run a minimal round-trip query; raises if PostgreSQL is unreachable."""
    await session.execute(text("SELECT 1"))
