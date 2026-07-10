"""Export orchestration: DB -> ExportBundle -> format builders, with Export rows
and audit events per artifact (plan Phase 4 exit: audit trail records exports).
"""

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.briefs.generator import llm_available
from app.briefs.guardrails import apply_guardrails
from app.briefs.schemas import GeneratedBrief
from app.briefs.service import _stored_spans
from app.briefs.validator import validate_claims
from app.core.config import settings
from app.db.models import Brief, Export, TimeSeries, User, Watchlist
from app.exports.bundle import ExportBundle, build_bundle
from app.exports.html_report import build_report_html
from app.exports.pptx_export import build_pptx
from app.exports.xlsx_export import build_xlsx
from app.services.audit import record_event

MEDIA_TYPES = {
    "pdf": "application/pdf",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def assemble_bundle(db: Session, brief: Brief, watchlist: Watchlist) -> ExportBundle:
    generated = GeneratedBrief.model_validate(brief.generated_draft)
    span_texts, span_labels, span_meta = _stored_spans(db, generated.claims, watchlist.org_id)
    validations = apply_guardrails(generated.claims, validate_claims(generated.claims, span_texts))
    approved_by_email = None
    if brief.approved_by:
        user = db.get(User, brief.approved_by)
        approved_by_email = user.email if user else None

    model_used = settings.generation_model if llm_available() else "deterministic/extractive-v1"
    return build_bundle(
        brief_id=str(brief.id),
        watchlist=watchlist.name,
        generated_at=brief.created_at,
        model=model_used,
        prompt_version=settings.prompt_version,
        status=brief.status,
        approved_by=approved_by_email,
        approved_at=brief.approved_at,
        generated=generated,
        validations=validations,
        span_labels=span_labels,
        span_meta=span_meta,
        user_edits=brief.user_edits or {},
    )


def _macro_rows(db: Session, watchlist: Watchlist) -> list[dict]:
    rows: list[dict] = []
    for series_id in watchlist.macro_series:
        snapshot = db.scalar(
            select(TimeSeries)
            .where(TimeSeries.org_id == watchlist.org_id, TimeSeries.series_id == series_id)
            .order_by(TimeSeries.vintage.desc())
            .limit(1)
        )
        if snapshot:
            rows.append(
                {
                    "series_id": snapshot.series_id,
                    "observations": snapshot.observations,
                    "units": snapshot.units,
                    "frequency": snapshot.frequency,
                    "vintage": snapshot.vintage.isoformat() if snapshot.vintage else "",
                }
            )
    return rows


def export_brief(db: Session, brief: Brief, watchlist: Watchlist, fmt: str) -> tuple[str, bytes, str]:
    """Returns (filename, content bytes, media type) and records the export."""
    if fmt not in MEDIA_TYPES:
        raise ValueError(f"fmt must be one of {sorted(MEDIA_TYPES)}")

    bundle = assemble_bundle(db, brief, watchlist)

    if fmt == "pdf":
        from app.exports.pdf import html_to_pdf  # lazy: needs playwright

        content = html_to_pdf(build_report_html(bundle))
    elif fmt == "pptx":
        content = build_pptx(bundle)
    else:
        content = build_xlsx(bundle, time_series=_macro_rows(db, watchlist))

    out_dir = Path(settings.exports_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"brief_{brief.id}.{fmt}"
    (out_dir / filename).write_bytes(content)

    db.add(
        Export(
            org_id=watchlist.org_id,
            brief_id=brief.id,
            fmt=fmt,
            object_key=str(out_dir / filename),
            ai_marking_embedded=True,
        )
    )
    record_event(
        db,
        org_id=watchlist.org_id,
        action="export.created",
        object_type="brief",
        object_id=str(brief.id),
        detail={"format": fmt, "status": brief.status, "bytes": len(content)},
    )
    db.commit()
    return filename, content, MEDIA_TYPES[fmt]
