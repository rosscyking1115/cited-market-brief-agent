"""Deterministic citation validator (plan §7 steps 8–10).

Application-layer enforcement — the model's claimed citations are checked against
stored spans:
1. A claim with no citations is UNSUPPORTED.
2. A citation referencing a span_id not in the evidence store FAILS.
3. If an evidence_quote is provided, it must appear verbatim (whitespace-normalized)
   in the cited span's text, otherwise the citation FAILS.
4. A claim is SUPPORTED if at least one citation passes; otherwise FLAGGED.
5. A claim that passes 1–4 is FLAGGED anyway if it fails a consistency check —
   it asserts a number or a period the cited evidence does not contain
   (see consistency.py).

Rules 1–4 check PROVENANCE: where the quote came from. They do not check that
the quote supports the claim, and rule 5 only narrows that gap, it does not
close it. Measured coverage and the residual are in docs/EVAL_METHODOLOGY.md;
do not describe this module as verifying that claims are supported by their
sources.

Flagged/unsupported claims never export (enforced at export time).
"""

import re
from dataclasses import dataclass, field

from app.briefs.consistency import check_claim_consistency
from app.briefs.schemas import GeneratedClaim


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


@dataclass
class CitationResult:
    span_id: str
    status: str  # pass | fail
    reason: str = ""


@dataclass
class ClaimValidation:
    claim_index: int
    support_status: str  # supported | unsupported | flagged
    needs_review: bool
    citations: list[CitationResult] = field(default_factory=list)
    reason: str = ""  # populated by guardrails or validator failure summaries


def validate_claims(
    claims: list[GeneratedClaim],
    span_texts: dict[str, str],
    span_labels: dict[str, str] | None = None,
) -> list[ClaimValidation]:
    """Validate each claim's citations against the stored spans.

    `span_labels` carries each span's document label (issuer, form, accession,
    section). It is optional for backwards compatibility, but callers that have
    it should pass it: a label carries period information a claim may legitimately
    restate, and rule 5 reads it for the TEMPORAL check. It does NOT feed the
    numeric check beyond year-like values — see consistency.check_claim_consistency
    — and accession numbers are handled claim-side by consistency._IDENTIFIER
    rather than by donating evidence. Omitting labels makes the temporal check
    stricter than reality.
    """
    results: list[ClaimValidation] = []
    labels = span_labels or {}

    for i, claim in enumerate(claims):
        if not claim.citations:
            results.append(ClaimValidation(claim_index=i, support_status="unsupported", needs_review=True))
            continue

        citation_results: list[CitationResult] = []
        any_pass = False
        for span_id in claim.citations:
            text = span_texts.get(span_id)
            if text is None:
                citation_results.append(CitationResult(span_id=span_id, status="fail", reason="unknown span_id"))
                continue
            if claim.evidence_quote:
                if _normalize_ws(claim.evidence_quote) not in _normalize_ws(text):
                    citation_results.append(
                        CitationResult(
                            span_id=span_id,
                            status="fail",
                            reason="evidence_quote not found verbatim in cited span",
                        )
                    )
                    continue
            citation_results.append(CitationResult(span_id=span_id, status="pass"))
            any_pass = True

        # Rule 5: consistency against the UNION of the spans this claim cites.
        # Union, not per-citation, so a claim legitimately drawing one figure
        # from each of two spans is not rejected for splitting them.
        #
        # Span text and labels are kept SEPARATE: labels inform the temporal
        # check only. Folding them into one blob let a label's structural
        # integers ("10-Q Q1 · Item 2") satisfy numeric assertions no span
        # made — a loosening found in review.
        resolved = [s for s in claim.citations if s in span_texts]
        cited_text = " ".join(span_texts[s] for s in resolved)
        cited_labels = " ".join(labels.get(s, "") for s in resolved)
        inconsistencies = check_claim_consistency(claim, cited_text, cited_labels) if any_pass else []

        results.append(
            ClaimValidation(
                claim_index=i,
                support_status="supported" if (any_pass and not inconsistencies) else "flagged",
                needs_review=not any_pass or bool(inconsistencies) or claim.needs_review,
                citations=citation_results,
                reason="; ".join(inconsistencies),
            )
        )

    return results
