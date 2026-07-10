"""Seed the pilot watchlist templates (plan Phase 6: 2-3 real templates).

Idempotent — safe to re-run. Schedules fire daily at 23:00 UTC, which is
07:00 Taiwan time. Run the pilot with scripts/run_scheduled.py via cron.

    python scripts/seed_watchlists.py
"""

from sqlalchemy import select

from app.db.base import get_sessionmaker
from app.db.models import Organization, Watchlist

PILOT_CRON = "0 23 * * *"

TEMPLATES = [
    {
        "name": "US Semiconductors — morning brief",
        "tickers": ["NVDA", "AMD", "AVGO", "TSM", "MU"],
        "sectors": ["Information Technology", "Semiconductors"],
        "macro_series": ["CPIAUCSL", "DGS10", "FEDFUNDS"],
    },
    {
        "name": "US Megabanks — morning brief",
        "tickers": ["JPM", "BAC", "GS", "MS", "C"],
        "sectors": ["Financials", "Banks"],
        # Rates complex: 10Y, 2s10s spread, Fed funds, bank credit
        "macro_series": ["DGS10", "T10Y2Y", "FEDFUNDS", "TOTBKCR"],
    },
    {
        "name": "US Energy Majors — morning brief",
        "tickers": ["XOM", "CVX", "COP"],
        "sectors": ["Energy"],
        # WTI spot, Henry Hub spot, gasoline
        "macro_series": ["DCOILWTICO", "DHHNGSP", "GASREGW"],
    },
]


def main() -> None:
    db = get_sessionmaker()()
    try:
        org = db.scalar(select(Organization).where(Organization.name == "dev-org"))
        if org is None:
            org = Organization(name="dev-org")
            db.add(org)
            db.commit()

        for template in TEMPLATES:
            existing = db.scalar(
                select(Watchlist).where(Watchlist.org_id == org.id, Watchlist.name == template["name"])
            )
            if existing:
                print(f"exists  {template['name']}")
                continue
            db.add(
                Watchlist(
                    org_id=org.id,
                    schedule_cron=PILOT_CRON,
                    template="morning_brief",
                    **template,
                )
            )
            db.commit()
            print(f"created {template['name']} (cron: {PILOT_CRON})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
