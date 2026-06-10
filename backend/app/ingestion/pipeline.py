"""Ingestion pipeline (plan §7 steps 1–4): EDGAR filings + FRED series ->
raw store -> parsed chunks -> Postgres (single write path: pgvector + FTS).

Phase 1 runs this synchronously from the API; Hatchet wraps it as a durable
workflow when schedules land. Every step emits audit events.
"""

import uuid
from datetime import datetime, timezone

UTC = timezone.utc

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.fred import FredClient
from app.connectors.sec_edgar import SecEdgarClient
from app.core.config import settings
from app.db.models import (
    Chunk,
    Document,
    Source,
    SourceType,
    TimeSeries,
    TrustTier,
    Watchlist,
)
from app.ingestion.sec_parser import parse_filing_html
from app.rag.embeddings import embed_texts
from app.services.audit import record_event
from app.storage.raw_store import get_raw_store

# Forms worth a morning brief, newest first; cap per ticker keeps the slice fast
_INTERESTING_FORMS = ("10-Q", "10-K", "8-K")
_MAX_FILINGS_PER_TICKER = 2


def _archive_url(cik: str, accession: str, primary_doc: str) -> str:
    accession_nodash = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_nodash}/{primary_doc}"


async def _resolve_ciks(sec: SecEdgarClient, tickers: list[str]) -> dict[str, str]:
    mapping = await sec.get_company_tickers()
    by_ticker = {row["ticker"].upper(): str(row["cik_str"]) for row in mapping.values()}
    return {t.upper(): by_ticker[t.upper()] for t in tickers if t.upper() in by_ticker}


def _store_document(
    db: Session,
    *,
    org_id: uuid.UUID,
    url: str,
    publisher: str,
    source_type: SourceType,
    trust_tier: TrustTier,
    license_note: str,
    raw: bytes,
    filename: str,
    doc_type: str,
    accession: str | None,
    publication_date: datetime | None,
    chunks: list[tuple[str, str, int | None, int | None, bool]],
) -> Document:
    """Persist Source -> Document -> Chunks (with FTS vector; embeddings optional)."""
    store = get_raw_store()
    object_key, checksum = store.put(str(org_id), filename, raw)

    source = Source(
        org_id=org_id,
        url=url,
        publisher=publisher,
        source_type=source_type,
        trust_tier=trust_tier,
        license_note=license_note,
        access_method="api",
        retrieved_at=datetime.now(UTC),
        checksum_sha256=checksum,
        raw_object_key=object_key,
    )
    db.add(source)
    db.flush()

    document = Document(
        org_id=org_id,
        source_id=source.id,
        doc_type=doc_type,
        filing_accession=accession,
        publication_date=publication_date,
    )
    db.add(document)
    db.flush()

    texts = [c[0] for c in chunks]
    vectors = embed_texts(texts)  # None when no embedding key configured (FTS-only mode)

    for i, (text, section, span_start, span_end, is_table) in enumerate(chunks):
        db.add(
            Chunk(
                org_id=org_id,
                document_id=document.id,
                section=section,
                span_start=span_start,
                span_end=span_end,
                is_table=is_table,
                text=text,
                embedding=vectors[i] if vectors else None,
                fts=func.to_tsvector("english", text),
            )
        )

    record_event(
        db,
        org_id=org_id,
        action="source.ingested",
        object_type="document",
        object_id=str(document.id),
        source_ids=[str(source.id)],
        detail={"url": url, "doc_type": doc_type, "chunks": len(chunks), "checksum": checksum},
    )
    return document


