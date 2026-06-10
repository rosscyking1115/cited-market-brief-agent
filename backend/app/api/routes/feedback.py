"""Analyst feedback capture (plan §3: useful / not_useful / wrong / needs_source).

Feedback rows feed the eval datasets (wrong-source rate, edit-distance analysis).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Brief, Claim, Feedback, Organization, User
from app.services.audit import record_event
from sqlalchemy import select

router = APIRouter(tags=["feedback"])

ALLOWED_KINDS = {"useful", "not_useful", "wrong", "needs_source"}


class FeedbackIn(BaseModel):
    brief_id: uuid.UUID | None = None
    claim_id: uuid.UUID | None = None
    kind: str = Field(description="useful | not_useful | wrong | needs_source")
    note: str = Field(default="", max_length=2000)


def _dev_user(db: Session) -> User:
    """Single-user placeholder until OIDC lands (Phase 5)."""
    user = db.scalar(select(User).where(User.email == "dev@ledgerbrief.local"))
    if user is None:
        org = db.scalar(select(Organization).where(Organization.name == "dev-org"))
        if org is None:
            org = Organization(name="dev-org")
            db.add(org)
            db.flush()
        user = User(org_id=org.id, email="dev@ledgerbrief.local", display_name="Dev Analyst")
        db.add(user)
        db.commit()
    return user


@router.post("/feedback", status_code=201)
def create_feedback(payload: FeedbackIn, db: Session = Depends(get_db)) -> dict:
    if payload.kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=422, detail=f"kind must be one of {sorted(ALLOWED_KINDS)}")
    if payload.brief_id is None and payload.claim_id is None:
        raise HTTPException(status_code=422, detail="brief_id or claim_id is required")

    org_id = None
    if payload.claim_id is not None:
        claim = db.get(Claim, payload.claim_id)
        if claim is None:
            raise HTTPException(status_code=404, detail="Claim not found")
        org_id = claim.org_id
        if payload.brief_id is None:
            payload.brief_id = claim.brief_id
    if payload.brief_id is not None and org_id is None:
        brief = db.get(Brief, payload.brief_id)
        if brief is None:
            raise HTTPException(status_code=404, detail="Brief not found")
        org_id = brief.org_id

    user = _dev_user(db)
    fb = Feedback(
        org_id=org_id,
        claim_id=payload.claim_id,
        brief_id=payload.brief_id,
        user_id=user.id,
        kind=payload.kind,
        note=payload.note,
    )
    db.add(fb)
    db.commit()
    record_event(
        db,
        org_id=org_id,
        actor_id=user.id,
        action="feedback.created",
        object_type="claim" if payload.claim_id else "brief",
        object_id=str(payload.claim_id or payload.brief_id),
        detail={"kind": payload.kind},
    )
    return {"feedback_id": str(fb.id), "kind": fb.kind}
