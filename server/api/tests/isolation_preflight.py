"""Strict isolation preflight and safety verifications for Juris AI tests.

Enforces:
1. Resolved loopback IP validation for all test database targets.
2. Explicit test database naming allowlist (rejects production/system names).
3. Ban on automatic destructive target derivation from arbitrary non-loopback DATABASE_URL.
4. Ephemeral storage and dedicated test index verification.
5. Graph client loopback/in-memory enforcement.
6. Baseline SHA-256 protected artifact integrity guarding.
"""

from __future__ import annotations

import hashlib
import ipaddress
import os
import re
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy.engine import URL, make_url

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROTECTED_INDEX_DIR = PROJECT_ROOT / "data" / "indexes" / "legal_chunks"
PROTECTED_CORPUS_DIR = PROJECT_ROOT / "data" / "legal_corpus_v1"

_BLOCKED_DATABASE_NAMES = frozenset(
    {
        "postgres",
        "legalgraph",
        "juris",
        "juris_ai",
        "juris_production",
        "juris_prod",
        "production",
        "prod",
        "template0",
        "template1",
    }
)

_APPROVED_DB_PATTERN = re.compile(r"^[a-z0-9_]+_test$")

_LOCAL_DEV_FALLBACK_URL = (
    "postgresql+asyncpg://legalgraph:replace-with-local-postgres-password@localhost:5432/legalgraph_test"
)


class IsolationViolationError(RuntimeError):
    """Raised when an environment, network, database, or storage safety gate fails."""
    pass


def is_loopback_host(host: str | None, port: int | None = 5432) -> bool:
    """Return True only if the host string resolves strictly to loopback IP addresses."""
    if not host or not host.strip():
        return False

    clean_host = host.strip()

    # Fast-path string checks
    if clean_host in {"localhost", "127.0.0.1", "::1"}:
        pass  # Proceed to socket verification to guarantee no DNS hijacking

    try:
        # Resolve all address records
        addr_info = socket.getaddrinfo(clean_host, port or 5432, proto=socket.IPPROTO_TCP)
        if not addr_info:
            return False

        for family, _socktype, _proto, _canonname, sockaddr in addr_info:
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)
            if not ip_obj.is_loopback:
                return False
        return True
    except (socket.gaierror, ValueError, OSError):
        return False


def verify_database_safety(url_or_str: str | URL) -> URL:
    """Validate that the target database is loopback-only and explicitly approved for tests.

    Fails closed if:
    - Host is missing or resolves to a non-loopback IP.
    - Database name is missing, on the blocklist, or does not end with '_test'.
    """
    url = make_url(url_or_str) if isinstance(url_or_str, str) else url_or_str

    database = url.database
    if not database or not database.strip():
        raise IsolationViolationError("Target database URL has no database name specified.")

    clean_db = database.strip().lower()

    if clean_db in _BLOCKED_DATABASE_NAMES:
        raise IsolationViolationError(
            f"Database name {clean_db!r} is explicitly blocked from test execution (protected/production name)."
        )

    if not _APPROVED_DB_PATTERN.match(clean_db):
        raise IsolationViolationError(
            f"Database name {clean_db!r} is not an approved test database name. "
            f"Test databases must strictly match {_APPROVED_DB_PATTERN.pattern!r} (must end with '_test')."
        )

    # Loopback IP resolution check
    if not is_loopback_host(url.host, url.port):
        raise IsolationViolationError(
            f"Target database host does not resolve strictly to loopback (127.0.0.1/::1). "
            f"Connections to remote hosts are strictly forbidden in test harnesses."
        )

    return url


