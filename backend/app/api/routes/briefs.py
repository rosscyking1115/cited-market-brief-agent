"""Ingestion + brief generation endpoints (Phase 1: synchronous local slice).

Long-running work moves to Hatchet workflows when schedules land; the service
functions are already shaped for that hand-off.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.briefs.service import export_brief_markdown, generate_and_store_brief
from app.db.base import get_db
from app.db.models import Brief, Chunk, Citation, Claim, Document, Source, Watchlist
from app.ingestion.pipeline import run_ingestion

router = APIRouter(tags=["briefs"])


def _get_watchlist(db: Session, watchlist_id: uuid.UUID) -> Watchlist:
    wl = db.get(Watchlist, watchlist_id)
    if wl is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return wl


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

    claims = list(
        db.scalars(select(Claim).where(Claim.brief_id == brief.id).order_by(Claim.id))
    )
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
