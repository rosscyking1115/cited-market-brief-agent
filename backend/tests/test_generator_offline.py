from app.briefs.generator import _json_payload, generate_deterministic
from app.briefs.schemas import EvidenceItem
from app.briefs.validator import validate_claims

PACK = [
    EvidenceItem(
        span_id="span-1",
        doc_label="ACME 10-Q 0000000000-26-000001 · Item 1A",
        section="Item 1A",
        text="A new export-control risk factor was added this quarter. It may affect revenue.",
    ),
    EvidenceItem(
        span_id="span-2",
        doc_label="FRED macro_series CPIAUCSL",
        section="CPIAUCSL",
        text="Consumer Price Index (CPIAUCSL). Units: Index. Observations:\n2026-05: 327.1",
    ),
]


def test_offline_brief_is_citation_perfect() -> None:
    brief = generate_deterministic("demo", PACK)
    assert brief.claims, "expected extractive claims"
    span_texts = {item.span_id: item.text for item in PACK}
    validations = validate_claims(brief.claims, span_texts)
    assert all(v.support_status == "supported" for v in validations)


def test_offline_brief_sections_reference_claims() -> None:
    brief = generate_deterministic("demo", PACK)
    joined = "\n".join(s.content_markdown for s in brief.brief_sections)
    assert "[#0]" in joined


def test_json_payload_accepts_fenced_provider_output() -> None:
    assert _json_payload('```json\n{"brief_sections":[]}\n```') == '{"brief_sections":[]}'


def test_json_payload_accepts_unclosed_fence() -> None:
    assert _json_payload('```json\n{"brief_sections":[]}') == '{"brief_sections":[]}'
