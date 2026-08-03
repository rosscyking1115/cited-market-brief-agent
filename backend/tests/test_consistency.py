"""Unit tests for the consistency rules (validator rule 5).

These rules REJECT claims, so their false-positive behaviour is the dangerous
side: a wrong rejection destroys a true, properly-cited claim and it never
exports. Most of this file is therefore about what the rules must NOT flag.

The modal-verb case below is a real defect found in independent review, not a
hypothetical. It is pinned because the corpus could not catch it — every source
document happens to be dated May 2026, so the bug was invisible in aggregate.
"""

import pytest

from app.briefs.consistency import check_claim_consistency, claim_numbers, claim_periods
from app.briefs.schemas import GeneratedClaim
from app.briefs.validator import validate_claims


def _claim(text: str, quote: str = "", citations: tuple[str, ...] = ("s1",)) -> GeneratedClaim:
    return GeneratedClaim(text=text, citations=list(citations), evidence_quote=quote)


# --------------------------------------------------------------------------
# Regression: the modal verb "may" is not the month May
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        # --- bare modal, no number anywhere
        "Tariffs may raise costs.",
        "Export restrictions may increase cost of revenue.",
        "The company may borrow, repay and reborrow revolving loans.",
        "Results may differ materially from expectations.",
        # --- modal followed by a number: the boundary the adjacency rule creates.
        # The first version of this fix required only "a number next to the
        # month", which left every one of these flagging. They are ordinary
        # credit-agreement prose and one of the corpus source documents IS a
        # credit agreement.
        "Up to $250 million may be utilized for letters of credit.",
        "The Company may, 30 days after the Closing Date, request an increase.",
        "The Borrower may, 3 business days prior to any borrowing, deliver a notice.",
        "Lenders may 60 days after default accelerate the loans.",
        "The Company may 1) borrow and 2) repay revolving loans.",
        "Costs may 10% exceed guidance.",
        "The facility may 5 times be extended.",
        "Borrowings may 2026 be repaid early.",  # even a year-shaped neighbour
        # --- other months as common words are rarer but the rule is uniform
        "The march 15 protest disrupted logistics.",
    ],
)
def test_modal_and_lowercase_month_words_are_not_period_references(text: str) -> None:
    """Hedging language must not be read as a date.

    "may" is the commonest modal verb in filing prose, and a claim it wrongly
    flags never exports. Two defences: the month must be capitalised as a proper
    noun, and a year must be present unless the day precedes the month.

    These cases are enumerated from the DEFECT CLASS — modal with and without a
    following number, comma-separated, enumerations, percentages, durations —
    not from the examples in any one review. The first cut of this fix passed a
    battery drawn from a reviewer's report and still failed half the class; see
    test_capitalised_modal_with_a_number_is_not_a_date for the other side of the
    boundary, which that cut left unprobed.
    """
    assert claim_periods(text) == set()


def test_modal_may_with_a_number_survives_the_full_validator() -> None:
    """The credit-agreement phrasing, end to end, with a passing citation."""
    spans = {
        "s1": (
            "The Company shall have the right, upon 30 days written notice after the "
            "Closing Date, to request an increase in the Revolving Facility."
        )
    }
    labels = {"s1": "AMD 8-K 2026-06-14 · Item 1.01"}
    claim = _claim(
        "The Company may, 30 days after the Closing Date, request an increase in the Revolving Facility.",
        quote="to request an increase in the Revolving Facility",
    )
    [validation] = validate_claims([claim], spans, labels)
    assert validation.support_status == "supported", validation.reason


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("The CPI-U index for May 2026 stood at 333.979.", {"may"}),
        ("the fiscal quarter ended May 3, 2026", {"may"}),
        ("dated as of April 29, 2022", {"april"}),
        ("entered into the Credit Agreement in June 2026", {"june"}),
        ("averaged 4.47% during July 2026", {"july"}),
        ("gross margin for the first quarter of fiscal year 2027", {"first"}),
    ],
)
def test_months_next_to_a_number_are_period_references(text: str, expected: set[str]) -> None:
    """The fix must not cost real temporal detection."""
    assert claim_periods(text) == expected


def test_hedged_claim_survives_the_full_validator() -> None:
    """End-to-end version of the regression, through validate_claims."""
    spans = {"s1": "Export restrictions could increase our cost of revenue in future periods."}
    claim = _claim(
        "Export restrictions may increase cost of revenue.",
        quote="Export restrictions could increase our cost of revenue",
    )
    [validation] = validate_claims([claim], spans)
    assert validation.support_status == "supported", validation.reason


