"""Shared API dependencies.

dev_user is the single-user placeholder until OIDC + PKCE lands (Phase 5 gate) —
every review/feedback action still records WHO acted, so the audit trail shape
is production-correct from day one.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Organization, User


def dev_user(db: Session) -> User:
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
