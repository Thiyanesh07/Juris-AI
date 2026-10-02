"""Migration reproducibility tests against a clean PostgreSQL database.

Exercises the full Alembic cycle (upgrade head, downgrade base, upgrade head)
using the same configuration source as the application. Runs synchronously
because Alembic's command API drives its own event loop.
"""

import asyncio
import os
import re
from pathlib import Path
from typing import cast

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from app.db.base import Base

API_DIR = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.usefixtures("migrated_database")


def _alembic_config() -> Config:
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "alembic"))
    return config


def _table_names() -> set[str]:
    async def _inner() -> set[str]:
        engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
        try:
            async with engine.connect() as conn:
                return await conn.run_sync(
                    lambda sync_conn: set(inspect(sync_conn).get_table_names())
                )
        finally:
            await engine.dispose()

    return asyncio.run(_inner())


def _stamped_version() -> str:
    async def _inner() -> str:
        engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT version_num FROM alembic_version"))
                return cast(str, result.scalar_one())
        finally:
            await engine.dispose()

    return asyncio.run(_inner())


def test_upgrade_head_creates_application_schema() -> None:
    names = _table_names()

    assert set(Base.metadata.tables).issubset(names)
    assert re.fullmatch(r"[0-9a-f]{12}", _stamped_version())


def test_downgrade_base_then_upgrade_head_restores_schema() -> None:
    assert "users" in _table_names()

    command.downgrade(_alembic_config(), "base")
    assert _table_names().isdisjoint(set(Base.metadata.tables))

    command.upgrade(_alembic_config(), "head")
    assert set(Base.metadata.tables).issubset(_table_names())
