"""Tests for the grounded citation-support eval.

The point of this file is to keep the eval honest. Two failure modes are being
guarded against, and they pull in opposite directions:

1. A gate that cannot fail (the tautology this eval replaces) — guarded by
   test_current_system_is_not_perfect and the negative controls.
2. A gate that cannot pass — guarded by test_oracle_scores_perfectly.

If either guard is ever deleted, the eval stops being a measurement.
"""

import json

import pytest

from app.briefs.schemas import GeneratedClaim
from app.briefs.validator import validate_claims
from app.evals import controls as ctl
from app.evals.grounded import (
    check_corpus_integrity,
    load_corpus,
    oracle_verdict,
    score_corpus,
    system_verdict,
)

CORPUS = load_corpus()


# --------------------------------------------------------------------------
# Corpus integrity
#
# The rules themselves live in check_corpus_integrity; test_eval_mutations.py
# proves each one fires when — and only when — it is violated.
# --------------------------------------------------------------------------


def test_corpus_passes_every_integrity_rule() -> None:
    violations = check_corpus_integrity(CORPUS)
    assert violations == [], "\n".join(f"{v.rule}: {v.subject}: {v.message}" for v in violations)


def test_corpus_is_large_enough_to_say_anything() -> None:
    assert len(CORPUS.claims) >= 25
    assert sum(c.label == "supported" for c in CORPUS.claims) >= 8
    assert len({s.source["issuer"] for s in CORPUS.spans}) >= 3, "corpus must span multiple issuers"


def test_labelling_limits_are_declared() -> None:
    """Single-annotator ground truth must say so in the artefact itself."""
    assert "single annotator" in CORPUS.labelling["annotator"].lower()


# --------------------------------------------------------------------------
# The harness can express a pass AND a fail
# --------------------------------------------------------------------------


def test_oracle_scores_perfectly() -> None:
    """A verdict function that returns ground truth must score 1.0/1.0.

    Guards the opposite failure from the tautology: an eval nothing can pass
    is as useless as one nothing can fail.
    """
    report = score_corpus(CORPUS, oracle_verdict)
    assert report.matrix.precision == 1.0
    assert report.matrix.recall == 1.0
    assert report.matrix.false_positives == 0


def test_always_supported_verdict_is_punished() -> None:
    """A degenerate 'everything is supported' system must score badly."""
    report = score_corpus(CORPUS, lambda claims, spans, labels: [True] * len(claims))
    assert report.matrix.recall == 1.0, "it does accept every supported claim"
    assert report.matrix.precision < 0.5, "but precision must collapse"


def test_always_rejecting_verdict_is_punished() -> None:
    report = score_corpus(CORPUS, lambda claims, spans, labels: [False] * len(claims))
    assert report.matrix.recall == 0.0


# --------------------------------------------------------------------------
# The measurement of the real system
# --------------------------------------------------------------------------


def test_current_system_is_not_perfect() -> None:
    """The anti-tautology test.

    The deterministic path scores 1.000/1.000 because the generator produces
    exactly what the validator checks. Against independently labelled claims
    the same validator must NOT score perfectly — if it ever does, either the
    validator gained entailment checking (good, update this test and say so) or
    the corpus stopped discriminating (bad, and this test is the alarm).
    """
    report = score_corpus(CORPUS, system_verdict)
    assert report.matrix.precision < 1.0, (
        "the grounded eval reported perfect precision — it is no longer measuring anything"
    )
    assert report.matrix.false_positives > 0


