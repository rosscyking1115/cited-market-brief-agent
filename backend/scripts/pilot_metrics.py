"""Pilot metrics snapshot (plan §11 product metrics).

Prints the scorecard and writes pilot/METRICS_SNAPSHOT.md for the weekly review.

    python scripts/pilot_metrics.py
"""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select

from app.db.base import get_sessionmaker
from app.db.models import (
    AuditEvent,
    Brief,
    Claim,
    Export,
    Feedback,
    SupportStatus,
    Watchlist,
)

SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "pilot" / "METRICS_SNAPSHOT.md"


def main() -> None:
    db = get_sessionmaker()()
    try:
        briefs_total = db.scalar(select(func.count(Brief.id))) or 0
        briefs_by_status = dict(db.execute(select(Brief.status, func.count(Brief.id)).group_by(Brief.status)).all())
        claims_total = db.scalar(select(func.count(Claim.id))) or 0
        claims_supported = (
            db.scalar(select(func.count(Claim.id)).where(Claim.support_status == SupportStatus.SUPPORTED)) or 0
        )
        claims_flagged = claims_total - claims_supported
        validated_pct = (100.0 * claims_supported / claims_total) if claims_total else 0.0

        feedback_by_kind = dict(
            db.execute(select(Feedback.kind, func.count(Feedback.id)).group_by(Feedback.kind)).all()
        )
        wrong_rate = 100.0 * feedback_by_kind.get("wrong", 0) / claims_total if claims_total else 0.0
        exports_by_fmt = dict(db.execute(select(Export.fmt, func.count(Export.id)).group_by(Export.fmt)).all())
        run_failures = db.scalar(select(func.count(AuditEvent.id)).where(AuditEvent.action == "pilot.run_failed")) or 0
        watchlists = db.scalar(select(func.count(Watchlist.id))) or 0
        approval_rate = 100.0 * briefs_by_status.get("approved", 0) / briefs_total if briefs_total else 0.0

        lines = [
            "# Pilot metrics snapshot",
            "",
            f"Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "| Metric | Value | Target (plan §11 / Phase 2 gate) |",
            "|---|---|---|",
            f"| Watchlists | {watchlists} | 2–3 pilot templates |",
            f"| Briefs generated | {briefs_total} | daily per watchlist |",
            f"| Briefs approved | {briefs_by_status.get('approved', 0)} ({approval_rate:.0f}%) | — |",
            f"| Briefs in review / draft | {briefs_by_status.get('in_review', 0)} / "
            f"{briefs_by_status.get('draft', 0)} | — |",
            f"| Claims total | {claims_total} | — |",
            f"| Claims validated | {claims_supported} ({validated_pct:.1f}%) | ≥95% |",
            f"| Claims flagged/unsupported | {claims_flagged} | flagged pre-export, never exported |",
            f"| Feedback: useful | {feedback_by_kind.get('useful', 0)} | — |",
            f"| Feedback: not useful | {feedback_by_kind.get('not_useful', 0)} | — |",
            f"| Feedback: wrong | {feedback_by_kind.get('wrong', 0)} ({wrong_rate:.1f}% of claims) | trending to 0 |",
            f"| Feedback: needs source | {feedback_by_kind.get('needs_source', 0)} | — |",
            f"| Exports | {', '.join(f'{k}: {v}' for k, v in sorted(exports_by_fmt.items())) or 'none'} | — |",
            f"| Scheduled-run failures | {run_failures} | triaged in pilot/ERROR_LOG.md |",
        ]
        report = "\n".join(lines) + "\n"
        print(report)
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(report, encoding="utf-8")
        print(f"-- written to {SNAPSHOT_PATH} --")
    finally:
        db.close()


if __name__ == "__main__":
    main()
