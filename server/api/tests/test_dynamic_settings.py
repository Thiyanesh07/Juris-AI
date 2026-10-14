import pytest

from app.auth.password import hash_password
from app.core.config import get_settings
from app.core.dynamic_settings import (
    clear_runtime_overrides,
    is_masked_secret,
    validate_section_config,
)
from app.models import User, UserRole


@pytest.fixture(autouse=True)
def clean_overrides():
    clear_runtime_overrides()
    yield
    clear_runtime_overrides()


def test_is_masked_secret():
    assert is_masked_secret("********") is True
    assert is_masked_secret("••••••••••••••••••••••••••••••••") is True
    assert is_masked_secret("sk-...****") is True
    assert is_masked_secret("val...***") is True
    assert is_masked_secret("••••••••") is True

    assert is_masked_secret("sk-proj-real-valid-api-key") is False
    assert is_masked_secret("bolt://localhost:7687") is False
    assert is_masked_secret("") is False
    assert is_masked_secret(None) is False


def test_validate_section_config_bounds():
    base = get_settings()

    # 1. Valid retrieval update
    valid_retrieval = {
        "default_top_k": 8,
        "dense_weight": 0.6,
        "graph_weight": 0.4,
        "graph_depth": 4,
        "graph_candidate_limit": 30,
    }
    extracted = validate_section_config("RETRIEVAL", valid_retrieval, base)
    assert extracted["retrieval_default_top_k"] == 8
    assert extracted["hybrid_vector_weight"] == 0.6
    assert extracted["hybrid_graph_weight"] == 0.4
    assert extracted["graph_max_hops"] == 4
    assert extracted["hybrid_max_graph_candidates"] == 30

    # 2. Invalid weights not summing to 1.0
    with pytest.raises(ValueError, match="must sum to 1.0"):
        validate_section_config("RETRIEVAL", {"dense_weight": 0.7, "graph_weight": 0.4}, base)

    # 3. Out-of-bounds top-k
    with pytest.raises(ValueError, match="retrieval_default_top_k must be between 1 and"):
        validate_section_config("RETRIEVAL", {"default_top_k": 99}, base)

    # 4. Out-of-bounds LLM tokens
    with pytest.raises(ValueError, match="llm_max_output_tokens must be between 1 and"):
        validate_section_config("AI_LLM", {"max_output_tokens": 10000}, base)

    # 5. Out-of-bounds LLM timeout
    with pytest.raises(ValueError, match="llm_timeout_seconds must be between 1.0 and"):
        validate_section_config("AI_LLM", {"timeout": 0.2}, base)

    # 6. Disallowed keys are ignored and never extracted
    disallowed = {
        "api_key": "new_key",
        "embedding_model_name": "other-bert",
        "neo4j_uri": "bolt://evil:7687",
        "chunk_target_chars": 100,
    }
    extracted_disallowed = validate_section_config("AI_LLM", disallowed, base)
    assert len(extracted_disallowed) == 0


