"""Dynamic runtime settings bridge with validation and safe environment fallback.

Enforces runtime-safe constraints for:
- Retrieval top-k
- Hybrid vector/graph weights (must sum to 1.0)
- Graph traversal depth
- Graph candidate limit
- LLM maximum output tokens
- LLM request timeout
- Maximum upload size

Disallowed for dynamic runtime modification (strictly environment-only or requires reindexing):
- API keys, OAuth, session security, database URIs, Neo4j connections,
  embedding models, vector dimensions, and chunking parameters.
"""

from __future__ import annotations

import copy
import logging
from typing import Any
from threading import Lock

from app.core.config import Settings

logger = logging.getLogger(__name__)

# Thread-safe in-memory store of validated runtime overrides
_OVERRIDES_LOCK = Lock()
_RUNTIME_OVERRIDES: dict[str, Any] = {}

# Allowed runtime-safe keys and their canonical Settings attributes
RUNTIME_SAFE_KEY_MAP: dict[str, str] = {
    # Retrieval top-k
    "retrieval_default_top_k": "retrieval_default_top_k",
    "default_top_k": "retrieval_default_top_k",
    "vectorTopK": "retrieval_default_top_k",
    # Hybrid fusion weights
    "hybrid_vector_weight": "hybrid_vector_weight",
    "dense_weight": "hybrid_vector_weight",
    "hybridWeight": "hybrid_vector_weight",
    "hybrid_graph_weight": "hybrid_graph_weight",
    "graph_weight": "hybrid_graph_weight",
    "graphWeight": "hybrid_graph_weight",
    # Graph traversal depth
    "graph_max_hops": "graph_max_hops",
    "max_traversal_depth": "graph_max_hops",
    "default_traversal_depth": "graph_max_hops",
    "graph_depth": "graph_max_hops",
    "graphDepth": "graph_max_hops",
    # Graph candidate limit
    "hybrid_max_graph_candidates": "hybrid_max_graph_candidates",
    "graph_candidate_limit": "hybrid_max_graph_candidates",
    "graphCandidateLimit": "hybrid_max_graph_candidates",
    # LLM generation parameters
    "llm_max_output_tokens": "llm_max_output_tokens",
    "max_output_tokens": "llm_max_output_tokens",
    "maxOutputTokens": "llm_max_output_tokens",
    "llm_timeout_seconds": "llm_timeout_seconds",
    "timeout": "llm_timeout_seconds",
    # Ingestion upload limit
    "max_upload_bytes": "max_upload_bytes",
    "max_file_size_mb": "max_upload_bytes",
    "maxFileSizeMb": "max_upload_bytes",
}

DISALLOWED_DYNAMIC_KEYS: set[str] = {
    "api_key",
    "llm_api_key",
    "llm_provider",
    "llm_base_url",
    "embedding_model_name",
    "embedding_dim",
    "inlegalbert_backend",
    "embedding_device",
    "vector_index_name",
    "neo4j_uri",
    "neo4j_username",
    "neo4j_password",
    "neo4j_database",
    "database_url",
    "session_secret",
    "session_cookie_secure",
    "session_max_age_seconds",
    "google_client_id",
    "google_client_secret",
    "google_redirect_uri",
    "chunk_target_chars",
    "chunk_max_chars",
    "chunk_overlap_chars",
}


def is_masked_secret(value: Any) -> bool:
    """Return True if string represents a masked credential placeholder."""
    if not isinstance(value, str):
        return False
    trimmed = value.strip()
    if not trimmed:
        return False
    if all(ch in ("*", "•") for ch in trimmed):
        return True
    if "••••" in trimmed:
        return True
    if len(trimmed) > 4 and "...***" in trimmed:
        return True
    return False


def validate_runtime_override(canonical_key: str, value: Any, current_settings: Settings) -> Any:
    """Validate bounds and type for a single runtime-safe override."""
    if canonical_key == "retrieval_default_top_k":
        try:
            val = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"retrieval_default_top_k must be an integer, got {value!r}") from exc
        if not 1 <= val <= current_settings.retrieval_max_top_k:
            raise ValueError(
                f"retrieval_default_top_k must be between 1 and {current_settings.retrieval_max_top_k}, got {val}"
            )
        return val

    elif canonical_key in ("hybrid_vector_weight", "hybrid_graph_weight"):
        try:
            val = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{canonical_key} must be a float, got {value!r}") from exc
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"{canonical_key} must be between 0.0 and 1.0, got {val}")
        return round(val, 4)

    elif canonical_key == "graph_max_hops":
        try:
            val = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"graph_max_hops must be an integer, got {value!r}") from exc
        if not 1 <= val <= 10:
            raise ValueError(f"graph_max_hops must be between 1 and 10, got {val}")
        return val

    elif canonical_key == "hybrid_max_graph_candidates":
        try:
            val = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"hybrid_max_graph_candidates must be an integer, got {value!r}") from exc
        if not 1 <= val <= 50:
            raise ValueError(f"hybrid_max_graph_candidates must be between 1 and 50, got {val}")
        return val

    elif canonical_key == "llm_max_output_tokens":
        try:
            val = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"llm_max_output_tokens must be an integer, got {value!r}") from exc
        if not 1 <= val <= 8192:
            raise ValueError(f"llm_max_output_tokens must be between 1 and 8192, got {val}")
        return val

    elif canonical_key == "llm_timeout_seconds":
        try:
            val = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"llm_timeout_seconds must be a float, got {value!r}") from exc
        if not 1.0 <= val <= 300.0:
            raise ValueError(f"llm_timeout_seconds must be between 1.0 and 300.0, got {val}")
        return round(val, 2)

    elif canonical_key == "max_upload_bytes":
        try:
            val = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"max_upload_bytes must be an integer, got {value!r}") from exc
        # Allow specifying in MB if <= 500
        if 1 <= val <= 500:
            val = val * 1024 * 1024
        if not 1024 * 1024 <= val <= 500 * 1024 * 1024:
            raise ValueError(
                f"max_upload_bytes must be between 1 MB (1048576) and 500 MB (524288000), got {val}"
            )
        return val

    raise ValueError(f"Setting key {canonical_key!r} is not an approved runtime-safe setting.")


