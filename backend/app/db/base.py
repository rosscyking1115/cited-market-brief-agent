"""SQLAlchemy 2.0 engine, session factory, and declarative base.

Engine creation is lazy: importing this module never touches the database driver,
which keeps unit tests and tooling import-clean.

Tenant isolation (Phase 5 gate): every org-scoped table carries org_id and will be
covered by Postgres Row-Level Security keyed by a session variable
(SET app.current_org_id = ...). Vector/FTS queries inherit RLS — never rely on
query-side filters alone. See docs/PRODUCTION_PLAN.md §9.
"""

from collections.abc import Generator

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


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped session."""
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()