@pytest.mark.asyncio
async def test_dynamic_settings_api_and_runtime_consumption(client, session):
    admin = User(
        email="dyn_admin@jurisai.law",
        password_hash=hash_password("admin_pass"),
        role=UserRole.ADMIN,
    )
    session.add(admin)
    await session.commit()

    client.post(
        "/auth/login",
        json={"email": "dyn_admin@jurisai.law", "password": "admin_pass"},
    )

    # Baseline check
    initial_cfg = get_settings()
    assert initial_cfg.retrieval_default_top_k == 5

    # 1. Reject invalid retrieval weights with HTTP 422
    bad_res = client.put(
        "/settings/RETRIEVAL",
        json={"config": {"dense_weight": 0.8, "graph_weight": 0.5}},
        headers={"Origin": "http://localhost:5173"},
    )
    assert bad_res.status_code == 422
    assert "must sum to 1.0" in bad_res.json()["detail"]

    # Settings remain unchanged
    assert get_settings().retrieval_default_top_k == 5

    # 2. Successfully update RETRIEVAL settings
    res = client.put(
        "/settings/RETRIEVAL",
        json={
            "config": {
                "default_top_k": 10,
                "dense_weight": 0.75,
                "graph_weight": 0.25,
                "graph_depth": 4,
                "graph_candidate_limit": 35,
            }
        },
        headers={"Origin": "http://localhost:5173"},
    )
    assert res.status_code == 200

    # Runtime consumption check: get_settings() must immediately reflect new values
    active_cfg = get_settings()
    assert active_cfg.retrieval_default_top_k == 10
    assert active_cfg.hybrid_vector_weight == 0.75
    assert active_cfg.hybrid_graph_weight == 0.25
    assert active_cfg.graph_max_hops == 4
    assert active_cfg.hybrid_max_graph_candidates == 35

    # 3. Update AI_LLM safe parameters
    ai_res = client.put(
        "/settings/AI_LLM",
        json={
            "config": {
                "max_output_tokens": 1600,
                "llm_timeout_seconds": 55.0,
                "api_key": "********",  # Masked secret
            }
        },
        headers={"Origin": "http://localhost:5173"},
    )
    assert ai_res.status_code == 200

    updated_ai_cfg = get_settings()
    assert updated_ai_cfg.llm_max_output_tokens == 1600
    assert updated_ai_cfg.llm_timeout_seconds == 55.0

    # 4. Update INGESTION upload limit
    ingest_res = client.put(
        "/settings/INGESTION",
        json={"config": {"max_file_size_mb": 20}},
        headers={"Origin": "http://localhost:5173"},
    )
    assert ingest_res.status_code == 200
    assert get_settings().max_upload_bytes == 20 * 1024 * 1024

    # 5. Fallback behavior: Clearing overrides reverts cleanly to base environment defaults
    clear_runtime_overrides()
    reverted_cfg = get_settings()
    assert reverted_cfg.retrieval_default_top_k == 5
    assert reverted_cfg.llm_max_output_tokens == 800
    assert reverted_cfg.max_upload_bytes == 50 * 1024 * 1024


@pytest.mark.asyncio
async def test_load_persisted_settings(session):
    from app.core.dynamic_settings import load_persisted_settings
    from app.models import SystemSetting

    # Seed valid persisted setting in DB
    setting = SystemSetting(
        section="RETRIEVAL",
        config_json={
            "default_top_k": 7,
            "dense_weight": 0.7,
            "graph_weight": 0.3,
            "graph_depth": 3,
            "graph_candidate_limit": 25,
        },
    )
    session.add(setting)
    await session.commit()

    clear_runtime_overrides()
    assert get_settings().retrieval_default_top_k == 5

    overrides = await load_persisted_settings(session)
    assert overrides["retrieval_default_top_k"] == 7
    assert overrides["hybrid_vector_weight"] == 0.7
    assert overrides["hybrid_graph_weight"] == 0.3

    active_cfg = get_settings()
    assert active_cfg.retrieval_default_top_k == 7
    assert active_cfg.hybrid_vector_weight == 0.7
    assert active_cfg.hybrid_graph_weight == 0.3


@pytest.mark.asyncio
async def test_load_persisted_settings_safe_fallback(session):
    from app.core.dynamic_settings import load_persisted_settings
    from app.models import SystemSetting

    # Seed invalid persisted setting in DB (invalid weight sum)
    setting = SystemSetting(
        section="RETRIEVAL",
        config_json={
            "dense_weight": 0.9,
            "graph_weight": 0.5,
        },
    )
    session.add(setting)
    await session.commit()

    clear_runtime_overrides()
    # Invalid settings are skipped while defaults remain available.
    overrides = await load_persisted_settings(session)
    assert len(overrides) == 0

    active_cfg = get_settings()
    assert active_cfg.retrieval_default_top_k == 5
    assert active_cfg.hybrid_vector_weight == 0.7
    assert active_cfg.hybrid_graph_weight == 0.3


@pytest.mark.asyncio
async def test_load_persisted_settings_db_exception_handled():
    from unittest.mock import AsyncMock

    from app.core.dynamic_settings import load_persisted_settings

    mock_session = AsyncMock()
    mock_session.execute.side_effect = RuntimeError("Database connection failed")

    clear_runtime_overrides()
    # Must not raise an exception; must gracefully return empty overrides
    overrides = await load_persisted_settings(mock_session)
    assert overrides == {}
    assert get_settings().retrieval_default_top_k == 5
