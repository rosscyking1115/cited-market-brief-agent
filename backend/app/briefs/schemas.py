"""Structured generation output (plan §7 step 7) and evidence-pack types.

The model NEVER invents citations: it may only reference span_ids present in the
evidence pack. The validator (validator.py) enforces this in the application layer.
"""

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """One retrievable span handed to the model."""

    span_id: str  # chunk UUID as string
    doc_label: str  # e.g. "NVDA 10-Q 0001045810-26-000089 · Item 1A"
    section: str | None = None
    text: str


class GeneratedClaim(BaseModel):
    text: str
    claim_type: str = Field(
        default="factual_summary",
        description="filing_change | macro_delta | risk | catalyst | factual_summary",
    )
    citations: list[str] = Field(default_factory=list, description="span_ids from the pack")
    confidence: str = "medium"  # high | medium | low
    evidence_quote: str = Field(default="", description="verbatim quote from the cited span supporting the claim")
    needs_review: bool = False


class BriefSection(BaseModel):
    title: str
    content_markdown: str = Field(
        description="Section prose; reference claims inline as [#N] where N is the claim index"
    )


class GeneratedBrief(BaseModel):
    brief_sections: list[BriefSection] = Field(default_factory=list)
    claims: list[GeneratedClaim] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
