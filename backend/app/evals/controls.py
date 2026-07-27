"""Negative controls for the grounded eval.

A metric that only ever reports good news is not a measurement. Each control
deliberately breaks the pipeline in one way and declares which metric must
collapse as a result. If a control does NOT score badly, the eval is not
measuring anything and the gate is decorative.

Controls are scored against the UNMODIFIED ground truth: the question is not
"is the corrupted output self-consistent?" but "if the retriever broke in this
specific way, would the eval notice?".

Every control is deterministic — no RNG — so CI results are reproducible.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace

from app.evals.grounded import GroundedCorpus, LabelledClaim, normalise, with_claims

PHANTOM_PREFIX = "control-nonexistent-span-"


@dataclass(frozen=True)
class NegativeControl:
    name: str
    description: str
    #: attribute on ConfusionMatrix that this corruption must drive down
    metric: str
    #: the corrupted pipeline must score at or below this
    ceiling: float
    #: why this ceiling, in words
    expectation: str
    apply: Callable[[GroundedCorpus], GroundedCorpus]


# --------------------------------------------------------------------------
# 1. Shuffled citation mapping
# --------------------------------------------------------------------------


def _shuffle(corpus: GroundedCorpus) -> GroundedCorpus:
    """Repoint every citation at a span that demonstrably does not contain the quote.

    Simulates a retriever whose ranking is broken: real spans, real quotes,
    systematically mismatched. A correct checker must reject all of them, so
    recall against the original labels must go to zero.
    """
    span_ids = [s.span_id for s in corpus.spans]
    texts = corpus.span_texts()

    def repoint(original: str, quote: str) -> str:
        start = span_ids.index(original) if original in span_ids else 0
        needle = normalise(quote)
        for offset in range(1, len(span_ids)):
            candidate = span_ids[(start + offset) % len(span_ids)]
            # an empty quote is a substring of everything; any different span will do
            if not needle or needle not in normalise(texts[candidate]):
                return candidate
        raise RuntimeError(f"no span available that fails to contain the quote for {original}")

    claims = [
        replace(c, cited_span_ids=[repoint(s, c.evidence_quote) for s in c.cited_span_ids]) for c in corpus.claims
    ]
    return with_claims(corpus, claims)


shuffle_citations = NegativeControl(
    name="shuffle_citations",
    description="Every citation repointed at a span that does not contain its quote.",
    metric="recall",
    ceiling=0.05,
    expectation=(
        "No claim's citation can support it any more, so no genuinely supported claim "
        "should be accepted. Recall must go to zero. If it does not, the eval is "
        "reporting support that the evidence does not carry."
    ),
    apply=_shuffle,
)


# --------------------------------------------------------------------------
# 2. Retriever that returns plausible but non-verbatim quotes
# --------------------------------------------------------------------------

_FABRICATION_SUFFIX = " across every reporting segment."
_FABRICATED_WHEN_EMPTY = "The filing states this explicitly in the relevant section."


def _fabricate_quotes(corpus: GroundedCorpus) -> GroundedCorpus:
    """Replace every evidence_quote with plausible text that is NOT in the span.

    Simulates a model that paraphrases instead of quoting — the classic
    fabricated-evidence failure. The provenance check exists precisely for this,
    so recall against the original labels must go to zero. If it does not, the
    verbatim-quote rule has stopped working.
    """
    claims = [
        replace(
            c,
            evidence_quote=(c.evidence_quote + _FABRICATION_SUFFIX) if c.evidence_quote else _FABRICATED_WHEN_EMPTY,
        )
        for c in corpus.claims
    ]
    return with_claims(corpus, claims)


fabricate_all_quotes = NegativeControl(
    name="fabricate_all_quotes",
    description="Every evidence_quote replaced with plausible non-verbatim text.",
    metric="recall",
    ceiling=0.0,
    expectation=(
        "No quote appears verbatim in its span any more, so no claim can clear the "
        "provenance check and no genuinely supported claim should be accepted. This "
        "control replaced strip_evidence_quotes, which stopped discriminating once "
        "the consistency rules landed — see KNOWN_HOLE_PROBES below."
    ),
    apply=_fabricate_quotes,
)


# --------------------------------------------------------------------------
# 3. Citations that resolve to nothing
# --------------------------------------------------------------------------


def _phantom(corpus: GroundedCorpus) -> GroundedCorpus:
    """Replace every citation with an id that is not in the span store."""
    claims: list[LabelledClaim] = []
    for i, c in enumerate(corpus.claims):
        ids = [f"{PHANTOM_PREFIX}{i}-{j}" for j, _ in enumerate(c.cited_span_ids)]
        claims.append(replace(c, cited_span_ids=ids))
    return with_claims(corpus, claims)


phantom_spans = NegativeControl(
    name="phantom_spans",
    description="Every citation replaced with a span id absent from the store.",
    metric="recall",
    ceiling=0.0,
    expectation=(
        "Nothing resolves, so nothing can be supported. This is the easiest control "
        "and the shipped validator already handles it; it is here so that a "
        "regression in span resolution shows up as a scored failure rather than "
        "silently passing."
    ),
    apply=_phantom,
)


CONTROLS: list[NegativeControl] = [shuffle_citations, fabricate_all_quotes, phantom_spans]


# --------------------------------------------------------------------------
# Known-hole probes
#
# A corruption that SHOULD collapse the score but does not. These are not
# controls — they are measured defects, kept runnable so that fixing the defect
# is visible rather than silent. Retiring one requires the hole to be closed,
# not the expectation to be lowered.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class KnownHoleProbe:
    name: str
    description: str
    #: what the corruption fails to do, and why that is a defect
    defect: str
    #: what closing the hole would look like
    remedy: str
    apply: Callable[[GroundedCorpus], GroundedCorpus]


def _strip_quotes(corpus: GroundedCorpus) -> GroundedCorpus:
    return with_claims(corpus, [replace(c, evidence_quote="") for c in corpus.claims])


strip_evidence_quotes = KnownHoleProbe(
    name="strip_evidence_quotes",
    description="Citations kept, every evidence_quote removed.",
    defect=(
        "Removing every quote leaves the score completely unchanged. Two causes "
        "compound: validator rule 3 only runs the verbatim comparison `if "
        "claim.evidence_quote:`, so an empty quote skips provenance entirely; and "
        "the consistency rules read the claim text, not the quote. On this corpus "
        "the evidence_quote is therefore doing no work at all — every claim it "
        "would reject is already rejected on numeric or temporal grounds."
    ),
    remedy=(
        "Treat a missing evidence_quote as a failed citation rather than a skipped "
        "check. That is a provenance fix, not an entailment one, and it was left "
        "out of scope deliberately in the round that added the consistency rules."
    ),
    apply=_strip_quotes,
)

KNOWN_HOLE_PROBES: list[KnownHoleProbe] = [strip_evidence_quotes]
