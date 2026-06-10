"""ExportBundle: one review-state-aware data assembly shared by every format.

Review semantics (plan Phase 4):
- rejected sections are EXCLUDED from exports
- edited sections export the analyst's content, not the model draft
- flagged/unsupported claims never render as findings (review appendix only)
- watermark reflects approval state; Art. 50 AI marking on every format
"""

import re
from dataclasses import dataclass, field
from datetime import datetime

from app.briefs.schemas import GeneratedBrief
from app.briefs.validator import ClaimValidation

_CLAIM_REF_RE = re.compile(r"\[#(\d+)\]")

DISCLAIMER_TEXT = (
    "Internal research draft. Factual, cited, non-personalized. Not investment advice, "
    "not a recommendation, and not an offer to buy or sell any security. AI-assisted "
    "content (machine-readable marking embedded per EU AI Act Art. 50 posture); human "
    "review required before external use. Sources include SEC EDGAR and FRED® — this "
    "product uses the FRED® API but is not endorsed or certified by the Federal Reserve "
    "Bank of St. Louis."
)


@dataclass
class ExportSection:
    title: str
    content: str  # analyst-edited content when present
    action: str | None  # accept | edit | None (rejected sections never reach here)


@dataclass
class ExportClaim:
    cid: str  # C-000
    index: int
    text: str
    claim_type: str
    confidence: str
    support_status: str
    reason: str
    sources: list[str]  # human labels
    meta: list[dict]  # span_meta entries for passing citations


@dataclass
class ExportBundle:
    brief_id: str
    watchlist: str
    generated_at: datetime
    model: str
    prompt_version: str
    status: str  # draft | in_review | approved
    watermark: str
    approval_line: str | None
    sections: list[ExportSection] = field(default_factory=list)
    supported_claims: list[ExportClaim] = field(default_factory=list)
    review_claims: list[ExportClaim] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)

    @property
    def disclaimer(self) -> str:
        return DISCLAIMER_TEXT


def strip_claim_refs(text: str) -> str:
    """[#3] -> (C-003) for formats without anchors."""
    return _CLAIM_REF_RE.sub(lambda m: f"(C-{int(m.group(1)):03d})", text)


def build_bundle(
    *,
    brief_id: str,
    watchlist: str,
    generated_at: datetime,
    model: str,
    prompt_version: str,
    status: str,
    approved_by: str | None,
    approved_at: datetime | None,
    generated: GeneratedBrief,
    validations: list[ClaimValidation],
    span_labels: dict[str, str],
    span_meta: dict[str, dict],
    user_edits: dict,
) -> ExportBundle:
    if status == "approved" and approved_by:
        watermark = "APPROVED — INTERNAL USE ONLY"
        approval_line = (
            f"Approved by {approved_by}"
            + (f" on {approved_at.strftime('%Y-%m-%d %H:%M UTC')}" if approved_at else "")
        )
    else:
        watermark = "INTERNAL RESEARCH DRAFT — NOT APPROVED FOR EXTERNAL USE"
        approval_line = None

    section_edits = (user_edits or {}).get("sections", {})
    sections: list[ExportSection] = []
    for i, section in enumerate(generated.brief_sections):
        edit = section_edits.get(str(i))
        action = edit.get("action") if edit else None
        if action == "reject":
            continue
        content = (
            edit["content"]
            if action == "edit" and edit.get("content")
            else section.content_markdown
        )
        sections.append(ExportSection(title=section.title, content=content, action=action))

    by_index = {v.claim_index: v for v in validations}
    supported: list[ExportClaim] = []
    review: list[ExportClaim] = []
    for i, claim in enumerate(generated.claims):
        v = by_index.get(i)
        status_i = v.support_status if v else "unsupported"
        passing = [c for c in (v.citations if v else []) if c.status == "pass"]
        reason = (v.reason if v else "") or "; ".join(
            c.reason for c in (v.citations if v else []) if c.reason
        ) or ("" if status_i == "supported" else "no validated citation")
        export_claim = ExportClaim(
            cid=f"C-{i:03d}",
            index=i,
            text=claim.text,
            claim_type=claim.claim_type,
            confidence=claim.confidence,
            support_status=status_i,
            reason=reason,
            sources=[span_labels.get(c.span_id, c.span_id) for c in passing],
            meta=[{**span_meta.get(c.span_id, {}), "span_id": c.span_id} for c in passing],
        )
        (supported if status_i == "supported" else review).append(export_claim)

    return ExportBundle(
        brief_id=brief_id,
        watchlist=watchlist,
        generated_at=generated_at,
        model=model,
        prompt_version=prompt_version,
        status=status,
        watermark=watermark,
        approval_line=approval_line,
        sections=sections,
        supported_claims=supported,
        review_claims=review,
        open_questions=list(generated.open_questions),
    )
