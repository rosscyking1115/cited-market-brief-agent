"""Schedule runner (Phase 3 lite): ingest + generate for every watchlist whose
cron schedule is due. Run from cron/Task Scheduler every few minutes; Hatchet
replaces this with durable workflows in Phase 5.

    python scripts/run_scheduled.py            # run due watchlists
    python scripts/run_scheduled.py --force    # run all scheduled watchlists now

Due-ness: croniter computes the next fire time after the last brief's created_at;
if that time is in the past, the watchlist is due.
"""

import asyncio
import sys
from datetime import UTC, datetime

from sqlalchemy import select

from app.briefs.service import generate_and_store_brief, prewarm_and_store_brief_translations
from app.db.base import get_sessionmaker
from app.db.models import Brief, Watchlist
from app.ingestion.pipeline import run_ingestion


def _is_due(schedule_cron: str, last_run: datetime | None, now: datetime) -> bool:
    try:
        from croniter import croniter  # optional dep: pip install croniter
    except ImportError:
        print("croniter not installed — treating all scheduled watchlists as due")
        return True
    base = last_run or datetime(1970, 1, 1, tzinfo=UTC)
    next_fire = croniter(schedule_cron, base).get_next(datetime)
    if next_fire.tzinfo is None:
        next_fire = next_fire.replace(tzinfo=UTC)
    return next_fire <= now


async def main(force: bool = False) -> None:
    db = get_sessionmaker()()
    now = datetime.now(UTC)
    try:
        watchlists = list(
            db.scalars(select(Watchlist).where(Watchlist.schedule_cron.is_not(None)))
        )
        failures = 0
        for wl in watchlists:
            last_brief = db.scalar(
                select(Brief)
                .where(Brief.watchlist_id == wl.id)
                .order_by(Brief.created_at.desc())
                .limit(1)
            )
            last_run = last_brief.created_at if last_brief else None
            if not force and not _is_due(wl.schedule_cron, last_run, now):
                print(f"skip {wl.name}: not due")
                continue
            # Pilot resilience: one watchlist failing must not block the others,
            # and every failure lands in the audit log for the error-review ritual
            # (pilot/PILOT_RUNBOOK.md).
            try:
                print(f"run  {wl.name}: ingesting…")
                counts = await run_ingestion(db, wl)
                brief = generate_and_store_brief(db, wl)
                prewarm_and_store_brief_translations(db, brief)
                print(f"     ingested {counts}, brief {brief.id}")
            except Exception as exc:
                failures += 1
                db.rollback()
                from app.services.audit import record_event

                record_event(
                    db,
                    org_id=wl.org_id,
                    action="pilot.run_failed",
                    object_type="watchlist",
                    object_id=str(wl.id),
                    detail={"error": f"{type(exc).__name__}: {exc}"[:500]},
                )
                print(f"FAIL {wl.name}: {type(exc).__name__}: {exc}")
        if failures:
            print(f"\n{failures} watchlist run(s) failed — triage in pilot/ERROR_LOG.md")
            sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main(force="--force" in sys.argv))
