"""Pytest fixtures: a clean PostgreSQL test database migrated via Alembic.

Isolation strategy
------------------
The test URL is derived from ``DATABASE_URL`` by appending ``_test`` to the
database name, and is pinned into the environment BEFORE any ``app`` import so
the application, Alembic and the tests all target the same throwaway database.
For every test session the database is dropped/recreated and migrated with
``alembic upgrade head``; every test runs against the migrated schema (no
``create_all`` shortcuts) and leaves the tables truncated afterwards.

Integration tests require the local Docker PostgreSQL:

    docker compose --env-file .env.example --profile infra up -d postgres
"""

import asyncio
import os
import re
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

API_DIR = Path(__file__).resolve().parents[1]

_FALLBACK_DEV_URL = (
    "postgresql+asyncpg://legalgraph:replace-with-local-postgres-password@localhost:5432/legalgraph"
)


def _test_database_url() -> str:
    """Derive the isolated ``<db>_test`` URL from DATABASE_URL or the default."""
    url = make_url(os.environ.get("DATABASE_URL", _FALLBACK_DEV_URL))
    database = url.database or "legalgraph"
    if not re.fullmatch(r"[a-z0-9_]+", database):
        raise RuntimeError(f"Unsafe database name for tests: {database!r}")
    return url.set(database=f"{database}_test").render_as_string(hide_password=False)


# Pin the test database before any app module (and therefore Settings) loads.
os.environ["DATABASE_URL"] = _test_database_url()
os.environ.setdefault("SESSION_SECRET", "test-session-secret-not-for-production")

from alembic.config import Config  # noqa: E402

from alembic import command  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.main import app  # noqa: E402


def _alembic_config() -> Config:
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "alembic"))
    return config


async def _reset_test_database() -> None:
    """Drop and recreate the test database (via the maintenance database)."""
    url = make_url(os.environ["DATABASE_URL"])
    database = url.database
    if database is None:
        raise RuntimeError("Test database URL has no database name")
    admin_engine = create_async_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.begin() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)'))
            await conn.execute(text(f'CREATE DATABASE "{database}"'))
    finally:
        await admin_engine.dispose()


@pytest.fixture(scope="session")
def migrated_database() -> Iterator[None]:
    """Provide a freshly created database migrated to head via Alembic."""
    asyncio.run(_reset_test_database())
    command.upgrade(_alembic_config(), "head")
    yield


@pytest.fixture
async def engine(migrated_database: None) -> AsyncIterator[AsyncEngine]:
    """Function-scoped engine over the migrated test database."""
    test_engine = create_async_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    yield test_engine
    await test_engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Session over the migrated schema; truncates all tables afterwards."""
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as test_session:
        yield test_session
    table_names = ", ".join(f'"{name}"' for name in Base.metadata.tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client(migrated_database: None) -> Iterator[TestClient]:
    """TestClient whose sessions use a fresh NullPool engine (event-loop safe)."""
    holder: dict[str, AsyncEngine] = {}

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        if "engine" not in holder:
            holder["engine"] = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
        maker = async_sessionmaker(holder["engine"], expire_on_commit=False)
        async with maker() as test_session:
            try:
                yield test_session
            except Exception:
                await test_session.rollback()
                raise

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
