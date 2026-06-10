"""Append-only audit logging (FINRA 2026 GenAI expectations; plan §9).

Every ingestion, model call, generation, validation, export, and approval emits an
event. Model provider/version and prompt version are mandatory on LLM actions.
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AuditEvent


def record_event(
    db: Session,
    *,
    org_id: uuid.UUID,
    action: str,
    actor_id: uuid.UUID | None = None,
    object_type: str = "",
    object_id: str = "",
    model_provider: str = "",
    model_version: str = "",
    prompt_version: str = "",
    source_ids: list[str] | None = None,
    policy_flags: list[str] | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        org_id=org_id,
        actor_id=actor_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        model_provider=model_provider,
        model_version=model_version,
        prompt_version=prompt_version,
        source_ids=source_ids or [],
        policy_flags=policy_flags or [],
        detail=detail or {},
    )
    db.add(event)
    db.commit()
    return event
