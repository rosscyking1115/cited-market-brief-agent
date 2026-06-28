"""Ingestion + brief generation endpoints (Phase 1: synchronous local slice).

Long-running work moves to Hatchet workflows when schedules land; the service
functions are already shaped for that hand-off.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.briefs.service import export_brief_markdown, generate_and_store_brief
from app.briefs.translation import (
    LOCALE_NAMES,
    cached_translation,
    translation_model,
    with_cached_translation,
)
from app.core.config import settings
from app.db.base import get_db
from app.db.models import Brief, Chunk, Citation, Claim, Document, Source, SupportStatus, Watchlist
from app.ingestion.pipeline import run_ingestion
from app.services.audit import record_event

router = APIRouter(tags=["briefs"])
logger = logging.getLogger(__name__)


def _get_watchlist(db: Session, watchlist_id: uuid.UUID) -> Watchlist:
    wl = db.get(Watchlist, watchlist_id)
    if wl is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return wl


def _claims_in_draft_order(db: Session, brief: Brief) -> list[Claim]:
    """Return stored Claim rows in the same order as generated_draft['claims'].

    Claim IDs are UUIDs, so ordering by ID can scramble the C-000/C-001 numbers
    that the brief prose references as [#N].
    """
    remaining = list(db.scalars(select(Claim).where(Claim.brief_id == brief.id)))
    ordered: list[Claim] = []
    for draft_claim in brief.generated_draft.get("claims", []):
        text = draft_claim.get("text")
        match = next((claim for claim in remaining if claim.text == text), None)
        if match is not None:
            ordered.append(match)
            remaining.remove(match)
    ordered.extend(remaining)
    return ordered


def _first_sentence(text: str) -> str:
    normalized = " ".join(text.split())
    for sep in (". ", "? ", "! "):
        if sep in normalized:
            return normalized.split(sep, 1)[0].strip() + sep.strip()
    return normalized[:320].strip()


@router.post("/watchlists/{watchlist_id}/ingest")
async def ingest(watchlist_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    wl = _get_watchlist(db, watchlist_id)
    try:
        counts = await run_ingestion(db, wl)
    except RuntimeError as exc:  # missing SEC_USER_AGENT / FRED_API_KEY configuration
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"watchlist_id": str(watchlist_id), **counts}


@router.post("/watchlists/{watchlist_id}/briefs", status_code=201)
def generate(watchlist_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    wl = _get_watchlist(db, watchlist_id)
    brief = generate_and_store_brief(db, wl)
    draft = brief.generated_draft
    return {
        "brief_id": str(brief.id),
        "status": brief.status,
        "sections": len(draft.get("brief_sections", [])),
        "claims": len(draft.get("claims", [])),
    }


@router.get("/briefs/{brief_id}")
def get_brief(brief_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    brief = db.get(Brief, brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found")
    return {
        "brief_id": str(brief.id),
        "watchlist_id": str(brief.watchlist_id),
        "status": brief.status,
        "created_at": brief.created_at.isoformat(),
        "draft": brief.generated_draft,
    }


@router.get("/briefs/{brief_id}/markdown", response_class=PlainTextResponse)
def get_brief_markdown(brief_id: uuid.UUID, db: Session = Depends(get_db)) -> str:
    brief = db.get(Brief, brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found")
    wl = _get_watchlist(db, brief.watchlist_id)
    md, _manifest = export_brief_markdown(db, brief, wl)
    return md


@router.get("/briefs/{brief_id}/translations/{locale}")
def get_brief_translation(brief_id: uuid.UUID, locale: str, db: Session = Depends(get_db)) -> dict:
    if locale not in LOCALE_NAMES:
        raise HTTPException(status_code=422, detail="locale must be one of zh-Hant, ko")
    brief = db.get(Brief, brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found")

    draft = dict(brief.generated_draft or {})
    cached = cached_translation(draft, locale)
    if cached:
        return cached

    try:
        draft, translation = with_cached_translation(draft, locale)
    except Exception as exc:  # pragma: no cover - provider/network failure path
        logger.exception("Translation failed for brief %s locale %s", brief_id, locale)
        raise HTTPException(status_code=502, detail=f"Translation failed: {exc}") from exc

    db.refresh(brief)
    latest_draft = dict(brief.generated_draft or {})
    translations = {**latest_draft.get("_translations", {}), locale: translation}
    brief.generated_draft = {**latest_draft, "_translations": translations}
    record_event(
        db,
        org_id=brief.org_id,
        action="brief.translated",
        object_type="brief",
        object_id=str(brief.id),
        model_provider="litellm",
        model_version=translation_model(),
        detail={"locale": locale, "mode": "reader_sidecar"},
    )
    db.commit()
    return translation


@router.get("/watchlists/{watchlist_id}/briefs")
def list_briefs(watchlist_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    _get_watchlist(db, watchlist_id)
    briefs = db.scalars(
        select(Brief)
        .where(Brief.watchlist_id == watchlist_id)
        .order_by(Brief.created_at.desc())
        .limit(50)
    )
    return [
        {
            "brief_id": str(b.id),
            "status": b.status,
            "created_at": b.created_at.isoformat(),
            "claims": len(b.generated_draft.get("claims", [])),
        }
        for b in briefs
    ]


@router.get("/briefs/{brief_id}/evidence")
def get_brief_evidence(brief_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    """Full evidence-ledger payload: stored claims -> citations -> exact chunk text,
    span, source URL, retrieval timestamp, checksum, validator status. This is the
    'click a claim, see the proof' endpoint (plan §14 demo moment)."""
    brief = db.get(Brief, brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found")
    wl = _get_watchlist(db, brief.watchlist_id)

    claims = _claims_in_draft_order(db, brief)
    claim_ids = [c.id for c in claims]
    rows = db.execute(
        select(Citation, Chunk, Document, Source)
        .join(Chunk, Chunk.id == Citation.chunk_id, isouter=True)
        .join(Document, Document.id == Chunk.document_id, isouter=True)
        .join(Source, Source.id == Document.source_id, isouter=True)
        .where(Citation.claim_id.in_(claim_ids))
    ).all() if claim_ids else []

    citations_by_claim: dict[uuid.UUID, list[dict]] = {}
    for citation, chunk, document, source in rows:
        citations_by_claim.setdefault(citation.claim_id, []).append(
            {
                "span_id": str(citation.chunk_id),
                "validator": citation.validator_status,
                "validated_at": citation.validated_at.isoformat()
                if citation.validated_at
                else None,
                "evidence_quote": citation.evidence_quote,
                "span": [citation.span_start, citation.span_end],
                "section": chunk.section if chunk else None,
                "chunk_text": chunk.text if chunk else None,
                "doc_type": document.doc_type if document else None,
                "accession": document.filing_accession if document else None,
                "source_url": source.url if source else None,
                "publisher": source.publisher if source else None,
                "retrieved_at": source.retrieved_at.isoformat()
                if source and source.retrieved_at
                else None,
                "checksum_sha256": source.checksum_sha256 if source else None,
            }
        )

    draft = brief.generated_draft
    return {
        "brief_id": str(brief.id),
        "watchlist": wl.name,
        "watchlist_id": str(wl.id),
        "status": brief.status,
        "created_at": brief.created_at.isoformat(),
        "sections": draft.get("brief_sections", []),
        "open_questions": draft.get("open_questions", []),
        "translations": draft.get("_translations", {}),
        "user_edits": brief.user_edits or {},
        "claims": [
            {
                "claim_id": str(c.id),
                "index": i,
                "text": c.text,
                "type": c.claim_type.value,
                "confidence": c.confidence,
                "support_status": c.support_status.value,
                "needs_review": c.needs_review,
                "citations": citations_by_claim.get(c.id, []),
            }
            for i, c in enumerate(claims)
        ],
    }


@router.post("/claims/{claim_id}/repair")
def repair_claim(claim_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    """Deterministically repair a flagged claim using only its stored citation span.

    This is intentionally conservative: the replacement text is an excerpt from the
    cited evidence, not a fresh model synthesis. Analyst edits can still refine the
    prose after the claim is back inside the citation boundary.
    """
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    brief = db.get(Brief, claim.brief_id)
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found")
    if brief.status == "approved":
        raise HTTPException(status_code=409, detail="Approved briefs are immutable")

    rows = db.execute(
        select(Citation, Chunk)
        .join(Chunk, Chunk.id == Citation.chunk_id, isouter=True)
        .where(Citation.claim_id == claim.id)
    ).all()
    if not rows:
        raise HTTPException(status_code=422, detail="Claim has no citations to repair from")

    citation, chunk = next(((cit, ch) for cit, ch in rows if ch is not None), (None, None))
    if citation is None or chunk is None:
        raise HTTPException(status_code=422, detail="Claim has no stored evidence span")

    quote = citation.evidence_quote.strip()
    if not quote or quote.lower() not in chunk.text.lower():
        quote = _first_sentence(chunk.text)
    replacement = _first_sentence(quote)
    if not replacement:
        raise HTTPException(status_code=422, detail="Stored evidence span is empty")

    old_text = claim.text
    claim.text = replacement
    claim.support_status = SupportStatus.SUPPORTED
    claim.needs_review = False
    citation.evidence_quote = replacement
    citation.validator_status = "pass"

    ordered = _claims_in_draft_order(db, brief)
    claim_index = next((i for i, row in enumerate(ordered) if row.id == claim.id), None)
    draft = {**brief.generated_draft}
    draft_claims = [dict(row) for row in draft.get("claims", [])]
    if claim_index is not None and claim_index < len(draft_claims):
        draft_claims[claim_index] = {
            **draft_claims[claim_index],
            "text": replacement,
            "confidence": "high",
            "evidence_quote": replacement,
            "needs_review": False,
        }
        draft["claims"] = draft_claims
        brief.generated_draft = draft

    if brief.status == "draft":
        brief.status = "in_review"

    record_event(
        db,
        org_id=claim.org_id,
        action="claim.repaired",
        object_type="claim",
        object_id=str(claim.id),
        detail={"old_text": old_text, "new_text": replacement, "repair_mode": "extractive"},
    )
    db.commit()
    return {
        "claim_id": str(claim.id),
        "text": replacement,
        "support_status": claim.support_status.value,
        "needs_review": claim.needs_review,
        "evidence_quote": replacement,
    }
