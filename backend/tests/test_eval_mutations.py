"""Mutation suite: every guard in the grounded eval must fail when violated.

The repo previously shipped a citation gate that could not fail. Replacing it
with a different check is worth nothing unless the replacement is shown to bite.
So each mutation below breaks exactly one property and asserts that exactly the
corresponding guard fires — the same discipline as the invalid-manifest fixtures
in neobank-product-analytics.

Two families:
  - corpus integrity rules, via check_corpus_integrity
  - eval behaviour guards (anti-tautology, ceiling, negative controls)
"""

from dataclasses import replace

import pytest

from app.evals import controls as ctl
from app.evals.grounded import (
    GroundedCorpus,
    LabelledClaim,
    check_corpus_integrity,
    load_corpus,
    oracle_verdict,
    score_corpus,
    system_verdict,
    with_claims,
)

CORPUS = load_corpus()


def _claim(corpus: GroundedCorpus, claim_id: str) -> LabelledClaim:
    return next(c for c in corpus.claims if c.claim_id == claim_id)


def _swap(corpus: GroundedCorpus, claim_id: str, **changes) -> GroundedCorpus:
    """Corpus with one claim modified."""
    return with_claims(
        corpus,
        [replace(c, **changes) if c.claim_id == claim_id else c for c in corpus.claims],
    )


# --------------------------------------------------------------------------
# The corpus as shipped is clean
# --------------------------------------------------------------------------


def test_shipped_corpus_has_no_integrity_violations() -> None:
    violations = check_corpus_integrity(CORPUS)
    assert violations == [], "\n".join(f"{v.rule}: {v.subject}: {v.message}" for v in violations)


# --------------------------------------------------------------------------
# Corpus integrity rules — one mutation each, one expected rule each
# --------------------------------------------------------------------------


def _mutate_unknown_span(corpus: GroundedCorpus) -> GroundedCorpus:
    """Add an unresolvable span alongside the real one.

    Adding rather than replacing keeps the quote verbatim in the cited text, so
    this mutation isolates span resolution instead of also tripping quote_verbatim.
    """
    return _swap(corpus, "sup-nvda-gm", cited_span_ids=["nvda-gross-margin", "no-such-span"])


def _mutate_fabricated_quote_on_hard_case(corpus: GroundedCorpus) -> GroundedCorpus:
    """Break the property that makes the hard cases hard."""
    return _swap(corpus, "tbu-gm-cause-wrong-span", evidence_quote="A sentence that is not in the filing.")


def _mutate_phantom_that_resolves(corpus: GroundedCorpus) -> GroundedCorpus:
    return _swap(corpus, "str-phantom-span", cited_span_ids=["nvda-gross-margin"])


def _mutate_single_label(corpus: GroundedCorpus) -> GroundedCorpus:
    """Collapse the corpus onto one label.

    Collapsing onto not_supported rather than supported keeps the
    true-but-unsupported subset populated, so this isolates label balance.
    """
    return with_claims(corpus, [replace(c, label="not_supported") for c in corpus.claims])


def _mutate_drop_hard_cases(corpus: GroundedCorpus) -> GroundedCorpus:
    """Remove the true-but-unsupported subset — the corpus stops discriminating."""
    kept = [c for c in corpus.claims if not (c.world_truth == "true" and c.label == "not_supported")]
    return with_claims(corpus, kept)


def _mutate_claim_agreement_stat(corpus: GroundedCorpus) -> GroundedCorpus:
    """Claim an inter-annotator agreement figure that was never computed."""
    return replace(corpus, labelling={**corpus.labelling, "inter_annotator_agreement": 0.91})


def _mutate_strip_provenance(corpus: GroundedCorpus) -> GroundedCorpus:
    spans = [
        replace(s, source={**s.source, "sha256": ""}) if s.span_id == "nvda-gross-margin" else s for s in corpus.spans
    ]
    return replace(corpus, spans=spans)


