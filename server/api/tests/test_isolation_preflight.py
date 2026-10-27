"""Unit tests verifying that isolation preflight gates fail closed on safety violations."""

import os
from pathlib import Path
import pytest
from sqlalchemy.engine import make_url

from tests.isolation_preflight import (
    IsolationViolationError,
    ProtectedArtifactGuard,
    get_safe_test_database_url,
    is_loopback_host,
    verify_database_safety,
    verify_graph_safety,
    verify_storage_safety,
)


def test_is_loopback_host():
    assert is_loopback_host("localhost") is True
    assert is_loopback_host("127.0.0.1") is True
    assert is_loopback_host("::1") is True
    assert is_loopback_host("example.com") is False
    assert is_loopback_host("8.8.8.8") is False
    assert is_loopback_host("") is False
    assert is_loopback_host(None) is False


def test_verify_database_safety_rejects_non_loopback():
    with pytest.raises(IsolationViolationError, match="does not resolve strictly to loopback"):
        verify_database_safety("postgresql+asyncpg://user:pass@example.com:5432/legalgraph_test")


def test_verify_database_safety_rejects_blocked_db_names():
    for blocked in ("postgres", "legalgraph", "juris_production", "template1"):
        with pytest.raises(IsolationViolationError, match="explicitly blocked from test execution"):
            verify_database_safety(f"postgresql+asyncpg://user:pass@127.0.0.1:5432/{blocked}")


def test_verify_database_safety_rejects_non_test_suffix():
    with pytest.raises(IsolationViolationError, match="must end with '_test'"):
        verify_database_safety("postgresql+asyncpg://user:pass@127.0.0.1:5432/my_database")


def test_verify_database_safety_accepts_valid_loopback_test_db():
    safe_url = verify_database_safety("postgresql+asyncpg://user:pass@127.0.0.1:5432/juris_test")
    assert safe_url.database == "juris_test"


def test_get_safe_test_database_url_rejects_remote_derivation(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@remote.postgres.render.com:5432/juris_prod")
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    with pytest.raises(IsolationViolationError, match="points to a non-loopback host"):
        get_safe_test_database_url()


def test_get_safe_test_database_url_accepts_explicit_test_url(monkeypatch):
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://user:pass@127.0.0.1:5432/custom_test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@remote.postgres.render.com:5432/prod")
    safe = get_safe_test_database_url()
    assert "custom_test" in safe


def test_verify_storage_safety_rejects_production_data_dir():
    from tests.isolation_preflight import PROJECT_ROOT
    with pytest.raises(IsolationViolationError, match="resolves to the production repository data root"):
        verify_storage_safety(PROJECT_ROOT / "data")


def test_verify_storage_safety_accepts_tmp_path(tmp_path: Path):
    # Should pass without error
    verify_storage_safety(tmp_path, vector_index_name="phase6_test_chunks")


def test_verify_graph_safety_rejects_remote_and_aura():
    with pytest.raises(IsolationViolationError, match="Remote SSL Neo4j scheme"):
        verify_graph_safety("neo4j+s://abc12345.databases.neo4j.io")

    with pytest.raises(IsolationViolationError, match="is not a verified loopback address"):
        verify_graph_safety("bolt://remote.neo4j.corp:7687")


def test_protected_artifact_guard_snapshot_and_verify(tmp_path: Path, monkeypatch):
    test_file = tmp_path / "protected.txt"
    test_file.write_text("initial content", encoding="utf-8")

    class CustomGuard(ProtectedArtifactGuard):
        PROTECTED_FILES = (test_file,)

    guard = CustomGuard()
    guard.verify()  # Passes

    test_file.write_text("mutated content", encoding="utf-8")
    with pytest.raises(IsolationViolationError, match="Protected repository artifact mutated"):
        guard.verify()
