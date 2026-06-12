"""Change detection + review workflow endpoints (Phase 3)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import dev_user
from app.briefs.review import (
    ReviewError,
    all_sections_resolved,
    approval_readiness,
    apply_section_action,
)
from app.changes.service import changes_since_last_brief
from app.db.base import get_db
from app.db.models import Brief, Claim, Watchlist
from app.services.audit import record_event

router = APIRouter(tags=["changes", "review"])


@router.get("/watchlists/{watchlist_id}/changes")
def get_changes(watchlist_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    wl = db.get(Watchlist, watchlist_id)
    if wl is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return changes_since_last_brief(db, wl)


class SectionActionIn(BaseModel):
    action: str = Field(description="accept | reject | edit | needs_source")
    content: str | None = Field(default=None, max_length=20000)


@router.patch("/briefs/{brief_id}/sections/{section_index}")
def review_section(
    brief_id: uuid.UUID,
    section_index: int,
    payload: SectionActionIn,
    db: Session = Depends(get_db),
) -> dict:
    brief = db.get(Brief, brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found")
    if brief.status == "approved":
        raise HTTPException(status_code=409, detail="Approved briefs are immutable")

    sections = brief.generated_draft.get("brief_sections", [])
    user = dev_user(db)
    try:
        brief.user_edits = apply_section_action(
            brief.user_edits or {},
            section_index=section_index,
            section_count=len(sections),
            action=payload.action,
            content=payload.content,
            actor=user.email,
        )
    except ReviewError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    brief.status = "in_review"
    db.commit()
    record_event(
        db,
        org_id=brief.org_id,
        actor_id=user.id,
        action=f"brief.section.{payload.action}",
        object_type="brief",
        object_id=str(brief.id),
        detail={"section_index": section_index},
    )
    return {
        "brief_id": str(brief.id),
        "status": brief.status,
        "section_index": section_index,
        "action": payload.action,
        "approvable": all_sections_resolved(brief.user_edits, len(sections)),
    }


@router.post("/briefs/{brief_id}/approve")
def approve_brief(brief_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    brief = db.get(Brief, brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found")
    if brief.status == "approved":
        return {"brief_id": str(brief.id), "status": "approved"}

    sections = brief.generated_draft.get("brief_sections", [])
    claims = list(db.scalars(select(Claim).where(Claim.brief_id == brief.id)))
    readiness = approval_readiness(brief.user_edits or {}, len(sections), claims)
    if not readiness["ready"]:
        raise HTTPException(
            status_code=409,
            detail=readiness,
        )

    from datetime import datetime, timezone

    user = dev_user(db)
    brief.status = "approved"
    brief.approved_by = user.id
    brief.approved_at = datetime.now(timezone.utc)
    db.commit()
    record_event(
        db,
        org_id=brief.org_id,
        actor_id=user.id,
        action="brief.approved",
        object_type="brief",
        object_id=str(brief.id),
        detail={"sections": len(sections), "claims": len(claims)},
    )
    return {"brief_id": str(brief.id), "status": "approved"}