def get_safe_test_database_url() -> str:
    """Retrieve or construct an explicitly verified test database URL.

    Safety Rules:
    - If TEST_DATABASE_URL is set, verify it strictly.
    - If TEST_DATABASE_URL is unset:
      - Inspect DATABASE_URL.
      - If DATABASE_URL is already an approved _test database on loopback, use it.
      - If DATABASE_URL is a local loopback URL targeting a dev DB, safely derive <db>_test.
      - If DATABASE_URL targets ANY non-loopback host, REFUSE to automatically derive a target.
    """
    explicit_test_url = os.environ.get("TEST_DATABASE_URL")
    if explicit_test_url and explicit_test_url.strip():
        safe_url = verify_database_safety(explicit_test_url.strip())
        return safe_url.render_as_string(hide_password=False)

    configured_db_url = os.environ.get("DATABASE_URL")
    if not configured_db_url or not configured_db_url.strip():
        # Fallback to local loopback default
        safe_url = verify_database_safety(_LOCAL_DEV_FALLBACK_URL)
        return safe_url.render_as_string(hide_password=False)

    parsed = make_url(configured_db_url.strip())

    # Gate: Never derive from non-loopback host
    if not is_loopback_host(parsed.host, parsed.port):
        raise IsolationViolationError(
            "DATABASE_URL points to a non-loopback host. "
            "Refusing to automatically derive a test database from a remote or ambiguous configuration. "
            "Set TEST_DATABASE_URL explicitly to a local loopback database."
        )

    db_name = parsed.database or ""
    if _APPROVED_DB_PATTERN.match(db_name) and db_name not in _BLOCKED_DATABASE_NAMES:
        # Already an approved test database
        safe_url = verify_database_safety(parsed)
        return safe_url.render_as_string(hide_password=False)

    # Derive <db>_test only for local loopback
    derived_name = f"{db_name}_test"
    derived_url = parsed.set(database=derived_name)
    safe_url = verify_database_safety(derived_url)
    return safe_url.render_as_string(hide_password=False)


def verify_storage_safety(data_dir: Path | str, vector_index_name: str | None = None) -> None:
    """Ensure data_dir is isolated to a temporary directory and not the repository data store."""
    resolved_path = Path(data_dir).resolve()
    repo_data_root = (PROJECT_ROOT / "data").resolve()

    if resolved_path == repo_data_root:
        raise IsolationViolationError(
            f"data_dir resolves to the production repository data root ({repo_data_root}). "
            f"Tests must specify an ephemeral temporary directory."
        )

    # Cannot be inside protected production directories
    for protected in (PROTECTED_INDEX_DIR, PROTECTED_CORPUS_DIR):
        if protected.exists() and (resolved_path == protected.resolve() or protected.resolve() in resolved_path.parents):
            raise IsolationViolationError(
                f"data_dir ({resolved_path}) points to or within protected production directory ({protected})."
            )

    if vector_index_name and vector_index_name == "legal_chunks":
        # If vector_index_name is the production name, ensure it cannot touch the real index
        if (resolved_path / "indexes" / "legal_chunks").resolve() == PROTECTED_INDEX_DIR.resolve():
            raise IsolationViolationError(
                "vector_index_name 'legal_chunks' would collide with the production index location."
            )


def verify_graph_safety(neo4j_uri: str) -> None:
    """Ensure Neo4j URI is not pointing to remote cloud services (e.g. Aura)."""
    parsed = urlsplit(neo4j_uri)
    scheme = parsed.scheme.lower()

    if scheme in {"neo4j+s", "bolt+s", "neo4j+ssc", "bolt+ssc"}:
        raise IsolationViolationError(
            f"Remote SSL Neo4j scheme {scheme!r} detected in NEO4J_URI. "
            f"Test harnesses must only connect to local unencrypted loopback instances or in-memory fakes."
        )

    host = parsed.hostname
    if not host or not is_loopback_host(host, parsed.port or 7687):
        raise IsolationViolationError(
            f"NEO4J_URI host {host!r} is not a verified loopback address. "
            f"Tests must not contact remote graph instances."
        )


def compute_file_sha256(path: Path) -> str | None:
    """Return SHA-256 hex digest of file if it exists, else None."""
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class ProtectedArtifactGuard:
    """Monitors protected repository assets and asserts they remain untouched."""

    PROTECTED_FILES = (
        PROTECTED_INDEX_DIR / "index.faiss",
        PROTECTED_INDEX_DIR / "metadata.json",
        PROTECTED_INDEX_DIR / "embeddings.npy",
        PROTECTED_CORPUS_DIR / "metadata" / "documents.json",
        PROTECTED_CORPUS_DIR / "metadata" / "versions.json",
        PROTECTED_CORPUS_DIR / "metadata" / "provenance.json",
    )

    def __init__(self) -> None:
        self.baselines: dict[Path, str | None] = {}
        self.snapshot()

    def snapshot(self) -> None:
        self.baselines = {f: compute_file_sha256(f) for f in self.PROTECTED_FILES}

    def verify(self) -> None:
        for file_path, baseline_hash in self.baselines.items():
            current_hash = compute_file_sha256(file_path)
            if current_hash != baseline_hash:
                raise IsolationViolationError(
                    f"CRITICAL: Protected repository artifact mutated during test run!\n"
                    f"File: {file_path}\n"
                    f"Baseline SHA-256: {baseline_hash}\n"
                    f"Current SHA-256:  {current_hash}"
                )
