"""Grounded citation-support eval — scores the system against independent labels.

Why this exists
---------------
The original harness (harness.py) reports the system's own verdicts as if they
were metrics: `citation_precision` counts how often the validator said "pass".
Run against `generate_deterministic` — which sets `evidence_quote` to a slice of
the very span it cites — every citation passes by construction and the gate
reports 1.000/1.000. That is a self-report, not a measurement, and it cannot fail.

This module scores the system against ground-truth labels assigned by a human
reader who was not looking at the system's output. The unit is the claim, and
the question is a confusion matrix:

                       truth: supported     truth: not_supported
    system: supported        TP                    FP  <- the dangerous cell
    system: rejected         FN                    TN

`label` (does the CITED SPAN support this claim?) is recorded separately from
`world_truth` (is the claim true at all?), so the corpus can measure the failure
mode the literature calls hardest: a claim that is TRUE but is NOT supported by
the span it cites. A citation checker that only verifies quote provenance is
structurally blind to it — the quote is real, the span is real, and the claim
still does not follow.

The corpus is real: verbatim excerpts from public 10-Q filings and real FRED
vintages, with issuer, CIK, period and source SHA-256 recorded per span.
Labels are single-annotator and unreviewed; see corpus/README.md.
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.briefs.guardrails import apply_guardrails
from app.briefs.schemas import GeneratedClaim
from app.briefs.validator import validate_claims

CORPUS_DIR = Path(__file__).parent / "corpus"

#: (claims, span_texts, span_labels) -> one supported/not-supported verdict per claim.
#: Labels are part of the contract because they are part of the evidence bundle the
#: model was shown, and the consistency rules read them as cited evidence.
VerdictFn = Callable[[list[GeneratedClaim], dict[str, str], dict[str, str]], list[bool]]


def normalise(text: str) -> str:
    """Whitespace-normalised, case-folded — matches the validator's comparison."""
    return re.sub(r"\s+", " ", text).strip().lower()


@dataclass(frozen=True)
class CorpusSpan:
    span_id: str
    doc_label: str
    section: str
    text: str
    source: dict[str, Any]


@dataclass(frozen=True)
class LabelledClaim:
    claim_id: str
    text: str
    cited_span_ids: list[str]
    evidence_quote: str
    label: str  # supported | not_supported  <- ground truth
    world_truth: str  # true | false | unknown
    trap: str
    rationale: str
    annotator: str

    @property
    def truth_supported(self) -> bool:
        return self.label == "supported"

    def as_generated_claim(self) -> GeneratedClaim:
        return GeneratedClaim(
            text=self.text,
            citations=list(self.cited_span_ids),
            evidence_quote=self.evidence_quote,
        )


@dataclass(frozen=True)
class GroundedCorpus:
    version: str
    labelling: dict[str, Any]
    spans: list[CorpusSpan]
    claims: list[LabelledClaim]

    def span_texts(self) -> dict[str, str]:
        return {s.span_id: s.text for s in self.spans}

    def span_labels(self) -> dict[str, str]:
        return {s.span_id: s.doc_label for s in self.spans}


@dataclass(frozen=True)
class ClaimDecision:
    claim_id: str
    trap: str
    world_truth: str
    truth_supported: bool
    system_supported: bool

    @property
    def cell(self) -> str:
        if self.truth_supported:
            return "tp" if self.system_supported else "fn"
        return "fp" if self.system_supported else "tn"


@dataclass
class ConfusionMatrix:
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0

    def add(self, cell: str) -> None:
        setattr(self, _CELL_FIELD[cell], getattr(self, _CELL_FIELD[cell]) + 1)

    @property
    def total(self) -> int:
        return self.true_positives + self.false_positives + self.false_negatives + self.true_negatives

    @property
    def precision(self) -> float | None:
        """Of the claims the system called supported, how many really were.

        None when the system predicted no positives at all: precision is
        undefined there, and reporting 1.0 would flatter an abstaining system.
        """
        predicted = self.true_positives + self.false_positives
        return (self.true_positives / predicted) if predicted else None

    @property
    def recall(self) -> float | None:
        """Of the genuinely supported claims, how many the system accepted."""
        actual = self.true_positives + self.false_negatives
        return (self.true_positives / actual) if actual else None

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        if p is None or r is None or (p + r) == 0:
            return None
        return 2 * p * r / (p + r)