def test_system_catches_provenance_and_consistency_but_not_entailment() -> None:
    """Locates the gap precisely, three layers deep.

    Rewritten from the round-1 version, which asserted that the consistency
    cases were MISSED. They are now caught, which is the improvement the
    consistency rules were added for. The modal-strength residual is unchanged
    and is the honest remaining gap.
    """
    report = score_corpus(CORPUS, system_verdict)
    by_id = {d.claim_id: d for d in report.decisions}

    # Layer 1 — provenance. Caught before the consistency rules existed.
    for claim_id in ("str-no-citation", "str-phantom-span", "str-fabricated-quote"):
        assert not by_id[claim_id].system_supported, f"{claim_id} should be rejected"

    # Layer 2 — consistency. These were false positives in round 1.
    for claim_id in (
        "neg-dc-revenue-altered",  # numeric: $85.2bn is not in the span
        "neg-gm-wrong-quarter",  # temporal: span says first quarter
        "tbu-gm-cause-wrong-span",  # numeric: $4.5bn is not in the revenue span
        "tbu-amd-gm-cited-to-nvda",  # numeric: 53/50 are not in NVIDIA's span
    ):
        assert not by_id[claim_id].system_supported, f"{claim_id} regressed — the consistency rules should reject it"

    # Layer 3 — entailment. Still uncaught, and no lexical rule reaches these.
    # "granted licences that would allow us to ship" does not become "shipped",
    # and "expressed an expectation" does not become "is required to".
    for claim_id in ("neg-h200-shipped", "neg-usg-15pct-required"):
        assert by_id[claim_id].system_supported, (
            f"{claim_id} unexpectedly rejected — if the validator gained real "
            "entailment checking, rewrite this test to assert the improvement and "
            "update docs/EVAL_METHODOLOGY.md"
        )


def test_empty_evidence_quote_still_skips_the_provenance_check() -> None:
    """The empty-quote hole is unfixed; only its corpus symptom is now masked.

    `str-empty-quote` is rejected today, but by the numeric rule, not by
    provenance. The underlying defect — rule 3 running only
    `if claim.evidence_quote:` — is untouched, so a claim with no quote and no
    checkable quantities still sails through on span existence alone.
    """
    span_texts = {"s1": "Gross margin improved on a favourable product mix."}
    claim = GeneratedClaim(text="Gross margin improved.", citations=["s1"], evidence_quote="")
    [validation] = validate_claims([claim], span_texts)
    assert validation.support_status == "supported", (
        "an empty evidence_quote no longer yields automatic support — the "
        "provenance hole was closed; update this test and controls.KNOWN_HOLE_PROBES"
    )


def test_true_but_unsupported_refusal_rate_is_reported() -> None:
    report = score_corpus(CORPUS, system_verdict)
    rate = report.true_but_unsupported_refusal_rate
    assert rate is not None
    assert 0.0 <= rate <= 1.0


def test_per_trap_breakdown_covers_every_trap_in_the_corpus() -> None:
    report = score_corpus(CORPUS, system_verdict)
    corpus_traps = {c.trap for c in CORPUS.claims if c.trap != "none"}
    assert corpus_traps <= set(report.per_trap)


# --------------------------------------------------------------------------
# Negative controls — each must collapse exactly the metric it declares
# --------------------------------------------------------------------------


def test_controls_are_registered() -> None:
    names = {c.name for c in ctl.CONTROLS}
    assert {"shuffle_citations", "fabricate_all_quotes", "phantom_spans"} <= names


def test_a_control_is_never_silently_demoted() -> None:
    """Moving a control to KNOWN_HOLE_PROBES must carry its reasoning with it.

    That move is how a control suite quietly loses its teeth: a corruption stops
    collapsing the score, and the tempting fix is to lower the ceiling. Demotion
    is allowed, but only with the defect and the remedy written down.
    """
    for probe in ctl.KNOWN_HOLE_PROBES:
        assert probe.defect.strip(), f"{probe.name} demoted without stating the defect"
        assert probe.remedy.strip(), f"{probe.name} demoted without stating the remedy"
        assert probe.name not in {c.name for c in ctl.CONTROLS}


