"""Deterministic citation validator (plan §7 steps 8–10).

Application-layer enforcement — the model's claimed citations are checked against
stored spans:
1. A claim with no citations is UNSUPPORTED.
2. A citation referencing a span_id not in the evidence store FAILS.
3. If an evidence_quote is provided, it must appear verbatim (whitespace-normalized)
   in the cited span's text, otherwise the citation FAILS.
4. A claim is SUPPORTED if at least one citation passes; otherwise FLAGGED.

Flagged/unsupported claims never export (enforced at export time).
"""

import re
from dataclasses import dataclass, field

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
    claims: list[GeneratedClaim], span_texts: dict[str, str]
) -> list[ClaimValidation]:
    results: list[ClaimValidation] = []

    for i, claim in enumerate(claims):
        if not claim.citations:
            results.append(
                ClaimValidation(claim_index=i, support_status="unsupported", needs_review=True)
            )
            continue

        citation_results: list[CitationResult] = []
        any_pass = False
        for span_id in claim.citations:
            text = span_texts.get(span_id)
            if text is None:
                citation_results.append(
                    CitationResult(span_id=span_id, status="fail", reason="unknown span_id")
                )
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

        results.append(
            ClaimValidation(
                claim_index=i,
                support_status="supported" if any_pass else "flagged",
                needs_review=not any_pass or claim.needs_review,
                citations=citation_results,
            )
        )

    return results