def _mutate_duplicate_id(corpus: GroundedCorpus) -> GroundedCorpus:
    return with_claims(corpus, [*corpus.claims, corpus.claims[0]])


MUTATIONS = {
    "cited_span_exists": _mutate_unknown_span,
    "quote_verbatim": _mutate_fabricated_quote_on_hard_case,
    "phantom_declared": _mutate_phantom_that_resolves,
    "both_labels_present": _mutate_single_label,
    "hard_cases_present": _mutate_drop_hard_cases,
    "labelling_limits_declared": _mutate_claim_agreement_stat,
    "span_provenance": _mutate_strip_provenance,
    "unique_claim_ids": _mutate_duplicate_id,
}


@pytest.mark.parametrize(("expected_rule", "mutate"), sorted(MUTATIONS.items()))
def test_mutation_trips_exactly_its_own_rule(expected_rule: str, mutate) -> None:
    violations = check_corpus_integrity(mutate(CORPUS))
    rules = {v.rule for v in violations}
    assert expected_rule in rules, f"mutation did not trip {expected_rule}; got {sorted(rules)}"
    assert rules == {expected_rule}, f"mutation tripped extra rules: {sorted(rules - {expected_rule})}"
    assert all(v.message for v in violations), "every violation must carry a human-readable message"


def test_mutations_do_not_mutate_the_shipped_corpus() -> None:
    for mutate in MUTATIONS.values():
        mutate(CORPUS)
    assert check_corpus_integrity(CORPUS) == []


# --------------------------------------------------------------------------
# Behaviour guards
# --------------------------------------------------------------------------


def test_anti_tautology_guard_would_fire_on_a_perfect_system() -> None:
    """test_current_system_is_not_perfect must be capable of failing.

    Score a system that is right about everything: precision hits 1.0, which is
    exactly the condition that test treats as the alarm. If this ever stops
    holding, the anti-tautology guard has become unfalsifiable.
    """
    perfect = score_corpus(CORPUS, oracle_verdict)
    assert perfect.matrix.precision == 1.0
    assert perfect.matrix.false_positives == 0


def test_ceiling_guard_would_fire_on_a_broken_harness() -> None:
    """If the harness mislabelled ground truth, the oracle would stop scoring 1.0."""
    corrupted = with_claims(
        CORPUS,
        [replace(c, label="not_supported" if c.label == "supported" else "supported") for c in CORPUS.claims],
    )
    # The oracle follows the (now inverted) labels, so it still agrees with itself...
    assert score_corpus(corrupted, oracle_verdict).matrix.precision == 1.0
    # ...but the real system's score must move, proving the labels are load-bearing
    # and not decorative.
    baseline = score_corpus(CORPUS, system_verdict).matrix.precision
    inverted = score_corpus(corrupted, system_verdict).matrix.precision
    assert baseline != inverted, "inverting every label changed nothing — labels are not being read"


def test_neutered_control_is_detected() -> None:
    """A control that does not actually corrupt anything must fail its own ceiling."""
    neutered = ctl.NegativeControl(
        name="neutered",
        description="does nothing",
        metric="recall",
        ceiling=0.05,
        expectation="a control that corrupts nothing must not pass",
        apply=lambda corpus: corpus,
    )
    report = score_corpus(neutered.apply(CORPUS), system_verdict)
    observed = getattr(report.matrix, neutered.metric)
    assert observed is not None and observed > neutered.ceiling, (
        "a do-nothing control passed its ceiling — the control mechanism is not checking anything"
    )


@pytest.mark.parametrize("control", ctl.CONTROLS, ids=lambda c: c.name)
def test_each_control_changes_the_score_it_targets(control: ctl.NegativeControl) -> None:
    """The corruption must move the declared metric, not merely sit below a loose ceiling."""
    before = getattr(score_corpus(CORPUS, system_verdict).matrix, control.metric)
    after = getattr(score_corpus(control.apply(CORPUS), system_verdict).matrix, control.metric)
    assert before is not None
    assert after is None or after < before, f"{control.name}: {control.metric} did not fall ({before} -> {after})"