@pytest.mark.parametrize("control", ctl.CONTROLS, ids=lambda c: c.name)
def test_negative_control_scores_badly(control: ctl.NegativeControl) -> None:
    """A corrupted pipeline must be visible in the score.

    Controls are scored against the UNMODIFIED ground truth: the question is
    'if the retriever broke, would the eval notice?'. Vacuous agreement is the
    thing being ruled out.
    """
    corrupted = control.apply(CORPUS)
    report = score_corpus(corrupted, system_verdict)
    observed = getattr(report.matrix, control.metric)
    assert observed is not None, f"{control.name}: {control.metric} was undefined"
    assert observed <= control.ceiling, (
        f"{control.name}: {control.metric}={observed:.3f} exceeds ceiling "
        f"{control.ceiling} — the eval did not notice a deliberately broken pipeline"
    )


def test_shuffle_control_actually_moves_every_citation() -> None:
    shuffled = ctl.shuffle_citations.apply(CORPUS)
    before = {c.claim_id: c.cited_span_ids for c in CORPUS.claims}
    moved = 0
    for claim in shuffled.claims:
        if not before[claim.claim_id]:
            continue
        assert claim.cited_span_ids != before[claim.claim_id], f"{claim.claim_id} was not moved"
        moved += 1
    assert moved >= 25


def test_controls_do_not_mutate_the_loaded_corpus() -> None:
    snapshot = json.dumps([[c.claim_id, c.cited_span_ids, c.evidence_quote] for c in CORPUS.claims])
    for control in ctl.CONTROLS:
        control.apply(CORPUS)
    after = json.dumps([[c.claim_id, c.cited_span_ids, c.evidence_quote] for c in CORPUS.claims])
    assert snapshot == after


# --------------------------------------------------------------------------
# The deterministic path is a smoke test, not a measurement
# --------------------------------------------------------------------------


def test_deterministic_path_is_labelled_as_a_smoke_test() -> None:
    from app.evals import harness

    assert "smoke" in harness.SMOKE_ONLY_WARNING.lower()
    assert "not a measurement" in harness.SMOKE_ONLY_WARNING.lower()


def test_grounded_claims_convert_to_generated_claims() -> None:
    claim = CORPUS.claims[0].as_generated_claim()
    assert isinstance(claim, GeneratedClaim)
    assert claim.citations == CORPUS.claims[0].cited_span_ids


# --------------------------------------------------------------------------
# Known-hole probes — corruptions that SHOULD collapse the score but do not
# --------------------------------------------------------------------------


@pytest.mark.parametrize("probe", ctl.KNOWN_HOLE_PROBES, ids=lambda p: p.name)
def test_known_hole_probe_still_shows_the_hole(probe: ctl.KnownHoleProbe) -> None:
    """Pin the defect so that closing it is visible rather than silent.

    If this test starts failing, that is good news: the hole was closed. Move the
    probe back into CONTROLS with a ceiling and record the change.
    """
    baseline = score_corpus(CORPUS, system_verdict).matrix
    probed = score_corpus(probe.apply(CORPUS), system_verdict).matrix
    assert (probed.precision, probed.recall) == (baseline.precision, baseline.recall), (
        f"{probe.name} now changes the score, so the hole appears to be closed. Remedy on record was: {probe.remedy}"
    )


# --------------------------------------------------------------------------
# The ratchet must track reality
# --------------------------------------------------------------------------


