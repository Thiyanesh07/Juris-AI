"""Application settings loaded from environment variables (with .env support).

There is deliberately a single configuration system for the whole backend.
`DATABASE_URL` follows the naming established in the root `.env.example`.
"""

import ipaddress
import json
from functools import lru_cache
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the .env file relative to this file's location so it works correctly
# regardless of the current working directory (e.g., when Alembic runs from services/api/).
# Walk up from this file: config.py → core → app → api → services → project root
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = _HERE.parent.parent.parent.parent.parent  # 5 levels up to project root
_ENV_FILE = _PROJECT_ROOT / ".env"
_ENV_LOCAL = _PROJECT_ROOT / ".env.local"
_DEFAULT_GOOGLE_OAUTH_JSON = _PROJECT_ROOT / "google-oauth-client.json"

_LEGACY_BACKEND_OAUTH_CALLBACKS = frozenset(
    {
        "http://127.0.0.1:8000/auth/google/callback",
        "http://localhost:8000/auth/google/callback",
    }
)


def _oauth_callback_for_frontend(frontend_url: str) -> str:
    return f"{frontend_url.rstrip('/')}/auth/google/callback"


def _load_google_credentials_from_file(path: Path) -> tuple[str, str] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    block = payload.get("web") or payload.get("installed")
    if not isinstance(block, dict):
        return None
    client_id = block.get("client_id")
    client_secret = block.get("client_secret")
    if (
        isinstance(client_id, str)
        and isinstance(client_secret, str)
        and client_id.strip()
        and client_secret.strip()
    ):
        return client_id.strip(), client_secret.strip()
    return None

# Local development fallback mirroring docker-compose.yml + .env.example.
# The password is the documented local placeholder, not a secret. Override with
# the DATABASE_URL environment variable (or a .env file) in any other context.
_DEFAULT_DATABASE_URL = (
    "postgresql+asyncpg://legalgraph:replace-with-local-postgres-password@localhost:5434/legalgraph"
)


