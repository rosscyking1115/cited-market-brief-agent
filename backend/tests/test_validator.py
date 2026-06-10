from app.briefs.schemas import GeneratedClaim
from app.briefs.validator import validate_claims

SPANS = {
    "span-1": "Revenue increased 12% year over year, driven by datacenter growth.",
    "span-2": "The company added a new export-control risk factor this quarter.",
}


def _claim(**kwargs) -> GeneratedClaim:
    return GeneratedClaim(text="t", **kwargs)


def test_no_citations_is_unsupported() -> None:
    [result] = validate_claims([_claim(citations=[])], SPANS)
    assert result.support_status == "unsupported"
    assert result.needs_review


def test_unknown_span_id_fails() -> None:
    [result] = validate_claims([_claim(citations=["span-404"])], SPANS)
    assert result.support_status == "flagged"
    assert result.citations[0].status == "fail"
    assert "unknown span_id" in result.citations[0].reason


def test_verbatim_quote_passes() -> None:
    [result] = validate_claims(
        [_claim(citations=["span-1"], evidence_quote="Revenue increased 12% year over year")],
        SPANS,
    )
    assert result.support_status == "supported"
    assert result.citations[0].status == "pass"


def test_quote_whitespace_and_case_normalized() -> None:
    [result] = validate_claims(
        [_claim(citations=["span-2"], evidence_quote="NEW   export-control risk\nfactor")],
        SPANS,
    )
    assert result.support_status == "supported"


def test_fabricated_quote_fails() -> None:
    [result] = validate_claims(
        [_claim(citations=["span-1"], evidence_quote="Revenue decreased 50%")], SPANS
    )
    assert result.support_status == "flagged"
    assert result.citations[0].status == "fail"


def test_one_passing_citation_suffices() -> None:
    [result] = validate_claims(
        [
            _claim(
                citations=["span-404", "span-1"],
                evidence_quote="driven by datacenter growth",
            )
        ],
        SPANS,
    )
    assert result.support_status == "supported"
    statuses = {c.span_id: c.status for c in result.citations}
    assert statuses == {"span-404": "fail", "span-1": "pass"}