_CELL_FIELD = {
    "tp": "true_positives",
    "fp": "false_positives",
    "fn": "false_negatives",
    "tn": "true_negatives",
}


@dataclass
class GroundedReport:
    matrix: ConfusionMatrix = field(default_factory=ConfusionMatrix)
    per_trap: dict[str, ConfusionMatrix] = field(default_factory=dict)
    decisions: list[ClaimDecision] = field(default_factory=list)

    @property
    def true_but_unsupported_refusal_rate(self) -> float | None:
        """Of claims that are TRUE but NOT supported by the span they cite,
        the share the system correctly refused. This is the headline number:
        it isolates the failure mode a provenance-only checker cannot see."""
        hard = [d for d in self.decisions if d.world_truth == "true" and not d.truth_supported]
        if not hard:
            return None
        return sum(not d.system_supported for d in hard) / len(hard)

    def passes(self, *, min_precision: float, min_recall: float) -> bool:
        p, r = self.matrix.precision, self.matrix.recall
        if p is None or r is None:
            return False
        return p >= min_precision and r >= min_recall


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


#: variant -> (spans file, claims file)
#:
#: "dev" is the corpus the consistency rules were developed against. "holdout"
#: was authored AFTER those rules were frozen, over documents and sections the
#: dev corpus never touched, and is the only honest read on whether they
#: generalise. Report both; never quote the dev number alone as the system's
#: accuracy.
CORPUS_VARIANTS = {
    "dev": ("spans.json", "claims.json"),
    "holdout": ("holdout_spans.json", "holdout_claims.json"),
}


@lru_cache(maxsize=len(CORPUS_VARIANTS))
def load_corpus(variant: str = "dev") -> GroundedCorpus:
    try:
        spans_file, claims_file = CORPUS_VARIANTS[variant]
    except KeyError:
        raise ValueError(f"unknown corpus variant {variant!r}; expected one of {sorted(CORPUS_VARIANTS)}") from None

    spans_doc = json.loads((CORPUS_DIR / spans_file).read_text(encoding="utf-8"))
    claims_doc = json.loads((CORPUS_DIR / claims_file).read_text(encoding="utf-8"))

    if spans_doc["corpus_version"] != claims_doc["corpus_version"]:
        raise ValueError("spans.json and claims.json disagree on corpus_version")

    return GroundedCorpus(
        version=spans_doc["corpus_version"],
        labelling=claims_doc["labelling"],
        spans=[CorpusSpan(**s) for s in spans_doc["spans"]],
        claims=[LabelledClaim(**c) for c in claims_doc["claims"]],
    )


# --------------------------------------------------------------------------
# Verdict functions (the systems under test)
# --------------------------------------------------------------------------


def system_verdict(claims: list[GeneratedClaim], span_texts: dict[str, str], span_labels: dict[str, str]) -> list[bool]:
    """The shipped pipeline: deterministic validator + advice guardrails."""
    validations = apply_guardrails(claims, validate_claims(claims, span_texts, span_labels))
    return [v.support_status == "supported" for v in validations]


class _Oracle:
    """Sentinel verdict function that returns ground truth.

    Scoring it must produce 1.0/1.0. That is the ceiling check: it proves the
    harness can express a pass, which matters as much as being able to express
    a failure. An eval nothing can pass is as useless as one nothing can fail.
    """

    def __call__(
        self, claims: list[GeneratedClaim], span_texts: dict[str, str], span_labels: dict[str, str]
    ) -> list[bool]:
        raise RuntimeError("oracle_verdict must be passed to score_corpus, which supplies the labels")


oracle_verdict = _Oracle()


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------


def score_corpus(corpus: GroundedCorpus, verdict_fn: VerdictFn) -> GroundedReport:
    generated = [c.as_generated_claim() for c in corpus.claims]
    span_texts = corpus.span_texts()

    if isinstance(verdict_fn, _Oracle):
        verdicts = [c.truth_supported for c in corpus.claims]
    else:
        verdicts = verdict_fn(generated, span_texts, corpus.span_labels())

    if len(verdicts) != len(corpus.claims):
        raise ValueError(f"verdict_fn returned {len(verdicts)} verdicts for {len(corpus.claims)} claims")

    report = GroundedReport()
    for labelled, supported in zip(corpus.claims, verdicts, strict=True):
        decision = ClaimDecision(
            claim_id=labelled.claim_id,
            trap=labelled.trap,
            world_truth=labelled.world_truth,
            truth_supported=labelled.truth_supported,
            system_supported=bool(supported),
        )
        report.decisions.append(decision)
        report.matrix.add(decision.cell)
        report.per_trap.setdefault(labelled.trap, ConfusionMatrix()).add(decision.cell)
    return report