class Settings(BaseSettings):
    """Environment-driven application settings."""

    _ALLOWED_APP_ENVS: ClassVar[frozenset[str]] = frozenset(
        {"development", "test", "production"}
    )

    model_config = SettingsConfigDict(
        env_file=(str(_ENV_FILE), str(_ENV_LOCAL)),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Required deployment mode; local/test callers must set it explicitly.
    app_env: str
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:5173"
    # Comma-separated list of additional CORS origins (e.g. production Vercel URLs).
    # EXTRA_CORS_ORIGINS="https://juris-ai.vercel.app,https://juris-ai-admin.vercel.app"
    extra_cors_origins: str = ""
    session_secret: str = "dev-secret-change-in-production-min-32-chars-long"
    session_cookie_secure: bool = False
    session_max_age_seconds: int = 60 * 60 * 24 * 7
    # Rate limiting is process-local; use an edge/shared-store limiter for a
    # global quota across multiple workers or application instances.
    rate_limit_enabled: bool = True
    rate_limit_window_seconds: int = 60
    rate_limit_auth_requests: int = 30
    rate_limit_qa_requests: int = 30
    rate_limit_upload_requests: int = 20
    # Only immediate proxy IPs listed here may supply a trusted X-Forwarded-For.
    # Comma-separated IPs or CIDRs; empty means use the direct peer address.
    trusted_proxy_ips: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    # Exact primary OAuth callback URI; Google Cloud Console must contain it.
    google_redirect_uri: str = ""
    # Comma-separated exact additional callback URIs; no wildcards or variants.
    google_allowed_redirect_uris: str = ""
    # Optional path to Google Cloud OAuth client JSON (Web application download).
    google_oauth_credentials_file: str = ""

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        """Normalize the environment and enforce secure production settings."""
        self.app_env = self.app_env.strip().lower()
        if self.app_env not in self._ALLOWED_APP_ENVS:
            raise ValueError(
                "APP_ENV must be one of: development, test, production."
            )

        if self.app_env == "production":
            # 1. Reject the development fallback secret
            dev_fallback = "dev-secret-change-in-production-min-32-chars-long"
            if self.session_secret == dev_fallback:
                raise ValueError(
                    "Production environment cannot use the development session secret."
                )

            # 2. Enforce minimum session secret strength
            if len(self.session_secret) < 32:
                raise ValueError("Production session secret must be at least 32 characters long.")

            # 3. Require secure session cookies
            if not self.session_cookie_secure:
                raise ValueError("Production environment requires session_cookie_secure=True.")

        return self

    # PostgreSQL (async driver) — see .env.example.

    # PostgreSQL (async driver) — see .env.example.
    database_url: str = _DEFAULT_DATABASE_URL
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle_seconds: int = 1800
    db_echo: bool = False

    # G03 — Document ingestion & chunking settings.
    # `data_dir` defaults to ../../data (relative to this file → project root/data).
    # Override DATA_DIR in .env for production/Docker deployments.
    data_dir: str = ""  # empty → resolved at runtime to <project_root>/data
    max_upload_bytes: int = 50 * 1024 * 1024  # 50 MB
    chunk_target_chars: int = 2000
    chunk_max_chars: int = 4000
    chunk_overlap_chars: int = 200

    # G04 — InLegalBERT + FAISS retrieval settings.
    embedding_model_name: str = "law-ai/InLegalBERT"
    embedding_device: str = "auto"
    embedding_batch_size: int = 16
    embedding_max_tokens: int = 512
    inlegalbert_backend: str = "onnx"
    vector_index_name: str = "legal_chunks"
    retrieval_default_top_k: int = 5
    retrieval_max_top_k: int = 25

    # G05-G07 — Neo4j graph and bounded hybrid retrieval.
    neo4j_uri: str = "bolt://localhost:7688"
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"
    graph_max_hops: int = 2
    graph_max_nodes: int = 100
    hybrid_vector_weight: float = 0.7
    hybrid_graph_weight: float = 0.3
    hybrid_dense_seed_top_k: int = 10
    hybrid_max_paths: int = 100
    hybrid_max_graph_candidates: int = 25
    hybrid_graph_timeout_seconds: float = 3.0

    # G08 — LLM legal QA (Phase 6).
    llm_provider: str = "openai_compatible"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_timeout_seconds: float = 30.0
    llm_max_output_tokens: int = 800
    llm_max_retries: int = 3
    qa_max_evidence: int = 5
    qa_max_context_chars: int = 24000
    qa_max_chunk_chars: int = 4000

    @model_validator(mode="after")
    def _apply_google_oauth_defaults(self) -> "Settings":
        if not self.google_redirect_uri:
            if self.app_env == "production":
                self.google_redirect_uri = "https://juris-ai-user.vercel.app/auth/google/callback"
            else:
                self.google_redirect_uri = f"http://{self.backend_host}:{self.backend_port}/auth/google/callback"

        if self.app_env == "production":
            allowed_parts = [p.strip() for p in self.google_allowed_redirect_uris.split(",") if p.strip()]
            if not allowed_parts or any(p.startswith("http://localhost") for p in allowed_parts):
                self.google_allowed_redirect_uris = (
                    "https://juris-ai-admin.vercel.app/admin/auth/google/callback,"
                    "https://juris-ai-user.vercel.app/auth/google/callback"
                )
            elif "https://juris-ai-admin.vercel.app/admin/auth/google/callback" not in allowed_parts and any("juris-ai-admin" in p for p in allowed_parts):
                allowed_parts.append("https://juris-ai-admin.vercel.app/admin/auth/google/callback")
                self.google_allowed_redirect_uris = ",".join(allowed_parts)
        elif not self.google_allowed_redirect_uris:
            self.google_allowed_redirect_uris = (
                "http://localhost:3001/admin/auth/google/callback,"
                "http://localhost:3002/auth/google/callback"
            )

        if not self.google_client_id or not self.google_client_secret:
            creds_path = (
                Path(self.google_oauth_credentials_file)
                if self.google_oauth_credentials_file.strip()
                else _DEFAULT_GOOGLE_OAUTH_JSON
            )
            creds = _load_google_credentials_from_file(creds_path.resolve())
            if creds is not None:
                self.google_client_id, self.google_client_secret = creds
        return self

    @model_validator(mode="after")
    def _validate_oauth_redirect_configuration(self) -> "Settings":
        """Validate configured OAuth callback URIs without normalizing them."""
        configured = [self.google_redirect_uri]
        configured.extend(
            value.strip()
            for value in self.google_allowed_redirect_uris.split(",")
            if value.strip()
        )
        for redirect_uri in configured:
            parsed = urlsplit(redirect_uri)
            if (
                "*" in redirect_uri
                or parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.username
                or parsed.password
                or parsed.fragment
                or parsed.query
                or parsed.path not in {"/auth/google/callback", "/admin/auth/google/callback"}
            ):
                raise ValueError("OAuth redirect URIs must be exact callback URLs.")
            if self.app_env == "production" and parsed.scheme != "https":
                raise ValueError("Production OAuth redirect URIs must use HTTPS.")
        return self

    @model_validator(mode="after")
    def _validate_hybrid_settings(self) -> "Settings":
        if self.rate_limit_window_seconds <= 0:
            raise ValueError("rate_limit_window_seconds must be greater than 0")
        for name, value in (
            ("rate_limit_auth_requests", self.rate_limit_auth_requests),
            ("rate_limit_qa_requests", self.rate_limit_qa_requests),
            ("rate_limit_upload_requests", self.rate_limit_upload_requests),
        ):
            if value <= 0:
                raise ValueError(f"{name} must be greater than 0")
        for proxy in self.trusted_proxy_ips.split(","):
            proxy = proxy.strip()
            if proxy:
                try:
                    ipaddress.ip_network(proxy, strict=False)
                except ValueError as exc:
                    raise ValueError(f"Invalid trusted proxy IP or CIDR: {proxy!r}") from exc
        if not 1 <= self.hybrid_dense_seed_top_k <= self.retrieval_max_top_k:
            raise ValueError(
                "hybrid_dense_seed_top_k must be between 1 and retrieval_max_top_k"
            )
        if not 1 <= self.hybrid_max_paths <= 500:
            raise ValueError("hybrid_max_paths must be between 1 and 500")
        if not 1 <= self.hybrid_max_graph_candidates <= 50:
            raise ValueError("hybrid_max_graph_candidates must be between 1 and 50")
        if self.hybrid_graph_timeout_seconds <= 0:
            raise ValueError("hybrid_graph_timeout_seconds must be greater than 0")
        for name, weight in (
            ("hybrid_vector_weight", self.hybrid_vector_weight),
            ("hybrid_graph_weight", self.hybrid_graph_weight),
        ):
            if not 0 <= weight <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if abs(self.hybrid_vector_weight + self.hybrid_graph_weight - 1.0) > 1e-6:
            raise ValueError("hybrid_vector_weight and hybrid_graph_weight must sum to 1")
        if self.llm_timeout_seconds <= 0:
            raise ValueError("llm_timeout_seconds must be greater than 0")
        if not 1 <= self.llm_max_output_tokens <= 8192:
            raise ValueError("llm_max_output_tokens must be between 1 and 8192")
        if not 1 <= self.qa_max_evidence <= self.retrieval_max_top_k:
            raise ValueError("qa_max_evidence must be between 1 and retrieval_max_top_k")
        if self.qa_max_context_chars < 1000:
            raise ValueError("qa_max_context_chars must be at least 1000")
        if not 500 <= self.qa_max_chunk_chars <= self.qa_max_context_chars:
            raise ValueError(
                "qa_max_chunk_chars must be between 500 and qa_max_context_chars"
            )
        return self

    @model_validator(mode="after")
    def _normalize_llm_settings(self) -> "Settings":
        self.llm_provider = (self.llm_provider or "").strip().lower()
        self.llm_base_url = (self.llm_base_url or "").strip()
        return self


@lru_cache
def _get_base_settings() -> Settings:
    """Return the cached base environment settings instance."""
    return Settings()


def get_settings() -> Settings:
    """Return the active settings instance with validated dynamic runtime overrides applied."""
    from app.core.dynamic_settings import get_runtime_settings

    return get_runtime_settings(_get_base_settings())


def get_data_dir() -> Path:
    """Resolve the data directory as an absolute Path.

    If ``data_dir`` is explicitly set in the environment / .env it is used as-is
    (resolved to an absolute path).  Otherwise defaults to ``<project_root>/data``.
    """
    cfg = get_settings()
    if cfg.data_dir:
        return Path(cfg.data_dir).resolve()
    return _PROJECT_ROOT / "data"
