"""SQLAlchemy 2.0 engine, session factory, and declarative base.

Engine creation is lazy: importing this module never touches the database driver,
which keeps unit tests and tooling import-clean.

Tenant isolation (Phase 5 gate): every org-scoped table carries org_id and will be
covered by Postgres Row-Level Security keyed by a session variable
(SET app.current_org_id = ...). Vector/FTS queries inherit RLS — never rely on
query-side filters alone. See docs/PRODUCTION_PLAN.md §9.
"""

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(), autoflush=False, expire_on_commit=False
        )
    return _session_factory


def get_db(request: Request) -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped session.

    When auth resolved a tenant (require_auth sets request.state.org_id), the RLS
    GUC is set on this session BEFORE any query — Postgres policies then scope
    every read/write, including vector and FTS queries, to the tenant."""
    db = get_sessionmaker()()
    try:
        org_id = getattr(request.state, "org_id", None)
        if org_id is not None:
            from app.db.rls import set_org_context  # local import avoids cycle

            set_org_context(db, org_id)
        yield db
    finally:
        db.close()
