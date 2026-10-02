"""System Settings API Routes (Phase 16).

Provides persistent backend configuration management by section with secret masking
and audit event generation.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.core.config import get_settings
from app.db.session import get_session
from app.models import SystemSetting, User
from app.schemas.settings import AllSettingsResponse, SettingSectionResponse, SettingUpdateRequest
from app.services.audit import log_audit_event

router = APIRouter(prefix="/settings", tags=["settings"])

# Default default configurations per section
_DEFAULT_SETTINGS: dict[str, dict] = {
    "GENERAL": {
        "platform_name": "Juris AI LegalGraph",
        "maintenance_mode": False,
        "max_query_length": 1000,
        "support_email": "support@jurisai.law",
    },
    "AI_LLM": {
        "provider": "google_genai",
        "model": "gemini-2.5-flash",
        "temperature": 0.2,
        "max_output_tokens": 2048,
        "llm_timeout_seconds": 45.0,
        "api_key": "********",  # Masked
    },
    "EMBEDDINGS": {
        "model_name": "law-ai/InLegalBERT",
        "embedding_dim": 768,
        "pooling": "mean",
    },
    "RETRIEVAL": {
        "default_top_k": 5,
        "dense_weight": 0.5,
        "graph_weight": 0.5,
        "fusion_algorithm": "rrf",
    },
    "INGESTION": {
        "chunk_size": 512,
        "chunk_overlap": 64,
        "enable_ocr_fallback": False,
    },
    "KNOWLEDGE_GRAPH": {
        "neo4j_uri": "bolt://localhost:7687",
        "neo4j_database": "neo4j",
        "max_traversal_depth": 5,
        "default_traversal_depth": 3,
    },
    "SECURITY": {
        "session_ttl_hours": 24,
        "require_mfa": False,
        "max_login_attempts": 5,
    },
}


def _mask_sensitive_keys(config: dict) -> dict:
    """Mask sensitive API keys, passwords, and secret tokens before returning to client."""
    masked = dict(config)
    for key in masked:
        if any(secret_term in key.lower() for secret_term in ("key", "secret", "password", "token")):
            val = str(masked[key])
            if val and val != "********":
                masked[key] = f"{val[:3]}...****" if len(val) > 6 else "********"
    return masked


@router.get("", response_model=AllSettingsResponse)
async def get_all_settings(
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> AllSettingsResponse:
    """Retrieve all configuration sections with secret values masked."""
    db_settings = (await session.scalars(select(SystemSetting))).all()
    setting_map = {s.section: s.config_json for s in db_settings}

    sections: dict[str, dict] = {}
    for section_name, default_cfg in _DEFAULT_SETTINGS.items():
        cfg = setting_map.get(section_name, default_cfg)
        sections[section_name] = _mask_sensitive_keys(cfg)

    return AllSettingsResponse(sections=sections)


@router.get("/{section}", response_model=SettingSectionResponse)
async def get_setting_section(
    section: str,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> SettingSectionResponse:
    """Retrieve configuration for a specific section."""
    section_upper = section.upper()
    setting = await session.scalar(select(SystemSetting).where(SystemSetting.section == section_upper))

    config = setting.config_json if setting else _DEFAULT_SETTINGS.get(section_upper, {})
    if not config and section_upper not in _DEFAULT_SETTINGS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Settings section '{section}' not found")

    return SettingSectionResponse(
        section=section_upper,
        config=_mask_sensitive_keys(config),
        updated_at=setting.updated_at if setting else None,
        updated_by_id=setting.updated_by_id if setting else None,
    )


@router.put("/{section}", response_model=SettingSectionResponse)
async def update_setting_section(
    section: str,
    body: SettingUpdateRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> SettingSectionResponse:
    """Update configuration for a specific section (ADMIN/SUPER_ADMIN only)."""
    section_upper = section.upper()
    setting = await session.scalar(select(SystemSetting).where(SystemSetting.section == section_upper))

    before_state = setting.config_json if setting else _DEFAULT_SETTINGS.get(section_upper, {})

    if not setting:
        setting = SystemSetting(
            section=section_upper,
            config_json=body.config,
            updated_by_id=current_user.id,
        )
        session.add(setting)
    else:
        setting.config_json = body.config
        setting.updated_by_id = current_user.id

    await session.commit()
    await session.refresh(setting)

    await log_audit_event(
        session,
        category="SETTINGS",
        action="UPDATE",
        result="SUCCESS",
        severity="WARNING",
        actor_id=current_user.id,
        target_resource=f"settings:{section_upper}",
        description=f"Updated system settings for section {section_upper}",
        before_state=_mask_sensitive_keys(before_state),
        after_state=_mask_sensitive_keys(setting.config_json),
    )

    return SettingSectionResponse(
        section=setting.section,
        config=_mask_sensitive_keys(setting.config_json),
        updated_at=setting.updated_at,
        updated_by_id=setting.updated_by_id,
    )