async def ingest_sec_for_watchlist(db: Session, watchlist: Watchlist) -> int:
    """Fetch latest interesting filings per ticker; skip accessions already stored."""
    sec = SecEdgarClient()
    ingested = 0
    try:
        ciks = await _resolve_ciks(sec, list(watchlist.tickers))
        for ticker, cik in ciks.items():
            submissions = await sec.get_submissions(cik)
            recent = submissions.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            picked = 0
            for idx, form in enumerate(forms):
                if form not in _INTERESTING_FORMS or picked >= _MAX_FILINGS_PER_TICKER:
                    continue
                accession = recent["accessionNumber"][idx]
                exists = db.scalar(
                    select(Document.id).where(
                        Document.org_id == watchlist.org_id,
                        Document.filing_accession == accession,
                    )
                )
                if exists:
                    picked += 1
                    continue

                primary_doc = recent["primaryDocument"][idx]
                url = _archive_url(cik, accession, primary_doc)
                raw = await sec.get_raw(url)
                parsed = parse_filing_html(raw.decode("utf-8", errors="replace"))
                filing_date = recent.get("filingDate", [None] * len(forms))[idx]
                pub_date = (
                    datetime.fromisoformat(filing_date).replace(tzinfo=UTC)
                    if filing_date
                    else None
                )
                _store_document(
                    db,
                    org_id=watchlist.org_id,
                    url=url,
                    publisher=f"SEC EDGAR ({ticker})",
                    source_type=SourceType.SEC_FILING,
                    trust_tier=TrustTier.OFFICIAL,
                    license_note="US government work; EDGAR fair-access terms",
                    raw=raw,
                    filename=primary_doc,
                    doc_type=form,
                    accession=accession,
                    publication_date=pub_date,
                    chunks=[
                        (c.text, c.section, c.span_start, c.span_end, c.is_table)
                        for c in parsed.chunks
                    ],
                )
                ingested += 1
                picked += 1
        db.commit()
    finally:
        await sec.aclose()
    return ingested


async def ingest_fred_for_watchlist(db: Session, watchlist: Watchlist) -> int:
    """Snapshot each FRED series as a citable document (one chunk per series),
    plus a TimeSeries row with vintage metadata (ALFRED awareness, plan §7)."""
    if not settings.fred_api_key.strip() or not watchlist.macro_series:
        return 0

    fred = FredClient()
    ingested = 0
    try:
        for series_id in watchlist.macro_series:
            info = (await fred.get_series_info(series_id)).get("seriess", [{}])[0]
            obs = await fred.get_observations(series_id)
            observations = obs.get("observations", [])[-13:]  # ~1y of monthly data
            vintage = datetime.now(UTC)

            db.add(
                TimeSeries(
                    org_id=watchlist.org_id,
                    provider="fred",
                    series_id=series_id,
                    units=info.get("units", ""),
                    frequency=info.get("frequency", ""),
                    vintage=vintage,
                    observations={o["date"]: o["value"] for o in observations},
                )
            )

            lines = [
                f"{info.get('title', series_id)} ({series_id}). "
                f"Units: {info.get('units', 'n/a')}. Frequency: {info.get('frequency', 'n/a')}. "
                f"Data vintage: {vintage.date().isoformat()}.",
                "Observations:",
            ] + [f"{o['date']}: {o['value']}" for o in observations]
            text = "\n".join(lines)

            _store_document(
                db,
                org_id=watchlist.org_id,
                url=f"https://fred.stlouisfed.org/series/{series_id}",
                publisher="FRED, Federal Reserve Bank of St. Louis",
                source_type=SourceType.MACRO_SERIES,
                trust_tier=TrustTier.OFFICIAL,
                license_note=(
                    "FRED API terms: attribution required; not endorsed or certified by the "
                    "Federal Reserve Bank of St. Louis; some series carry third-party restrictions"
                ),
                raw=text.encode("utf-8"),
                filename=f"{series_id}.txt",
                doc_type="macro_series",
                accession=None,
                publication_date=vintage,
                chunks=[(text, series_id, 0, len(text), True)],
            )
            ingested += 1
        db.commit()
    finally:
        await fred.aclose()
    return ingested


async def run_ingestion(db: Session, watchlist: Watchlist) -> dict[str, int]:
    record_event(
        db,
        org_id=watchlist.org_id,
        action="ingest.started",
        object_type="watchlist",
        object_id=str(watchlist.id),
    )
    sec_count = await ingest_sec_for_watchlist(db, watchlist)
    fred_count = await ingest_fred_for_watchlist(db, watchlist)
    record_event(
        db,
        org_id=watchlist.org_id,
        action="ingest.completed",
        object_type="watchlist",
        object_id=str(watchlist.id),
        detail={"sec_documents": sec_count, "fred_series": fred_count},
    )
    return {"sec_documents": sec_count, "fred_series": fred_count}
