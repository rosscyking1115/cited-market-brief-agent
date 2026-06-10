"""Watchlist CRUD (Phase 1).

AuthN/AuthZ note: org scoping is currently a single dev-org placeholder. Phase 5
replaces this with OIDC+PKCE auth and Postgres RLS keyed by the session org —
do NOT ship multi-tenant before that gate (plan §9).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Organization, Watchlist
from app.schemas import WatchlistCreate, WatchlistOut, WatchlistUpdate
from app.services.audit import record_event

router = APIRouter(prefix="/watchlists", tags=["watchlists"])

DEV_ORG_NAME = "dev-org"


def _dev_org(db: Session) -> Organization:
    org = db.scalar(select(Organization).where(Organization.name == DEV_ORG_NAME))
    if org is None:
        org = Organization(name=DEV_ORG_NAME)
        db.add(org)
        db.commit()
    return org


@router.post("", response_model=WatchlistOut, status_code=201)
def create_watchlist(payload: WatchlistCreate, db: Session = Depends(get_db)) -> Watchlist:
    org = _dev_org(db)
    wl = Watchlist(org_id=org.id, **payload.model_dump())
    db.add(wl)
    db.commit()
    record_event(
        db,
        org_id=org.id,
        action="watchlist.created",
        object_type="watchlist",
        object_id=str(wl.id),
        detail={"name": wl.name, "tickers": wl.tickers},
    )
    return wl


@router.get("", response_model=list[WatchlistOut])
def list_watchlists(db: Session = Depends(get_db)) -> list[Watchlist]:
    org = _dev_org(db)
    return list(db.scalars(select(Watchlist).where(Watchlist.org_id == org.id)))


@router.get("/{watchlist_id}", response_model=WatchlistOut)
def get_watchlist(watchlist_id: uuid.UUID, db: Session = Depends(get_db)) -> Watchlist:
    wl = db.get(Watchlist, watchlist_id)
    if wl is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return wl


@router.patch("/{watchlist_id}", response_model=WatchlistOut)
def update_watchlist(
    watchlist_id: uuid.UUID, payload: WatchlistUpdate, db: Session = Depends(get_db)
) -> Watchlist:
    wl = db.get(Watchlist, watchlist_id)
    if wl is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(wl, field, value)
    db.commit()
    record_event(
        db,
        org_id=wl.org_id,
        action="watchlist.updated",
        object_type="watchlist",
        object_id=str(wl.id),
    )
    return wl


@router.delete("/{watchlist_id}", status_code=204)
def delete_watchlist(watchlist_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    wl = db.get(Watchlist, watchlist_id)
    if wl is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    org_id = wl.org_id
    db.delete(wl)
    db.commit()
    record_event(
        db,
        org_id=org_id,
        action="watchlist.deleted",
        object_type="watchlist",
        object_id=str(watchlist_id),
    )
