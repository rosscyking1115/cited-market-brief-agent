"""Prewarm reader-mode translations for existing briefs.

Use this after deploying translation-cache changes so already-created briefs
become instant in the UI without waiting for tomorrow's scheduled run.

    python scripts/prewarm_translations.py          # latest brief per watchlist
    python scripts/prewarm_translations.py --all    # every stored brief
"""

import sys

from sqlalchemy import select

from app.briefs.service import prewarm_and_store_brief_translations
from app.db.base import get_sessionmaker
from app.db.models import Brief, Watchlist


def _latest_briefs(db) -> list[Brief]:
    briefs: list[Brief] = []
    watchlists = db.scalars(select(Watchlist)).all()
    for watchlist in watchlists:
        brief = db.scalar(
            select(Brief)
            .where(Brief.watchlist_id == watchlist.id)
            .order_by(Brief.created_at.desc())
            .limit(1)
        )
        if brief is not None:
            briefs.append(brief)
    return briefs


def main() -> None:
    db = get_sessionmaker()()
    try:
        if "--all" in sys.argv:
            briefs = list(db.scalars(select(Brief).order_by(Brief.created_at.desc())))
        else:
            briefs = _latest_briefs(db)

        if not briefs:
            print("No briefs found.")
            return

        for brief in briefs:
            before = sorted((brief.generated_draft or {}).get("_translations", {}).keys())
            prewarm_and_store_brief_translations(db, brief)
            db.refresh(brief)
            after = sorted((brief.generated_draft or {}).get("_translations", {}).keys())
            print(f"{brief.id}: {before or 'none'} -> {after or 'none'}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
