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


from tests.isolation_preflight import (  # noqa: E402
    IsolationViolationError,
    ProtectedArtifactGuard,
    get_safe_test_database_url,
    verify_database_safety,
)


def _test_database_url() -> str:
    """Derive the strictly verified, loopback-only test database URL."""
    return get_safe_test_database_url()


# Pin the test database before any app module (and therefore Settings) loads.
os.environ["DATABASE_URL"] = _test_database_url()
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SESSION_SECRET", "test-session-secret-not-for-production")

from alembic.config import Config  # noqa: E402

from alembic import command  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.rate_limit import reset_rate_limiters  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.main import app  # noqa: E402

_ORIGINAL_SETTINGS = get_settings().model_dump()


@pytest.fixture(scope="session", autouse=True)
def protected_artifact_guard() -> Iterator[None]:
    """Ensure protected repository assets remain completely untouched across the test session."""
    guard = ProtectedArtifactGuard()
    yield
    guard.verify()


@pytest.fixture(autouse=True)
def restore_global_settings():
    reset_rate_limiters()
    yield
    reset_rate_limiters()
    settings = get_settings()
    for key, value in _ORIGINAL_SETTINGS.items():
        object.__setattr__(settings, key, value)


def _alembic_config() -> Config:
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "alembic"))
    return config


async def _reset_test_database() -> None:
    """Drop and recreate the test database (via the maintenance database) with safety verification."""
    url = verify_database_safety(os.environ["DATABASE_URL"])
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
    verified_url = verify_database_safety(os.environ["DATABASE_URL"])
    test_engine = create_async_engine(verified_url, pool_pre_ping=True)
    yield test_engine
    await test_engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Session over the migrated schema; truncates all tables afterwards."""
    verify_database_safety(os.environ["DATABASE_URL"])
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
    with TestClient(app, headers={"Origin": "http://localhost:3000"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()
