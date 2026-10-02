"""Audit Logging Service (Phase 16).

Provides append-only structured audit logging for authentication, user management,
document operations, ingestion, knowledge graph actions, validation decisions, settings changes,
and security events.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_event import SystemEvent

logger = logging.getLogger(__name__)


async def log_audit_event(
    session: AsyncSession,
    *,
    category: str,
    action: str,
    result: str = "SUCCESS",
    severity: str = "INFO",
    actor_id: UUID | None = None,
    target_resource: str | None = None,
    description: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> SystemEvent:
    """Log an append-only audit event to PostgreSQL system_events table."""
    payload: dict[str, Any] = {
        "category": category,
        "action": action,
        "result": result,
        "severity": severity,
        "target_resource": target_resource,
        "description": description or f"{category}.{action} ({result})",
        "ip_address": ip_address,
        "user_agent": user_agent,
    }
    if before_state is not None:
        payload["before_state"] = before_state
    if after_state is not None:
        payload["after_state"] = after_state
    if extra_metadata is not None:
        payload["extra"] = extra_metadata

    event = SystemEvent(
        event_type=f"{category.upper()}_{action.upper()}",
        actor_id=actor_id,
        event_metadata=payload,
    )
    session.add(event)
    await session.commit()
    logger.info(f"Audit event logged: {event.event_type} by actor={actor_id}")
    return event
