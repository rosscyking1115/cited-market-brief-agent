"""Deterministic consistency checks between a claim and the spans it cites.

These are NOT an entailment checker and must not be described as one. They are
two narrow, mechanical rules that catch a specific and common class of citation
error — a claim that introduces a quantity or a period the cited evidence does
not contain. Real entailment (does this prose actually follow from that prose?)
is untouched, and the modal-strength failures in the eval corpus stay uncaught:
"the USG granted licences that would allow us to ship" does not become "we
shipped" through any amount of lexical comparison.

Why these two rules and not more
--------------------------------
Both are derivable from first principles without looking at the evaluation set:
a factual claim about a filing should not assert a number the filing does not
state, nor attribute a figure to a period the filing does not discuss. That
matters, because a checker tuned against the corpus that scores it reproduces
exactly the tautology this project removed — the generator producing what the
checker checks, one level up.

An open-ended named-entity rule was prototyped and deliberately rejected: it
raised precision but cost recall, wrongly rejecting genuinely supported claims,
and every attempt to repair it amounted to fitting the fixture.

Design notes
------------
- Checks run against the UNION of a claim's cited spans, not each span
  separately, so a claim that legitimately draws one figure from each of two
  spans is not rejected for it.
- The claim side is read strictly and the span side permissively. A false
  rejection destroys a true claim; a false acceptance is merely the status quo.
- Tokens mixing letters and digits (`H200`, `MI350`, `10-Q`, `CPIAUCSL`) are
  skipped on the claim side. Matching them is identifier comparison, which is
  the open-ended entity rule under another name.
"""

import re

from app.briefs.schemas import GeneratedClaim

#: A numeric literal: optional thousands separators, optional decimal part.
_NUMBER = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")

_HAS_LETTER = re.compile(r"[A-Za-z]")

_QUARTER = re.compile(r"\b(first|second|third|fourth)\s+quarter\b", re.IGNORECASE)

_MONTH_NAMES = "January|February|March|April|May|June|July|August|September|October|November|December"

#: A month counts as a PERIOD REFERENCE only when it is written as a DATE.
#:
#: Two defences, because "may" is both a month and the commonest modal verb in
#: filing prose, and a bare-month rule rejected any hedged claim whose evidence
#: happened not to contain the word:
#:
#: 1. CASE-SENSITIVE. The month is a proper noun ("May 2026"); the modal is not
#:    ("the Company may"). This is the signal `re.IGNORECASE` was throwing away.
#: 2. A YEAR IS REQUIRED unless the day precedes the month. So "May 2026",
#:    "May 3, 2026" and "29 April" qualify; a bare "Month + number" does not.
#:
#: Defence 2 replaced an earlier duration-noun blocklist ("not followed by
#: days/weeks/percent"). The blocklist was the wrong shape: it had to enumerate
#: every measure word English might put after a number, and review escaped it
#: twice in a minute ("May 15 Times Higher", "May 30 basis points"). Requiring a
#: year is structural rather than enumerative, and it subsumes the whole class —
#: "The Company May 30 Days After Closing" carries no year and cannot match.
#:
#: There is no comma alternative between month and number: a date writes
#: "May 3, 2026" (comma after the day), never "May, 30".
#:
#: The costs are two, both in the safe direction and both recorded in the
#: Limits section of docs/EVAL_METHODOLOGY.md: a bare "May 3" with no year is
#: not detected, and neither is a date in ALL-CAPS text.
_DAY = r"(?:0?[1-9]|[12]\d|3[01])"
_YEAR = r"(?:19|20)\d{2}"

_MONTH_IN_DATE = re.compile(
    # 29 April, 3rd May — the day precedes, so no modal reading is possible
    rf"\b{_DAY}(?:st|nd|rd|th)?\s+({_MONTH_NAMES})\b"
    # May 2026
    rf"|\b({_MONTH_NAMES})\s+{_YEAR}\b"
    # May 3, 2026 — day then year, comma optional
    rf"|\b({_MONTH_NAMES})\s+{_DAY}(?:st|nd|rd|th)?,?\s+{_YEAR}\b"
)

#: ISO dates are DATES, not identifiers: "2026-07-04" asserts a specific
#: observation date and must be checked. Matched before _IDENTIFIER, which
#: would otherwise swallow it as a hyphen-joined group and let a claim cite an
#: observation the series does not contain — a regression found in review.
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

#: Document identifiers, not quantities: accession numbers
#: ("0000000000-26-000001") and zero-padded CIKs ("0001045810"). Skipped on the
#: claim side for the same reason letter-fused tokens are — comparing
#: identifiers is a different rule, and the zero-padding canonicalises to
#: meaningless small integers no cited span will contain.
#:
#: The long-run branch requires a LEADING ZERO. A plain 8+ digit run is a
#: quantity ("24500000000" shares), and skipping those silently dropped real
#: assertions.
_IDENTIFIER = re.compile(r"^0\d{7,}$|^\d+(?:-\d+){2,}$")

