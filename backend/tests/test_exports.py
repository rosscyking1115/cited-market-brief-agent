import io
import json
from datetime import datetime, timezone

import pytest

from app.briefs.guardrails import apply_guardrails
from app.briefs.markdown import build_citation_manifest
from app.briefs.schemas import BriefSection, GeneratedBrief, GeneratedClaim
from app.briefs.validator import validate_claims
from app.exports.bundle import build_bundle, strip_claim_refs
from app.exports.html_report import build_report_html
from app.exports.xlsx_export import _safe_cell, build_xlsx

SPANS = {
    "span-1": "Revenue increased 12% year over year, driven by datacenter growth.",
    "span-2": "A new export-control risk factor was added this quarter.",
}
LABELS = {"span-1": "ACME 10-Q · Item 2", "span-2": "ACME 10-Q · Item 1A"}
META = {
    "span-1": {"doc_type": "10-Q", "accession": "0000000000-26-000001", "section": "Item 2",
               "span": [100, 200], "source_url": "https://example.sec.gov/a", "checksum_sha256": "abc"},
    "span-2": {"doc_type": "10-Q", "accession": "0000000000-26-000001", "section": "Item 1A",
               "span": [300, 400], "source_url": "https://example.sec.gov/a", "checksum_sha256": "abc"},
}


def _generated() -> GeneratedBrief:
    return GeneratedBrief(
        brief_sections=[
            BriefSection(title="Filing changes", content_markdown="Revenue grew [#0]."),
            BriefSection(title="Risks", content_markdown="New risk factor [#1]."),
            BriefSection(title="Noise", content_markdown="Rejected section text."),
        ],
        claims=[
            GeneratedClaim(
                text="Revenue increased 12% YoY",
                citations=["span-1"],
                evidence_quote="Revenue increased 12% year over year",
            ),
            GeneratedClaim(
                text="New export-control risk factor added",
                citations=["span-2"],
                evidence_quote="new export-control risk factor was added",
            ),
            GeneratedClaim(text="<script>alert(1)</script> margins will expand", citations=[]),
        ],
        open_questions=["What drove margins?"],
    )


def _bundle(status: str = "draft", user_edits: dict | None = None):
    generated = _generated()
    validations = apply_guardrails(generated.claims, validate_claims(generated.claims, SPANS))
    return build_bundle(
        brief_id="b-1",
        watchlist="demo",
        generated_at=datetime(2026, 6, 10, 6, 21, tzinfo=timezone.utc),
        model="deterministic/extractive-v1",
        prompt_version="p1.0",
        status=status,
        approved_by="dev@ledgerbrief.local" if status == "approved" else None,
        approved_at=datetime(2026, 6, 10, 7, 0, tzinfo=timezone.utc)
        if status == "approved"
        else None,
        generated=generated,
        validations=validations,
        span_labels=LABELS,
        span_meta=META,
        user_edits=user_edits or {},
    ), generated, validations


def test_bundle_applies_review_state() -> None:
    edits = {
        "sections": {
            "1": {"action": "edit", "content": "Analyst rewrite of risks.", "at": "t", "by": "dev"},
            "2": {"action": "reject", "content": None, "at": "t", "by": "dev"},
        }
    }
    bundle, _, _ = _bundle(user_edits=edits)
    titles = [s.title for s in bundle.sections]
    assert "Noise" not in titles  # rejected section excluded
    risks = next(s for s in bundle.sections if s.title == "Risks")
    assert risks.content == "Analyst rewrite of risks."  # edit wins
    assert len(bundle.supported_claims) == 2
    assert len(bundle.review_claims) == 1  # uncited claim quarantined


def test_watermark_reflects_approval() -> None:
    draft, _, _ = _bundle("draft")
    assert "NOT APPROVED" in draft.watermark
    approved, _, _ = _bundle("approved")
    assert approved.watermark.startswith("APPROVED")
    assert "dev@ledgerbrief.local" in (approved.approval_line or "")


def test_html_report_escapes_llm_text() -> None:
    bundle, _, _ = _bundle()
    html = build_report_html(bundle)
    assert "<script>" not in html  # injected markup neutralized
    assert "&lt;script&gt;" in html
    assert "INTERNAL RESEARCH DRAFT" in html
    assert "ledger" in html.lower()


def test_strip_claim_refs() -> None:
    assert strip_claim_refs("Revenue grew [#0] and [#12].") == "Revenue grew (C-000) and (C-012)."


def test_xlsx_formula_injection_escaped() -> None:
    assert _safe_cell("=HYPERLINK(...)") == "'=HYPERLINK(...)"
    assert _safe_cell("+1.2") == "'+1.2"
    assert _safe_cell("-1.24%") == "'-1.24%"
    assert _safe_cell("@cmd") == "'@cmd"
    assert _safe_cell("plain text") == "plain text"
    assert _safe_cell(42) == 42


def test_xlsx_roundtrip_and_manifest_consistency() -> None:
    """Exit criterion: the citation manifest matches the exported ledger claims."""
    openpyxl = pytest.importorskip("openpyxl")
    bundle, generated, validations = _bundle()

    xlsx_bytes = build_xlsx(
        bundle,
        time_series=[{"series_id": "CPIAUCSL", "observations": {"2026-05": "327.1"},
                      "units": "Index", "frequency": "Monthly", "vintage": "2026-06-10"}],
    )
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    assert {"Brief", "Evidence Ledger", "Sources", "Macro Data", "Disclosures"} <= set(wb.sheetnames)

    ledger = wb["Evidence Ledger"]
    xlsx_rows = {
        (row[0].value, row[4].value)
        for row in ledger.iter_rows(min_row=2)
        if row[0].value
    }

    manifest = json.loads(
        build_citation_manifest(
            brief_id="b-1", watchlist_name="demo", brief=generated,
            validations=validations, span_meta=META,
            model="deterministic/extractive-v1", prompt_version="p1.0",
        )
    )
    manifest_rows = {(c["id"], c["support_status"]) for c in manifest["claims"]}
    assert xlsx_rows == manifest_rows
    assert manifest["ai_generated"] is True


def test_pptx_roundtrip() -> None:
    pptx = pytest.importorskip("pptx")
    bundle, _, _ = _bundle()
    data = __import__("app.exports.pptx_export", fromlist=["build_pptx"]).build_pptx(bundle)
    prs = pptx.Presentation(io.BytesIO(data))
    # title + 3 sections (none rejected here) + ledger + needs-review + disclaimer
    assert len(prs.slides) >= 6
    all_text = "\n".join(
        run.text
        for slide in prs.slides
        for shape in slide.shapes
        if shape.has_text_frame
        for para in shape.text_frame.paragraphs
        for run in para.runs
    )
    assert "What changed since yesterday?" in all_text
    assert "INTERNAL RESEARCH DRAFT" in all_text
    assert "Not investment advice" in all_text
    assert "ai_generated=true" in (prs.core_properties.comments or "")