def validate_section_config(
    section: str, config: dict[str, Any], current_settings: Settings
) -> dict[str, Any]:
    """Validate incoming section updates, rejecting invalid bounds, types, or weight sums.

    Returns the extracted runtime overrides dictionary.
    """
    section_upper = section.upper()
    extracted_overrides: dict[str, Any] = {}

    for raw_key, raw_val in config.items():
        if raw_key in DISALLOWED_DYNAMIC_KEYS:
            logger.debug(
                "Ignoring dynamic modification attempt for environment-only key %s in section %s",
                raw_key,
                section_upper,
            )
            continue

        canonical_key = RUNTIME_SAFE_KEY_MAP.get(raw_key)
        if canonical_key:
            validated_val = validate_runtime_override(canonical_key, raw_val, current_settings)
            extracted_overrides[canonical_key] = validated_val

    # Enforce hybrid weights sum constraint if either weight is provided
    if "hybrid_vector_weight" in extracted_overrides or "hybrid_graph_weight" in extracted_overrides:
        vec_w = extracted_overrides.get(
            "hybrid_vector_weight", current_settings.hybrid_vector_weight
        )
        graph_w = extracted_overrides.get(
            "hybrid_graph_weight", current_settings.hybrid_graph_weight
        )
        if abs(vec_w + graph_w - 1.0) > 1e-4:
            raise ValueError(
                f"hybrid_vector_weight ({vec_w}) and hybrid_graph_weight ({graph_w}) must sum to 1.0 (got {vec_w + graph_w:.4f})"
            )
        extracted_overrides["hybrid_vector_weight"] = vec_w
        extracted_overrides["hybrid_graph_weight"] = graph_w

    return extracted_overrides


def apply_runtime_overrides(overrides: dict[str, Any]) -> None:
    """Thread-safely apply validated runtime overrides to the in-memory store."""
    with _OVERRIDES_LOCK:
        _RUNTIME_OVERRIDES.update(overrides)


def get_runtime_overrides() -> dict[str, Any]:
    """Return a copy of the current active runtime overrides."""
    with _OVERRIDES_LOCK:
        return copy.deepcopy(_RUNTIME_OVERRIDES)


def clear_runtime_overrides() -> None:
    """Clear all active runtime overrides (for testing and resets)."""
    with _OVERRIDES_LOCK:
        _RUNTIME_OVERRIDES.clear()


def get_runtime_settings(base_settings: Settings | None = None) -> Settings:
    """Return a Settings instance with all approved runtime overrides applied.

    Falls back safely to base environment settings on any error.
    """
    from app.core.config import Settings as SettingsCls

    base = base_settings or SettingsCls()
    with _OVERRIDES_LOCK:
        overrides = copy.deepcopy(_RUNTIME_OVERRIDES)

    if not overrides:
        return base

    try:
        # Create updated model instance
        updated = base.model_copy(update=overrides)
        return updated
    except Exception as exc:
        logger.warning(
            "Failed to overlay dynamic settings overrides %r onto Settings: %s. Falling back to base settings.",
            overrides,
            exc,
        )
        return base


async def load_persisted_settings(session: Any, base_settings: Settings | None = None) -> dict[str, Any]:
    """Query system_settings table and apply validated runtime-safe overrides.

    If the database is unavailable, table does not exist, or records are invalid,
    logs a warning and safely retains base settings without crashing.
    """
    from sqlalchemy import select
    from app.models import SystemSetting
    from app.core.config import _get_base_settings

    base = base_settings or _get_base_settings()
    accumulated_overrides: dict[str, Any] = {}

    try:
        stmt = select(SystemSetting)
        result = await session.execute(stmt)
        records = result.scalars().all()
        for record in records:
            if not record.config_json or not isinstance(record.config_json, dict):
                continue
            try:
                valid = validate_section_config(record.section, record.config_json, base)
                accumulated_overrides.update(valid)
            except Exception as val_err:
                logger.warning(
                    "Skipping invalid persisted settings in section %s: %s",
                    record.section,
                    val_err,
                )
        if accumulated_overrides:
            apply_runtime_overrides(accumulated_overrides)
            logger.info("Loaded persisted runtime settings overrides: %s", list(accumulated_overrides.keys()))
    except Exception as exc:
        logger.warning(
            "Failed to load persisted settings from system_settings: %s. Using environment defaults.",
            exc,
        )

    return accumulated_overrides