def with_claims(corpus: GroundedCorpus, claims: list[LabelledClaim]) -> GroundedCorpus:
    """Copy of the corpus carrying different claims — used by the controls."""
    return replace(corpus, claims=claims)


# --------------------------------------------------------------------------
# Corpus integrity
# --------------------------------------------------------------------------

#: Traps whose evidence_quote is deliberately NOT drawn from the cited span.
QUOTE_NOT_VERBATIM = frozenset({"fabricated_quote", "phantom_span", "no_citation", "empty_quote"})

#: Minimum size of the true-but-unsupported subset, and how many distinct shapes
#: it must take. A corpus that drops below either has stopped discriminating.
MIN_HARD_CASES = 6
MIN_HARD_TRAPS = 3


@dataclass(frozen=True)
class IntegrityViolation:
    rule: str
    subject: str
    message: str


def check_corpus_integrity(corpus: GroundedCorpus) -> list[IntegrityViolation]:
    """Structural checks on the labelled corpus itself.

    Separated out so the mutation suite can prove each rule fires when — and
    only when — it is violated. A corpus rule that never fails is the same
    category of mistake as an eval gate that never fails.
    """
    out: list[IntegrityViolation] = []
    known = {s.span_id for s in corpus.spans}
    texts = corpus.span_texts()

    seen: set[str] = set()
    for claim in corpus.claims:
        if claim.claim_id in seen:
            out.append(IntegrityViolation("unique_claim_ids", claim.claim_id, "duplicate claim_id"))
        seen.add(claim.claim_id)

        if claim.trap == "phantom_span":
            if set(claim.cited_span_ids) <= known:
                out.append(
                    IntegrityViolation("phantom_declared", claim.claim_id, "phantom trap cites only spans that exist")
                )
        else:
            missing = sorted(set(claim.cited_span_ids) - known)
            if missing:
                out.append(IntegrityViolation("cited_span_exists", claim.claim_id, f"cites unknown spans: {missing}"))

        if claim.trap not in QUOTE_NOT_VERBATIM:
            cited = " ".join(texts[s] for s in claim.cited_span_ids if s in texts)
            if not claim.evidence_quote:
                out.append(IntegrityViolation("quote_verbatim", claim.claim_id, "missing evidence_quote"))
            elif normalise(claim.evidence_quote) not in normalise(cited):
                out.append(
                    IntegrityViolation(
                        "quote_verbatim",
                        claim.claim_id,
                        "evidence_quote is not verbatim in the cited span, so the case would be "
                        "caught by provenance checking and proves nothing about entailment",
                    )
                )

    labels = {c.label for c in corpus.claims}
    if labels != {"supported", "not_supported"}:
        out.append(IntegrityViolation("both_labels_present", "corpus", f"labels present: {sorted(labels)}"))

    hard = [c for c in corpus.claims if c.world_truth == "true" and c.label == "not_supported"]
    if len(hard) < MIN_HARD_CASES:
        out.append(IntegrityViolation("hard_cases_present", "corpus", f"only {len(hard)} true-but-unsupported claims"))
    elif len({c.trap for c in hard}) < MIN_HARD_TRAPS:
        out.append(
            IntegrityViolation("hard_cases_present", "corpus", "true-but-unsupported claims are all the same shape")
        )

    meta = corpus.labelling
    if meta.get("inter_annotator_agreement") is not None or not str(meta.get("limits", "")).strip():
        out.append(
            IntegrityViolation(
                "labelling_limits_declared",
                "corpus",
                "single-annotator ground truth must declare its limits and claim no agreement statistic",
            )
        )

    for span in corpus.spans:
        if not span.source.get("sha256") or not span.source.get("issuer"):
            out.append(IntegrityViolation("span_provenance", span.span_id, "missing source hash or issuer"))

    return out