# --------------------------------------------------------------------------
# Identifiers and locators are not quantities
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "ACME 10-Q 0000000000-26-000001: a new risk factor was added.",  # accession
        "Reported in Item 8.01 of the filing.",  # section locator
        "Attached as Exhibit 99.1 to the report.",
        "Filed under Rule 405 of the Securities Act.",
        "The H200 and MI350 accelerators shipped.",  # letter-fused
    ],
)
def test_document_identifiers_are_not_read_as_asserted_quantities(text: str) -> None:
    assert claim_numbers(text) == set()


def test_real_quantities_are_still_extracted() -> None:
    assert claim_numbers("Revenue was $75.2 billion, up 92% and 21% sequentially.") == {"75.2", "92", "21"}
    assert claim_numbers("Gross margin was 74.9% against 60.5%.") == {"74.9", "60.5"}


def test_thousands_separators_and_trailing_zeros_canonicalise() -> None:
    assert claim_numbers("Gross margin was $15,415 million.") == {"15415"}
    assert claim_numbers("The yield was 4.50%.") == claim_numbers("The yield was 4.5%.")


# --------------------------------------------------------------------------
# Document labels inform the TEMPORAL check only
# --------------------------------------------------------------------------


def test_label_integers_cannot_satisfy_an_invented_quantity() -> None:
    """A label donates structural integers; they must not license a number claim.

    "NVDA 10-Q Q1 FY2027 · Item 2" contains 1, 2, 10 and 2027. Folding that into
    the numeric evidence pool let a claim assert quantities no span stated —
    a loosening found in independent review.
    """
    span = "Gross margin improved on a favourable product mix."
    label = "NVDA 10-Q Q1 FY2027 · Item 2 · Results of Operations"
    claim = _claim("NVIDIA reported 2 reportable segments and 10 major customers in fiscal 2027.")
    failures = check_claim_consistency(claim, span, label)
    assert failures, "label integers must not satisfy the numeric rule"
    assert failures[0].startswith("numeric:")


def test_label_periods_do_satisfy_the_temporal_rule() -> None:
    """Periods legitimately live in labels, so the temporal check reads them."""
    span = "Operating expenses increased six percent sequentially."
    label = "AMD 8-K 2026-05-14 · Item 1.01"
    claim = _claim("Operating expenses increased in May 2026.")
    assert check_claim_consistency(claim, span, label) == []
    # ...and without the label the same claim is flagged, proving the label is doing the work
    assert check_claim_consistency(claim, span, "") != []


# --------------------------------------------------------------------------
# The rules still catch what they are for
# --------------------------------------------------------------------------


def test_invented_quantity_is_flagged() -> None:
    claim = _claim("Data Center revenue was $85.2 billion.")
    failures = check_claim_consistency(claim, "Data Center revenue was $75.2 billion, up 92%.")
    assert failures and failures[0].startswith("numeric:")


def test_wrong_period_is_flagged() -> None:
    claim = _claim("AMD entered into the Credit Agreement in June 2026.")
    failures = check_claim_consistency(claim, "On May 14, 2026 the Company entered into a Credit Agreement.")
    assert failures and failures[0].startswith("temporal:")


def test_nothing_resolved_produces_no_consistency_noise() -> None:
    """Provenance has already rejected the claim; rule 5 adds nothing useful."""
    assert check_claim_consistency(_claim("Anything at all, 42."), "") == []


# --------------------------------------------------------------------------
# ISO dates are checked, not skipped as identifiers
# --------------------------------------------------------------------------


def test_wrong_iso_observation_date_is_caught() -> None:
    """A claim citing an observation date the series lacks must be rejected.

    Treating ISO dates as identifiers made this invisible: the numeric rule
    skipped the token and the temporal rule saw no month name, so nothing
    checked it. FRED series are a first-class source and every observation is
    ISO-dated, so the gap sat exactly where the product uses dates most.
    """
    span = "DATE VALUE 2026-06-10 4.45 2026-06-11 4.47 2026-06-12 4.48"
    claim = _claim("The DGS10 observation for 2026-07-04 was 4.47.")
    failures = check_claim_consistency(claim, span)
    assert failures and failures[0].startswith("numeric:")


def test_correct_iso_observation_date_is_accepted() -> None:
    span = "DATE VALUE 2026-06-10 4.45 2026-06-11 4.47 2026-06-12 4.48"
    claim = _claim("The DGS10 observation for 2026-06-11 was 4.47.")
    assert check_claim_consistency(claim, span) == []


