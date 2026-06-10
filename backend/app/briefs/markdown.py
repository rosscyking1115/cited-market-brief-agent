"""Markdown brief renderer + JSON citation manifest (plan §7 step 11, §3 exports).

Only SUPPORTED claims render in the body; flagged/unsupported claims appear in a
separate review section and never read as findings. Every export carries the
internal-draft watermark, the advice disclaimer, FRED attribution, and an
AI-generated marking (EU AI Act Art. 50 posture).
"""

import json
import re
from datetime import datetime, timezone
from typing import Any

from app.briefs.schemas import GeneratedBrief
from app.briefs.validator import ClaimValidation

_CLAIM_REF_RE = re.compile(r"\[#(\d+)\]")

DISCLAIMER = (
    "> **INTERNAL RESEARCH DRAFT — not approved for external use.** Factual, cited, "
    "non-personalized. Not investment advice, not a recommendation, and not an offer to "
    "buy or sell any security. AI-assisted content; human review required. Sources include "
    "SEC EDGAR and FRED® (this product uses the FRED® API but is not endorsed or certified "
    "by the Federal Reserve Bank of St. Louis)."
)


def _status_of(validations: list[ClaimValidation], index: int) -> ClaimValidation | None:
    return next((v for v in validations if v.claim_index == index), None)


def render_markdown(
    *,
    title: str,
    watchlist_name: str,
    brief: GeneratedBrief,
    validations: list[ClaimValidation],
    span_labels: dict[str, str],
    model: str,
    prompt_version: str,
    generated_at: datetime | None = None,
) -> str:
    ts = (generated_at or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M UTC")
    supported = {v.claim_index for v in validations if v.support_status == "supported"}

    lines: list[str] = [
        f"# {title}",
        "",
        f"*Watchlist: {watchlist_name} · generated {ts} · model `{model}` · "
        f"prompt `{prompt_version}` · {len(supported)}/{len(brief.claims)} claims validated*",
        "",
        DISCLAIMER,
        "",
    ]

    def _claim_chip(match: re.Match[str]) -> str:
        idx = int(match.group(1))
        if idx in supported:
            return f"[C-{idx:03d}](#evidence-ledger)"
        return f"⚑[C-{idx:03d} — flagged](#needs-review)"

    for section in brief.brief_sections:
        lines += [f"## {section.title}", "", _CLAIM_REF_RE.sub(_claim_chip, section.content_markdown), ""]

    # Evidence ledger — supported claims only
    lines += ["## Evidence ledger", ""]
    lines += ["| ID | Claim | Type | Sources | Validator |", "|---|---|---|---|---|"]
    for i, claim in enumerate(brief.claims):
        v = _status_of(validations, i)
        if v is None or v.support_status != "supported":
            continue
        sources = "; ".join(
            span_labels.get(c.span_id, c.span_id) for c in v.citations if c.status == "pass"
        )
        text = claim.text.replace("|", "\\|")
        lines.append(f"| C-{i:03d} | {text} | {claim.claim_type} | {sources} | ✓ PASS |")
    lines.append("")

    # Review queue — never rendered as findings
    flagged = [
        (i, c)
        for i, c in enumerate(brief.claims)
        if (_status_of(validations, i) or ClaimValidation(i, "flagged", True)).support_status
        != "supported"
    ]
    if flagged or brief.unsupported_claims:
        lines += ['<a id="needs-review"></a>', "## Needs review — not validated, do not cite", ""]
        for i, claim in enumerate(brief.claims):
            v = _status_of(validations, i)
            if v is not None and v.support_status == "supported":
                continue
            reason = (
                (v.reason if v else "")
                or "; ".join(
                    f"{c.span_id[:8]}…: {c.reason}" for c in (v.citations if v else []) if c.reason
                )
                or "no validated citation"
            )
            lines.append(f"- ⚑ **C-{i:03d}** {claim.text} — *{reason}*")
        for text in brief.unsupported_claims:
            lines.append(f"- ⚑ (model-flagged) {text}")
        lines.append("")

    if brief.open_questions:
        lines += ["## Analyst open questions", ""]
        lines += [f"- {q}" for q in brief.open_questions]
        lines.append("")

    return "\n".join(lines)


def build_citation_manifest(
    *,
    brief_id: str,
    watchlist_name: str,
    brief: GeneratedBrief,
    validations: list[ClaimValidation],
    span_meta: dict[str, dict[str, Any]],
    model: str,
    prompt_version: str,
    generated_at: datetime | None = None,
) -> str:
    """The audit artifact: machine-readable claim -> span -> source mapping."""
    manifest = {
        "format": "ledgerbrief.citation-manifest/v1",
        "ai_generated": True,  # EU AI Act Art. 50 machine-readable marking
        "brief_id": brief_id,
        "watchlist": watchlist_name,
        "generated_at": (generated_at or datetime.now(timezone.utc)).isoformat(),
        "model": model,
        "prompt_version": prompt_version,
        "claims": [
            {
                "id": f"C-{i:03d}",
                "text": claim.text,
                "type": claim.claim_type,
                "confidence": claim.confidence,
                "support_status": (
                    (_status_of(validations, i) or ClaimValidation(i, "unsupported", True)).support_status
                ),
                "citations": [
                    {
                        "span_id": c.span_id,
                        "validator": c.status,
                        "reason": c.reason,
                        **span_meta.get(c.span_id, {}),
                    }
                    for c in (_status_of(validations, i).citations if _status_of(validations, i) else [])
                ],
            }
            for i, claim in enumerate(brief.claims)
        ],
        "unsupported_claims": brief.unsupported_claims,
        "open_questions": brief.open_questions,
    }
    return json.dumps(manifest, indent=2, ensure_ascii=False)