def _ratchet() -> dict:
    """Import the gate floors from the CI script without executing main()."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts" / "run_evals.py"
    spec = importlib.util.spec_from_file_location("run_evals", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.RATCHET


@pytest.mark.parametrize("variant", ["dev", "holdout"])
def test_ratchet_floor_is_not_above_the_measured_figures(variant: str) -> None:
    """A floor above reality is a permanently red build."""
    matrix = score_corpus(load_corpus(variant), system_verdict).matrix
    floors = _ratchet()[variant]
    assert matrix.precision is not None and matrix.recall is not None
    assert matrix.precision >= floors["precision"], (
        f"{variant}: measured precision {matrix.precision:.3f} is below its ratchet floor "
        f"{floors['precision']:.3f} — this is the regression the ratchet exists to catch"
    )
    assert matrix.recall >= floors["recall"], (
        f"{variant}: measured recall {matrix.recall:.3f} is below its ratchet floor "
        f"{floors['recall']:.3f} — a new check is rejecting genuinely supported claims"
    )


@pytest.mark.parametrize("variant", ["dev", "holdout"])
def test_ratchet_floor_has_not_drifted_below_reality(variant: str) -> None:
    """An unraised floor is a gate that slowly stops meaning anything.

    Tolerance is 0.01: enough that a floor may be recorded rounded down, not
    enough for a real improvement to go unlocked.
    """
    matrix = score_corpus(load_corpus(variant), system_verdict).matrix
    floors = _ratchet()[variant]
    assert matrix.precision is not None
    assert matrix.precision - floors["precision"] <= 0.01, (
        f"{variant}: precision improved to {matrix.precision:.3f} but the floor is still "
        f"{floors['precision']:.3f}. Raise it in this commit to lock the gain in."
    )


def test_holdout_is_genuinely_disjoint_from_dev() -> None:
    """The holdout only means anything if it shares no spans with the dev corpus."""
    dev = {s.span_id for s in load_corpus("dev").spans}
    holdout = {s.span_id for s in load_corpus("holdout").spans}
    assert dev.isdisjoint(holdout), f"overlapping spans: {sorted(dev & holdout)}"

    dev_files = {(s.source["file"], s.source["sha256"]) for s in load_corpus("dev").spans}
    holdout_files = {(s.source["file"], s.source["sha256"]) for s in load_corpus("holdout").spans}
    shared = dev_files & holdout_files
    # Sharing a source FILE is acceptable (different sections of the same 10-Q);
    # sharing a span is not. Record which files overlap so the limit is visible.
    assert len(shared) < len(holdout_files), "holdout draws on no source the dev corpus lacks"


def test_holdout_corpus_passes_every_integrity_rule() -> None:
    violations = check_corpus_integrity(load_corpus("holdout"))
    assert violations == [], "\n".join(f"{v.rule}: {v.subject}: {v.message}" for v in violations)


#: Holdout spans that knowingly share a source document AND section with a dev
#: span. Disclosed in docs/EVAL_METHODOLOGY.md and the corpus card, because the
#: holdout's whole value is the independence claim and an undisclosed overlap
#: would quietly weaken it. Excluding the claims citing these gives precision
#: 0.429 against the headline 0.400 — the overlap depresses the figure.
DISCLOSED_SECTION_OVERLAP = {
    "ho-avgo-semis-operating-income",
    "ho-fred-cpiaucsl-v20260612",
    "ho-fred-dgs10-v20260611",
}


def test_holdout_overlap_with_dev_is_exactly_what_is_disclosed() -> None:
    """A NEW overlap must fail, not silently erode the independence claim."""
    dev_pairs = {(s.source["file"], s.section) for s in load_corpus("dev").spans}
    actual = {s.span_id for s in load_corpus("holdout").spans if (s.source["file"], s.section) in dev_pairs}
    assert actual == DISCLOSED_SECTION_OVERLAP, (
        f"holdout/dev section overlap changed: {sorted(actual)}. Amend the disclosure in "
        "docs/EVAL_METHODOLOGY.md, backend/app/evals/corpus/README.md and claim-ledger 10c "
        "first — the independence claim is load-bearing."
    )


def test_holdout_spans_are_not_near_duplicates_of_dev_spans() -> None:
    """Span-id disjointness is trivially satisfied by the `ho-` prefix.

    Check the text too: a holdout span that merely renames a dev span would
    make the held-out figure meaningless while passing an id-based check.
    """
    dev_texts = [s.text for s in load_corpus("dev").spans]
    for span in load_corpus("holdout").spans:
        for dev_text in dev_texts:
            assert span.text not in dev_text and dev_text not in span.text, f"{span.span_id} duplicates dev span text"