def test_accession_numbers_are_still_skipped_but_plain_long_runs_are_not() -> None:
    """Zero padding is what marks an identifier; a long digit run is a quantity."""
    assert claim_numbers("Filed under 0000000000-26-000001 last quarter.") == set()
    assert claim_numbers("The CIK is 0001045810.") == set()
    assert claim_numbers("Shares outstanding were 24500000000.") == {"24500000000"}


def test_ambiguous_locator_words_need_a_citation_continuation() -> None:
    """'section', 'note', 'part', 'form' and 'rule' are ordinary English.

    Stripping them unconditionally deleted real quantities from claims; dropping
    them entirely would reject real regulatory citations. So they qualify as
    locators only in citation form.
    """
    # Ordinary English — the number is a real quantity and must be checked
    assert claim_numbers("Section 5 employees were reduced.") == {"5"}
    assert claim_numbers("The form 8 acquisitions closed.") == {"8"}
    # Citation form — the number names a place, not a quantity
    assert claim_numbers("Filed under Rule 405 of the Securities Act.") == set()
    assert claim_numbers("Pursuant to Section 13 of the Exchange Act.") == set()


def test_unambiguous_filing_locators_are_always_removed() -> None:
    assert claim_numbers("Reported in Item 8.01 of the filing.") == set()
    assert claim_numbers("Attached as Exhibit 99.1.") == set()
    assert claim_numbers("See Annex 2 for detail.") == set()


# --------------------------------------------------------------------------
# Boundaries created by the case-sensitivity defence itself
#
# The previous cut of this battery tested only LOWERCASE modal constructions —
# it guarded the defence but not the boundary the defence introduced. These
# cases come from the other side: a CAPITALISED "May" in modal position, which
# is where defence 1 cannot help and defence 2 has to carry the weight.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        # Title-case body prose — capitalised modal AND capitalised measure word
        "The Company May 30 Days After Closing Request An Increase.",
        "Revenue May 15 Times Higher Than Guidance.",
        # Measure words no blocklist would reliably enumerate
        "The Company May 30 basis points reduce the margin.",
        "Costs May 12 percentage points exceed plan.",
        "The facility May 5 times be extended.",
        # Sentence-initial modal, where capitalisation carries no information
        "May 30 days elapse before the notice takes effect.",
        "May 15 lenders participate in the syndicate.",
    ],
)
def test_capitalised_modal_with_a_number_is_not_a_date(text: str) -> None:
    """A year is required, so none of these can be read as a date.

    This is why the duration-noun blocklist was removed: it had to enumerate
    every measure word English might use, and review escaped it twice in a
    minute. Requiring a year is structural and subsumes the class.
    """
    assert claim_periods(text) == set()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("The agreement was signed May 3, 2026.", {"may"}),
        ("The agreement was signed May 3rd, 2026.", {"may"}),
        ("dated as of April 29, 2022", {"april"}),
        ("the quarter ended 3 May", {"may"}),
        ("reported for May 2026", {"may"}),
    ],
)
def test_genuine_dates_still_resolve_after_the_year_requirement(text: str, expected: set[str]) -> None:
    assert claim_periods(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "MAY 3, 2026 WAS THE CLOSING DATE.",  # all-caps
        "The agreement was signed May 3.",  # bare month + day, no year
        "reported for may 2026",  # lowercase month
    ],
)
def test_known_temporal_blind_spots_are_pinned(text: str) -> None:
    """Documented capability losses, all in the safe (false-acceptance) direction.

    Pinned rather than left implicit so that closing one is a visible change
    rather than an accident. Recorded in the Limits section of
    docs/EVAL_METHODOLOGY.md.
    """
    assert claim_periods(text) == set()


# --------------------------------------------------------------------------
# Systematic date-shape classification
#
# Every previous round of this module ended the same way: a new defence landed,
# and the boundary THAT defence created was the thing left untested. Three
# rounds, three times, each caught by a reviewer rather than by the suite.
#
# A hand-picked list cannot end that pattern, because the cases you think to
# write are the ones you already understand. This enumerates the cross-product
# of date shape x letter case instead, and declares the expected classification
# for every cell. A rule change that moves any cell fails here — including the
# cells nobody thought to worry about.
# --------------------------------------------------------------------------

_MONTHS = ("January February March April May June July August September October November December").split()

