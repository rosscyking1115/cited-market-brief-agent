"""'What changed since last brief' (plan Phase 3 exit criterion).

Aggregates, per watchlist:
- new documents ingested since the previous brief
- risk-factor / MD&A diffs between the latest two filings of the same form per company
  (re-parsed deterministically from the raw store; diff blocks mapped to stored chunks
  so change claims remain citable)
- macro deltas with vintage revision detection across the latest two snapshots
"""

import logging
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.changes.filing_diff import blocks_to_chunk_ids, diff_filings
from app.changes.macro_delta import compute_series_delta
from app.db.models import Brief, Chunk, Document, Source, TimeSeries, Watchlist
from app.ingestion.sec_parser import parse_filing_html
from app.storage.raw_store import get_raw_store

logger = logging.getLogger(__name__)

_DIFFABLE_FORMS = {"10-K", "10-Q"}
_MAX_SAMPLE_BLOCKS = 5


def _accession_cik(accession: str | None) -> str | None:
    """EDGAR accession numbers embed the filer CIK: 0001045810-26-000089 -> 1045810."""
    if not accession or "-" not in accession:
        return None
    head = accession.split("-", 1)[0]
    return str(int(head)) if head.isdigit() else None


def _previous_brief(db: Session, watchlist: Watchlist) -> Brief | None:
    return db.scalar(select(Brief).where(Brief.watchlist_id == watchlist.id).order_by(Brief.created_at.desc()).limit(1))


def _filing_diffs(db: Session, watchlist: Watchlist) -> tuple[list[dict], list[str]]:
    """Diff the latest two same-form filings per company; return (summaries, chunk ids)."""
    docs = list(
        db.scalars(
            select(Document)
            .join(Source, Source.id == Document.source_id)
            .where(
                Document.org_id == watchlist.org_id,
                Document.doc_type.in_(_DIFFABLE_FORMS),
            )
            .order_by(Document.publication_date.desc())
        )
    )

    by_company: dict[tuple[str, str], list[Document]] = {}
    for doc in docs:
        cik = _accession_cik(doc.filing_accession)
        if cik:
            by_company.setdefault((cik, doc.doc_type), []).append(doc)

    store = get_raw_store()
    summaries: list[dict] = []
    changed_chunk_ids: list[str] = []

    for (cik, form), group in by_company.items():
        if len(group) < 2:
            continue
        new_doc, old_doc = group[0], group[1]
        try:
            new_src = db.get(Source, new_doc.source_id)
            old_src = db.get(Source, old_doc.source_id)
            new_parsed = parse_filing_html(store.get(new_src.raw_object_key).decode("utf-8", errors="replace"))
            old_parsed = parse_filing_html(store.get(old_src.raw_object_key).decode("utf-8", errors="replace"))
        except Exception:
            logger.exception("diff re-parse failed for CIK %s %s", cik, form)
            continue

        diffs = diff_filings(
            old_parsed.normalized_text,
            old_parsed.sections,
            new_parsed.normalized_text,
            new_parsed.sections,
        )
        if not diffs:
            continue

        chunk_spans = [
            (str(c.id), c.span_start, c.span_end)
            for c in db.scalars(select(Chunk).where(Chunk.document_id == new_doc.id))
        ]
        all_blocks = [b for d in diffs for b in d.blocks]
        changed_chunk_ids.extend(blocks_to_chunk_ids(all_blocks, chunk_spans))

        samples = [
            {
                "kind": b.kind,
                "section": b.section,
                "text": (b.new_text or b.old_text)[:280],
                "similarity": b.similarity,
            }
            for b in all_blocks[:_MAX_SAMPLE_BLOCKS]
        ]
        summaries.append(
            {
                "cik": cik,
                "form": form,
                "publisher": new_src.publisher,
                "accession_new": new_doc.filing_accession,
                "accession_old": old_doc.filing_accession,
                "sections": [
                    {"section": d.section, "added": d.added, "removed": d.removed, "modified": d.modified}
                    for d in diffs
                ],
                "samples": samples,
            }
        )

    return summaries, list(dict.fromkeys(changed_chunk_ids))


def _macro_deltas(db: Session, watchlist: Watchlist) -> list[dict]:
    out: list[dict] = []
    for series_id in watchlist.macro_series:
        snapshots = list(
            db.scalars(
                select(TimeSeries)
                .where(
                    TimeSeries.org_id == watchlist.org_id,
                    TimeSeries.series_id == series_id,
                )
                .order_by(TimeSeries.vintage.desc())
                .limit(2)
            )
        )
        if not snapshots:
            continue
        new_obs = snapshots[0].observations or {}
        old_obs = snapshots[1].observations if len(snapshots) > 1 else None
        delta = compute_series_delta(series_id, new_obs, old_obs)
        if delta.has_signal:
            d = asdict(delta)
            d["vintage"] = snapshots[0].vintage.isoformat() if snapshots[0].vintage else None
            out.append(d)
    return out


def changes_since_last_brief(db: Session, watchlist: Watchlist) -> dict:
    previous = _previous_brief(db, watchlist)
    since = previous.created_at if previous else None

    new_docs_q = (
        select(Document, Source)
        .join(Source, Source.id == Document.source_id)
        .where(Document.org_id == watchlist.org_id)
    )
    if since is not None:
        new_docs_q = new_docs_q.where(Document.created_at > since)
    new_documents = [
        {
            "document_id": str(doc.id),
            "doc_type": doc.doc_type,
            "accession": doc.filing_accession,
            "publisher": src.publisher,
            "url": src.url,
            "publication_date": doc.publication_date.isoformat() if doc.publication_date else None,
        }
        for doc, src in db.execute(new_docs_q.order_by(Document.created_at.desc()).limit(25))
    ]

    filing_diffs, changed_chunk_ids = _filing_diffs(db, watchlist)
    macro_deltas = _macro_deltas(db, watchlist)

    return {
        "watchlist_id": str(watchlist.id),
        "since": since.isoformat() if since else None,
        "previous_brief_id": str(previous.id) if previous else None,
        "new_documents": new_documents,
        "filing_diffs": filing_diffs,
        "macro_deltas": macro_deltas,
        "changed_chunk_ids": changed_chunk_ids,
    }
