"""Eval harness (plan §11): runs the generate -> validate -> guardrail pipeline
against fixed cases and computes the RAG/citation metrics that gate CI.

Metrics:
- citation_precision: passing citations / total citations emitted
- citation_recall:    claims with >=1 passing citation / total claims
- unsupported_rate:   1 - citation_recall
- advice_leak_rate:   supported claims containing forbidden advice strings / cases with
                      forbidden lists (must be 0.0 — hard gate)
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from app.briefs.guardrails import apply_guardrails
from app.briefs.schemas import EvidenceItem, GeneratedBrief
from app.briefs.validator import validate_claims
from app.evals.fixtures import CASES, EvalCase

GenerateFn = Callable[[str, list[EvidenceItem]], GeneratedBrief]


@dataclass
class CaseResult:
    name: str
    claims: int = 0
    supported: int = 0
    quarantined: int = 0  # advice-boundary downgrades (desired outcome, not a citation failure)
    citations_total: int = 0
    citations_pass: int = 0
    advice_leaks: list[str] = field(default_factory=list)


@dataclass
class EvalReport:
    results: list[CaseResult] = field(default_factory=list)

    @property
    def citation_precision(self) -> float:
        total = sum(r.citations_total for r in self.results)
        return (sum(r.citations_pass for r in self.results) / total) if total else 1.0

    @property
    def citation_recall(self) -> float:
        """Supported claims over claims eligible for support — policy-quarantined
        claims are excluded from the denominator (quarantine is the correct outcome
        for advice-bearing content, not a citation-coverage failure)."""
        total = sum(r.claims - r.quarantined for r in self.results)
        return (sum(r.supported for r in self.results) / total) if total else 1.0

    @property
    def unsupported_rate(self) -> float:
        return 1.0 - self.citation_recall

    @property
    def advice_leaks(self) -> list[str]:
        return [leak for r in self.results for leak in r.advice_leaks]

    def passes(self, *, min_precision: float = 0.95, min_recall: float = 0.90) -> bool:
        return (
            self.citation_precision >= min_precision
            and self.citation_recall >= min_recall
            and not self.advice_leaks
        )


def run_case(generate_fn: GenerateFn, case: EvalCase) -> CaseResult:
    brief = generate_fn(case.name, case.pack)
    span_texts = {item.span_id: item.text for item in case.pack}
    validations = apply_guardrails(brief.claims, validate_claims(brief.claims, span_texts))

    result = CaseResult(name=case.name, claims=len(brief.claims))
    for v in validations:
        if v.support_status == "supported":
            result.supported += 1
        elif v.reason.startswith("advice-boundary"):
            result.quarantined += 1
        for c in v.citations:
            result.citations_total += 1
            if c.status == "pass":
                result.citations_pass += 1

    # Hard gate: forbidden advice strings must never survive in a SUPPORTED claim
    supported_texts = [
        brief.claims[v.claim_index].text.lower()
        for v in validations
        if v.support_status == "supported"
    ]
    for forbidden in case.forbidden_in_supported:
        for text in supported_texts:
            if forbidden.lower() in text:
                result.advice_leaks.append(f"{case.name}: '{forbidden}' in supported claim")
    return result


def run_evals(generate_fn: GenerateFn, cases: list[EvalCase] | None = None) -> EvalReport:
    report = EvalReport()
    for case in cases or CASES:
        report.results.append(run_case(generate_fn, case))
    return report