#: shape -> is it recognised as a period reference, in canonical capitalisation?
#: False entries are DELIBERATE losses, each recorded in the Limits section of
#: docs/EVAL_METHODOLOGY.md. They are not aspirations; changing one to True
#: means the rule changed and the disclosure must change with it.
DATE_SHAPES = {
    "{m} {y}": True,  # May 2026
    "{m} {d}, {y}": True,  # May 3, 2026
    "{m} {d} {y}": True,  # May 3 2026
    "{m} {o}, {y}": True,  # May 3rd, 2026
    "{d} {m} {y}": True,  # 3 May 2026
    "{o} {m} {y}": True,  # 3rd May 2026
    "{d} {m}": True,  # 3 May — day first, no modal reading possible
    "{m} {d}": False,  # May 3 — indistinguishable from "may 3 times"
    "{m} of {y}": False,  # May of 2026 — year not adjacent
    "{m}, {y}": False,  # May, 2026 — year not adjacent
    "{m} in fiscal {y}": False,  # year not adjacent
    "{m}": False,  # bare month
}


def _render(shape: str, month: str) -> str:
    return shape.format(m=month, d="3", o="3rd", y="2026")


@pytest.mark.parametrize("shape,recognised", sorted(DATE_SHAPES.items()))
@pytest.mark.parametrize("month", _MONTHS)
def test_date_shape_classification_is_uniform_across_months(shape: str, recognised: bool, month: str) -> None:
    """Every month behaves identically. No month is special-cased, including May."""
    text = f"Revenue rose in {_render(shape, month)} on strong demand."
    detected = month.lower() in claim_periods(text)
    assert detected is recognised, (
        f"shape {shape!r} with {month}: expected recognised={recognised}, got {detected}. "
        "If the rule changed deliberately, update DATE_SHAPES and the Limits section "
        "of docs/EVAL_METHODOLOGY.md together."
    )


@pytest.mark.parametrize("shape", sorted(DATE_SHAPES))
@pytest.mark.parametrize("transform", ["lower", "upper"], ids=["lowercase", "ALLCAPS"])
def test_no_date_shape_is_recognised_outside_canonical_capitalisation(shape: str, transform: str) -> None:
    """Case-sensitivity is what separates the month May from the modal "may".

    The cost is that lowercase and ALL-CAPS dates are invisible, uniformly and
    for every shape. That is a deliberate loss in the false-acceptance
    direction, pinned here so that closing it is a visible change.
    """
    rendered = _render(shape, "May")
    text = f"Revenue rose in {getattr(rendered, transform)()} on strong demand."
    assert claim_periods(text) == set()


def test_a_month_range_hides_the_month_the_evidence_lacks() -> None:
    """A month range resolves only its second month, so the first one escapes.

    "May and June 2026" yields June alone.

    Found in review. The Limits section said the loss was "a date with no year",
    which was narrower than the behaviour: the year must be ADJACENT. A claim
    that widens the period it covers is not rejected.
    """
    assert claim_periods("Revenue rose in May and June 2026.") == {"june"}

    claim = _claim("Revenue rose in May and June 2026.")
    span = "The CPI-U index for June 2026 stood at 334.5."
    assert check_claim_consistency(claim, span) == [], "documented blind spot; see Limits"


def test_equivalent_notation_is_wrongly_rejected() -> None:
    """The README's fourth example: a supported claim refused over notation.

    The numeric rule is set-subset over canonicalised numeric literals, so a
    claim that restates the span's own figure in an equivalent form asserts a
    number the span does not contain and is refused. `$5.0 billion` canonicalises
    to 5 and passes; `$5,000 million` canonicalises to 5000 and does not.

    This is the concrete reason recall 1.000 is a property of these corpora
    rather than a guarantee: every supported claim in them happens to restate
    figures in the span's own notation. Pinned here so the README's example
    cannot quietly become false if canonicalisation changes — if this test goes
    red, the README paragraph beside it needs rewriting, not this assertion.

    The span is the real AMD 8-K text from the held-out corpus.
    """
    span = (
        "The Credit Agreement provides for a five-year, $5.0 billion unsecured "
        "revolving credit facility (the “Revolving Facility”)."
    )

    accepted = "AMD entered into a $5.0 billion revolving credit facility."
    assert check_claim_consistency(_claim(accepted), span) == []

    rounded = "AMD entered into a $5 billion revolving credit facility."
    assert check_claim_consistency(_claim(rounded), span) == []

    restated = "AMD entered into a $5,000 million revolving credit facility."
    failures = check_claim_consistency(_claim(restated), span)
    assert failures == ["numeric: 5000 not in the cited evidence"], (
        "the equivalent-notation false negative documented in the README no longer "
        "reproduces; update the README's limit example in the same change"
    )
