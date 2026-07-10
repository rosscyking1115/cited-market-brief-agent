import json

from app.briefs.markdown import build_citation_manifest, render_markdown
from app.briefs.schemas import BriefSection, GeneratedBrief, GeneratedClaim
from app.briefs.validator import validate_claims

SPANS = {"span-1": "Revenue increased 12% year over year."}
LABELS = {"span-1": "ACME 10-Q 0000000000-26-000001 · Item 2"}


def _brief() -> GeneratedBrief:
    return GeneratedBrief(
        brief_sections=[BriefSection(title="Filing changes", content_markdown="Revenue grew [#0]. Also [#1].")],
        claims=[
            GeneratedClaim(
                text="Revenue increased 12% YoY",
                citations=["span-1"],
                evidence_quote="Revenue increased 12% year over year",
            ),
            GeneratedClaim(text="Margins will definitely expand", citations=[]),
        ],
        open_questions=["What drove the increase?"],
    )


def test_supported_claims_render_flagged_quarantined() -> None:
    brief = _brief()
    validations = validate_claims(brief.claims, SPANS)
    md = render_markdown(
        title="What changed?",
        watchlist_name="demo",
        brief=brief,
        validations=validations,
        span_labels=LABELS,
        model="deterministic/extractive-v1",
        prompt_version="p1.0",
    )
    assert "C-000" in md and "✓ PASS" in md
    assert "Needs review" in md
    assert "Margins will definitely expand" in md  # in review section
    assert "INTERNAL RESEARCH DRAFT" in md
    # The flagged claim must NOT appear in the evidence ledger table
    ledger = md.split("## Evidence ledger")[1].split("##")[0]
    assert "Margins" not in ledger


def test_manifest_is_valid_json_with_art50_marking() -> None:
    brief = _brief()
    validations = validate_claims(brief.claims, SPANS)
    manifest = json.loads(
        build_citation_manifest(
            brief_id="b-1",
            watchlist_name="demo",
            brief=brief,
            validations=validations,
            span_meta={"span-1": {"doc_type": "10-Q", "accession": "0000000000-26-000001"}},
            model="deterministic/extractive-v1",
            prompt_version="p1.0",
        )
    )
    assert manifest["ai_generated"] is True
    assert manifest["format"].startswith("cited-market-brief-agent.citation-manifest/")
    c0 = manifest["claims"][0]
    assert c0["support_status"] == "supported"
    assert c0["citations"][0]["validator"] == "pass"
    assert manifest["claims"][1]["support_status"] == "unsupported"
