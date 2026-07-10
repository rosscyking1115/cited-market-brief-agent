"""Advice-boundary guardrails (plan §9, launch no-go gate).

The product is factual, cited, non-personalized. Claims containing recommendation,
suitability, target-price, allocation, or performance-promise language are
downgraded to FLAGGED regardless of citation status — they never render as
findings and never export.

v1 is a deliberately narrow pattern set (low false-positive bias). The Phase 5
red-team suite expands it; FINRA 2210 review happens before any external use.
"""

import re
from dataclasses import replace

from app.briefs.schemas import GeneratedClaim
from app.briefs.validator import ClaimValidation

ADVICE_PATTERNS: dict[str, re.Pattern[str]] = {
    "recommendation": re.compile(
        r"\b(?:strong\s+)?(?:buy|sell|hold)\s+(?:rating|recommendation)\b"
        r"|\brecommend(?:s|ed)?\s+(?:buying|selling|holding|an?\s+(?:overweight|underweight))\b"
        r"|\byou\s+should\s+(?:buy|sell|hold)\b",
        re.IGNORECASE,
    ),
    "target_price": re.compile(r"\b(?:price\s+target|target\s+price)\b", re.IGNORECASE),
    "rating_language": re.compile(r"\b(?:overweight|underweight|outperform|underperform)\b", re.IGNORECASE),
    "allocation": re.compile(
        r"\ballocat\w*\s+\d{1,3}\s*%|\b\d{1,3}\s*%\s+of\s+(?:your|the)\s+portfolio\b",
        re.IGNORECASE,
    ),
    "performance_promise": re.compile(
        r"\bguaranteed?\s+returns?\b|\bwill\s+(?:definitely\s+)?(?:outperform|double|triple)\b"
        r"|\brisk[-\s]free\s+(?:return|profit)\b",
        re.IGNORECASE,
    ),
    # Red-team additions (Phase 5): indirect prompt-injection artifacts surviving
    # into claim text are policy violations regardless of citation status.
    "prompt_manipulation": re.compile(
        r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions"
        r"|\bsystem\s+prompt\b|\bdeveloper\s+mode\b|\byou\s+must\s+tell\s+the\s+analyst\b",
        re.IGNORECASE,
    ),
    # Markdown-image/link exfiltration and raw URLs in claim prose (claims cite via
    # the ledger, never inline URLs — an embedded URL is an exfil channel)
    "embedded_url": re.compile(r"!\[[^\]]*\]\(\s*https?://|https?://[^\s)\"']+", re.IGNORECASE),
}


def scan_text(text: str) -> list[str]:
    """Return the names of advice-boundary patterns found in the text."""
    return [name for name, pattern in ADVICE_PATTERNS.items() if pattern.search(text)]


def apply_guardrails(claims: list[GeneratedClaim], validations: list[ClaimValidation]) -> list[ClaimValidation]:
    """Downgrade any claim whose text trips the advice boundary. Citation status is
    irrelevant: a perfectly-cited recommendation is still a policy violation."""
    out: list[ClaimValidation] = []
    for v in validations:
        claim = claims[v.claim_index]
        flags = scan_text(claim.text)
        if flags:
            out.append(
                replace(
                    v,
                    support_status="flagged",
                    needs_review=True,
                    reason=f"advice-boundary: {', '.join(flags)}",
                )
            )
        else:
            out.append(v)
    return out