#: Document locators — "Item 1A", "Item 8.01", "Exhibit 99.1". The number names
#: a place in a filing, not a quantity, so it is removed from the claim before
#: numbers are extracted. Same rationale as _IDENTIFIER and the letter-fused
#: skip: comparing locators is the provenance layer's job.
#:
#: The vocabulary is split by ambiguity. "item", "exhibit", "schedule",
#: "appendix" and "annex" followed by a number are locators in any context.
#: "section", "rule", "note", "part" and "form" are ordinary English —
#: "Section 5 employees were reduced" is not a locator — so those require a
#: citation continuation ("of the", "to", "under") to qualify. Stripping them
#: unconditionally deleted real quantities; dropping them entirely would have
#: rejected real regulatory citations such as "Rule 405 of the Securities Act",
#: which is the false-rejection direction this module exists to avoid.
_LOCATOR_NUMBER = r"\d+(?:\.\d+)*[A-Za-z]?\b"
_DOC_LOCATOR = re.compile(
    rf"\b(?:item|exhibit|schedule|appendix|annex)\s+{_LOCATOR_NUMBER}"
    rf"|\b(?:section|rule|note|part|form)\s+{_LOCATOR_NUMBER}(?=\s+(?:of|to|under|pursuant)\b)",
    re.IGNORECASE,
)
_MONTH_NUMBER = {
    "january": "01",
    "february": "02",
    "march": "03",
    "april": "04",
    "may": "05",
    "june": "06",
    "july": "07",
    "august": "08",
    "september": "09",
    "october": "10",
    "november": "11",
    "december": "12",
}


def _canonical(raw: str) -> str:
    """Canonicalise a numeric literal: 1,234.50 -> 1234.5; 04 -> 4; 0.50 -> 0.5."""
    value = raw.replace(",", "")
    if "." in value:
        value = value.rstrip("0").rstrip(".")
    integer, _, fraction = value.partition(".")
    integer = integer.lstrip("0") or "0"
    return f"{integer}.{fraction}" if fraction else integer


def claim_numbers(text: str) -> set[str]:
    """Numbers asserted by the claim.

    Read strictly: tokens containing letters are skipped, because a number
    fused to letters is part of an identifier (H200, MI350) rather than a
    quantity, and comparing identifiers is a different rule.
    """
    found: set[str] = set()
    for raw_token in _DOC_LOCATOR.sub(" ", text).split():
        if _HAS_LETTER.search(raw_token):
            continue
        token = raw_token.strip("$()[],;:%").rstrip(".")
        # ISO dates are checked, not skipped — see _ISO_DATE.
        if not _ISO_DATE.match(token) and _IDENTIFIER.match(token):
            continue
        found.update(_canonical(m.group()) for m in _NUMBER.finditer(token))
    return found


def span_numbers(text: str) -> set[str]:
    """Numbers available in the evidence. Read permissively: every numeric
    literal anywhere in the span counts, identifiers included.
    """
    return {_canonical(m.group()) for m in _NUMBER.finditer(text)}


def label_numbers(text: str) -> set[str]:
    """Year-like values a document label contributes to the numeric evidence.

    ONLY years. A label establishes the filing's period, so a claim naming that
    year ("in May 2026", "fiscal 2027") is citing it, not inventing it. But a
    label also carries structural integers — "10-Q Q1 · Item 2" yields 1, 2 and
    10 — and admitting those would let a claim assert quantities no span states.
    Independent review caught exactly that, so the window is deliberately narrow.
    """
    return {m.group() for m in re.finditer(r"\b(?:19|20)\d{2}\b", text)}


def claim_periods(text: str) -> set[str]:
    periods = {m.group(1).lower() for m in _QUARTER.finditer(text)}
    for match in _MONTH_IN_DATE.finditer(text):
        month = next(group for group in match.groups() if group)
        periods.add(month.lower())
    return periods


def _period_present(period: str, span: str) -> bool:
    if re.search(rf"\b{re.escape(period)}\b", span, re.IGNORECASE):
        return True
    # FRED-style series write months as -MM- rather than by name
    month_number = _MONTH_NUMBER.get(period)
    return bool(month_number and re.search(rf"-{month_number}-", span))


def check_claim_consistency(claim: GeneratedClaim, cited_text: str, cited_labels: str = "") -> list[str]:
    """Return the names of the consistency rules the claim fails.

    `cited_text` is the concatenation of every span the claim cites that
    resolved. An empty string means nothing resolved, in which case provenance
    has already rejected the claim and there is nothing useful to add.

    `cited_labels` is the document labels of those same spans, and is used for
    the TEMPORAL check only. Labels legitimately carry period information
    ("NVDA 10-Q Q1 FY2027", "AMD 8-K 2026-05-14") that a claim may restate.

    They are deliberately NOT used for the numeric check. A label donates its
    structural integers — "10-Q Q1 · Item 2" contributes 1, 2 and 10 — which
    would let a claim assert quantities no span states. Review caught that
    loosening; the accession-number false positive it was originally added to
    prevent is now handled properly, by skipping document identifiers on the
    claim side (see _IDENTIFIER).
    """
    if not cited_text.strip():
        return []

    failures: list[str] = []

    available = span_numbers(cited_text) | label_numbers(cited_labels)
    missing_numbers = claim_numbers(claim.text) - available
    if missing_numbers:
        failures.append(f"numeric: {', '.join(sorted(missing_numbers))} not in the cited evidence")

    period_evidence = f"{cited_labels} {cited_text}"
    missing_periods = [p for p in sorted(claim_periods(claim.text)) if not _period_present(p, period_evidence)]
    if missing_periods:
        failures.append(f"temporal: {', '.join(missing_periods)} not in the cited evidence")

    return failures
