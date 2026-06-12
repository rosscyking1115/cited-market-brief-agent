"""End-to-end vertical slice demo: watchlist -> EDGAR/FRED ingest -> cited brief -> export.

Prereqs: docker compose db running, tables created (scripts/bootstrap_db.py),
SEC_USER_AGENT set in .env. FRED_API_KEY and LLM keys optional (degrades gracefully:
no FRED key = filings only; no LLM key = deterministic extractive brief).

Usage (from backend/):
    python scripts/demo_brief.py
"""

import asyncio
import sys

from sqlalchemy import select

from app.briefs.service import export_brief_markdown, generate_and_store_brief
from app.db.base import get_sessionmaker
from app.db.models import Organization, Watchlist
from app.ingestion.pipeline import run_ingestion

TICKERS = ["NVDA", "AMD", "AVGO"]
MACRO = ["CPIAUCSL", "DGS10"]


async def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    db = get_sessionmaker()()
    try:
        org = db.scalar(select(Organization).where(Organization.name == "dev-org"))
        if org is None:
            org = Organization(name="dev-org")
            db.add(org)
            db.commit()

        wl = db.scalar(select(Watchlist).where(Watchlist.name == "demo-us-semis"))
        if wl is None:
            wl = Watchlist(
                org_id=org.id, name="demo-us-semis", tickers=TICKERS, macro_series=MACRO
            )
            db.add(wl)
            db.commit()

        print("Ingesting (EDGAR fair-access throttled — this takes a minute)...")
        counts = await run_ingestion(db, wl)
        print(f"  ingested: {counts}")

        print("Generating brief...")
        brief = generate_and_store_brief(db, wl)
        md, _manifest = export_brief_markdown(db, brief, wl)

        print(f"\nBrief {brief.id} exported to .data/exports/")
        print("=" * 70)
        print(md[:2500])
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
