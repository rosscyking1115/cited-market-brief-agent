"""Core data model (docs/PRODUCTION_PLAN.md §6).

Conventions:
- UUID primary keys, timezone-aware timestamps.
- Every org-scoped table carries org_id (RLS enforcement lands in Phase 5; the
  column and FK are mandatory from day one so policies can be applied without rewrites).
- chunks carries both the pgvector embedding and a Postgres FTS tsvector — single
  write path for RRF hybrid retrieval (no external search engine at MVP).
"""

import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="pilot")
    retention_days: Mapped[int] = mapped_column(Integer, default=365)
    created_at: Mapped[datetime] = _created_at()


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(50), default="analyst")  # analyst|reviewer|admin
    mfa_enrolled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = _created_at()


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[uuid.UUID] = _uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tickers: Mapped[list] = mapped_column(JSON, default=list)
    sectors: Mapped[list] = mapped_column(JSON, default=list)
    macro_series: Mapped[list] = mapped_column(JSON, default=list)  # FRED series ids
    schedule_cron: Mapped[str | None] = mapped_column(String(100))
    template: Mapped[str] = mapped_column(String(100), default="morning_brief")
    created_at: Mapped[datetime] = _created_at()


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = _uuid_pk()
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    cik: Mapped[str | None] = mapped_column(String(20), index=True)
    lei: Mapped[str | None] = mapped_column(String(40))
    exchange: Mapped[str | None] = mapped_column(String(40))
    sector: Mapped[str | None] = mapped_column(String(120))
    aliases: Mapped[list] = mapped_column(JSON, default=list)


class SourceType(str, enum.Enum):
    SEC_FILING = "sec_filing"
    MACRO_SERIES = "macro_series"
    IR_PAGE = "ir_page"
    RSS = "rss"
    USER_LICENSED = "user_licensed"


class TrustTier(str, enum.Enum):
    """RAG-poisoning control: non-government sources land in QUARANTINE before promotion."""

    OFFICIAL = "official"        # SEC, FRED, BLS, BEA, Census
    QUARANTINE = "quarantine"    # IR pages, RSS — pending integrity checks
    PROMOTED = "promoted"


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = _uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    publisher: Mapped[str] = mapped_column(String(255), default="")
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    trust_tier: Mapped[TrustTier] = mapped_column(Enum(TrustTier), default=TrustTier.QUARANTINE)
    license_note: Mapped[str] = mapped_column(Text, default="")
    access_method: Mapped[str] = mapped_column(String(50), default="api")
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_object_key: Mapped[str] = mapped_column(Text, nullable=False)  # per-tenant S3 prefix


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = _uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), index=True)
    doc_type: Mapped[str] = mapped_column(String(50))  # 10-K | 10-Q | 8-K | ir_pdf | ...
    filing_accession: Mapped[str | None] = mapped_column(String(40), index=True)
    publication_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = _created_at()

    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = _uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), index=True)
    page: Mapped[int | None] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(255))
    span_start: Mapped[int | None] = mapped_column(Integer)
    span_end: Mapped[int | None] = mapped_column(Integer)
    is_table: Mapped[bool] = mapped_column(Boolean, default=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(settings.embedding_dimensions), nullable=True)
    fts = mapped_column(TSVECTOR, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="chunks")

    __table_args__ = (
        # HNSW index added in migration once pgvector >=0.8.2 confirmed:
        # CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)
        Index("ix_chunks_fts", "fts", postgresql_using="gin"),
    )


class TimeSeries(Base):
    __tablename__ = "time_series"

    id: Mapped[uuid.UUID] = _uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    provider: Mapped[str] = mapped_column(String(50), default="fred")
    series_id: Mapped[str] = mapped_column(String(120), index=True)
    units: Mapped[str] = mapped_column(String(120), default="")
    frequency: Mapped[str] = mapped_column(String(120), default="")
    vintage: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # ALFRED awareness
    observations: Mapped[dict] = mapped_column(JSON, default=dict)


class ClaimType(str, enum.Enum):
    FILING_CHANGE = "filing_change"
    MACRO_DELTA = "macro_delta"
    RISK = "risk"
    CATALYST = "catalyst"
    FACTUAL_SUMMARY = "factual_summary"


class SupportStatus(str, enum.Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    FLAGGED = "flagged"
    REMOVED = "removed"


class Brief(Base):
    __tablename__ = "briefs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    watchlist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("watchlists.id"), index=True)
    template: Mapped[str] = mapped_column(String(100), default="morning_brief")
    generated_draft: Mapped[dict] = mapped_column(JSON, default=dict)  # structured JSON output
    user_edits: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="draft")  # draft|in_review|approved
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created_at()

    claims: Mapped[list["Claim"]] = relationship(back_populates="brief")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = _uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    brief_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("briefs.id"), index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[ClaimType] = mapped_column(Enum(ClaimType), nullable=False)
    confidence: Mapped[str] = mapped_column(String(10), default="medium")  # high|medium|low
    support_status: Mapped[SupportStatus] = mapped_column(
        Enum(SupportStatus), default=SupportStatus.UNSUPPORTED
    )
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)

    brief: Mapped["Brief"] = relationship(back_populates="claims")
    citations: Mapped[list["Citation"]] = relationship(back_populates="claim")


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[uuid.UUID] = _uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id"), index=True)
    chunk_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chunks.id"), index=True)
    span_start: Mapped[int | None] = mapped_column(Integer)
    span_end: Mapped[int | None] = mapped_column(Integer)
    source_url: Mapped[str] = mapped_column(Text, default="")
    evidence_quote: Mapped[str] = mapped_column(Text, default="")
    validator_status: Mapped[str] = mapped_column(String(20), default="pending")  # pass|fail|pending
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    claim: Mapped["Claim"] = relationship(back_populates="citations")


class Export(Base):
    __tablename__ = "exports"

    id: Mapped[uuid.UUID] = _uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    brief_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("briefs.id"), index=True)
    fmt: Mapped[str] = mapped_column(String(20))  # md|pdf|pptx|xlsx|json_manifest
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    ai_marking_embedded: Mapped[bool] = mapped_column(Boolean, default=True)  # EU AI Act Art. 50
    created_at: Mapped[datetime] = _created_at()


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = _uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    claim_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("claims.id"))
    brief_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("briefs.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(20))  # useful|not_useful|wrong|needs_source
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = _created_at()


class AuditEvent(Base):
    """Append-only. No UPDATE/DELETE grants in production (enforced via DB role in Phase 5)."""

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = _uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(String(50), default="")
    object_id: Mapped[str] = mapped_column(String(64), default="")
    model_provider: Mapped[str] = mapped_column(String(50), default="")
    model_version: Mapped[str] = mapped_column(String(100), default="")
    prompt_version: Mapped[str] = mapped_column(String(50), default="")
    source_ids: Mapped[list] = mapped_column(JSON, default=list)
    policy_flags: Mapped[list] = mapped_column(JSON, default=list)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = _created_at()


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    dataset: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), default="")
    model_version: Mapped[str] = mapped_column(String(100), default="")
    scores: Mapped[dict] = mapped_column(JSON, default=dict)
    failures: Mapped[list] = mapped_column(JSON, default=list)
    citation_precision: Mapped[float | None] = mapped_column(Float)
    citation_recall: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = _created_at()
