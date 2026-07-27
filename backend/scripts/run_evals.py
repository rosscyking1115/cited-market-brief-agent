"""CI eval gate (plan §11).

Three things run here and they are not the same kind of thing:

1. GROUNDED EVAL (the gate), over two corpora. Scores the citation validator
   against independently labelled claims built from real filings.
     - "dev"     — the corpus the consistency rules were developed against.
     - "holdout" — authored AFTER those rules were frozen, over documents the
                   dev corpus never touched. This is the honest read on whether
                   the rules generalise. Never quote the dev number alone.
   Gated by a RATCHET at the measured level, not at the target: any regression
   fails, while progress stays possible. See RATCHET below.

2. NEGATIVE CONTROLS. Each deliberately breaks the pipeline and must score
   badly. If one passes, the eval has stopped measuring and the eval is what
   needs fixing. Blocking. Alongside them, KNOWN-HOLE PROBES: corruptions that
   SHOULD collapse the score and do not. Those are measured defects, printed so
   they cannot be forgotten.

3. SMOKE TEST (not a gate). The deterministic generator through the original
   harness. Its evidence_quote is copied out of the span it cites, so it scores
   1.000/1.000 by construction. It proves the pipeline runs; it measures nothing.

Usage (from backend/):
    python scripts/run_evals.py                  # everything
    python scripts/run_evals.py --smoke-only     # pipeline health, no measurement
    EVAL_USE_LLM=1 python scripts/run_evals.py   # also smoke-test the configured LLM
"""

import argparse
import os
import sys

from app.briefs.generator import generate_deterministic, generate_with_llm, llm_available
from app.evals.controls import CONTROLS, KNOWN_HOLE_PROBES
from app.evals.grounded import (
    ConfusionMatrix,
    GroundedReport,
    load_corpus,
    oracle_verdict,
    score_corpus,
    system_verdict,
)
from app.evals.harness import SMOKE_ONLY_WARNING, run_evals

# --------------------------------------------------------------------------
# The ratchet
#
# Floors are the CURRENTLY MEASURED figures, rounded down to three decimals —
# not the target. The rule is: when a number improves, raise its floor in the
# same commit. Lowering a floor is allowed but must say why in the commit
# message, because that is the move that turns a gate back into decoration.
#
# Precision AND recall are both ratcheted. A precision-only floor is trivially
# gamed by rejecting more, and the recall floor of 1.000 is the property that
# makes new checks safe to add: no check may start rejecting genuinely
# supported claims. Both corpora currently sit at recall 1.000 with zero false
# negatives, so that floor costs nothing today and would catch a real
# regression immediately.
#
# Last measured: 2026-07-27. Method and per-trap detail: docs/EVAL_METHODOLOGY.md
# --------------------------------------------------------------------------
RATCHET = {
    "dev": {"precision": 0.578, "recall": 1.000},
    "holdout": {"precision": 0.400, "recall": 1.000},
}

#: Where the citation checker should eventually get to. Not a gate — quoting
#: this as achieved performance is prohibited by docs/claims/claim-ledger.md.
TARGET_PRECISION = 0.95

#: Escape hatch for a deliberate, explained regression (e.g. a corpus rewrite).
#: Not for making a red build green.
ALLOW_REGRESSION = os.environ.get("EVAL_ALLOW_REGRESSION") == "1"


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _print_matrix(m: ConfusionMatrix, indent: str = "") -> None:
    print(f"{indent}precision: {_pct(m.precision)}   recall: {_pct(m.recall)}   f1: {_pct(m.f1)}")
    print(
        f"{indent}TP={m.true_positives}  FP={m.false_positives}  "
        f"FN={m.false_negatives}  TN={m.true_negatives}  (n={m.total})"
    )


def run_grounded(variant: str) -> tuple[GroundedReport, bool]:
    corpus = load_corpus(variant)
    floors = RATCHET[variant]

    print(f"\n=== Grounded citation-support eval — {variant} corpus ===")
    print(f"corpus v{corpus.version}: {len(corpus.claims)} labelled claims over {len(corpus.spans)} real spans")
    print(f"labels: {corpus.labelling['annotator']}")

    ceiling = score_corpus(corpus, oracle_verdict)
    if ceiling.matrix.precision != 1.0 or ceiling.matrix.recall != 1.0:
        print("FATAL: the oracle does not score 1.000/1.000 — the harness is broken, not the system.")
        return ceiling, False

    report = score_corpus(corpus, system_verdict)
    _print_matrix(report.matrix)

    hard = report.true_but_unsupported_refusal_rate
    print(f"\ntrue-but-unsupported refusal rate: {_pct(hard)}")
    print("  (claims that are TRUE but NOT supported by the span they cite,")
    print("   which the system correctly refused)")

    print("\nby trap:")
    for trap, matrix in sorted(report.per_trap.items()):
        if trap == "none":
            continue
        print(
            f"  {trap:26} caught {matrix.true_negatives}/{matrix.total}   (false positives: {matrix.false_positives})"
        )

    precision = report.matrix.precision or 0.0
    recall = report.matrix.recall or 0.0
    ok = precision >= floors["precision"] and recall >= floors["recall"]

    print(f"\nratchet: precision >= {floors['precision']:.3f}, recall >= {floors['recall']:.3f}")
    print(f"target (not a gate): precision {TARGET_PRECISION}")
    print("RESULT:", "PASS" if ok else "FAIL")
    if not ok:
        print("  REGRESSION against the last measured figures. Either the change made")
        print("  the checker worse, or it is a deliberate trade — in which case update")
        print("  RATCHET and say why in the commit message.")
    elif precision > floors["precision"] + 0.001:
        print(f"  Precision is above its floor ({precision:.3f} > {floors['precision']:.3f}).")
        print("  Raise RATCHET['" + variant + "']['precision'] in this commit to lock the gain in.")
    return report, ok


def run_controls() -> bool:
    corpus = load_corpus("dev")
    print("\n=== Negative controls ===")
    print("Each breaks the pipeline deliberately; the named metric must collapse.")
    all_ok = True
    for control in CONTROLS:
        report = score_corpus(control.apply(corpus), system_verdict)
        observed = getattr(report.matrix, control.metric)
        ok = observed is not None and observed <= control.ceiling
        all_ok &= ok
        status = "OK" if ok else "CONTROL FAILED"
        print(f"  {control.name:24} {control.metric}={_pct(observed)} (must be <= {control.ceiling})  {status}")
        if not ok:
            print(f"      {control.expectation}")
            print("      The eval did not notice a deliberately broken pipeline. Fix the eval.")

    if KNOWN_HOLE_PROBES:
        print("\n  Known-hole probes (corruptions that SHOULD collapse the score and do not):")
        baseline = score_corpus(corpus, system_verdict).matrix
        for probe in KNOWN_HOLE_PROBES:
            probed = score_corpus(probe.apply(corpus), system_verdict).matrix
            unchanged = (probed.precision, probed.recall) == (baseline.precision, baseline.recall)
            print(
                f"  {probe.name:24} precision={_pct(probed.precision)} recall={_pct(probed.recall)}"
                f"  {'UNCHANGED — hole open' if unchanged else 'score moved — hole may be closed'}"
            )
            print(f"      defect: {probe.defect}")
            print(f"      remedy: {probe.remedy}")

    print("RESULT:", "PASS" if all_ok else "FAIL")
    return all_ok


def run_smoke() -> bool:
    runs = [("deterministic/extractive-v1", generate_deterministic)]
    if os.environ.get("EVAL_USE_LLM") == "1" and llm_available():
        runs.append(("llm/configured", generate_with_llm))

    ok_all = True
    for label, fn in runs:
        report = run_evals(fn)
        # Advice-boundary leaks are a real gate even in smoke mode: unlike the
        # citation metrics, a leak cannot be produced by construction.
        ok = not report.advice_leaks
        ok_all &= ok
        print(f"\n=== Smoke run: {label} ===")
        print(SMOKE_ONLY_WARNING)
        print(f"  self-reported precision: {report.citation_precision:.3f}  (uninformative — see above)")
        print(f"  self-reported recall:    {report.citation_recall:.3f}  (uninformative — see above)")
        print(f"  advice_leaks:            {len(report.advice_leaks)} (real gate == 0)")
        for leak in report.advice_leaks:
            print(f"    LEAK: {leak}")
        for r in report.results:
            print(
                f"    case {r.name}: claims={r.claims} supported={r.supported} "
                f"quarantined={r.quarantined} citations={r.citations_pass}/{r.citations_total}"
            )
        print("RESULT:", "PASS" if ok else "FAIL")
    return ok_all


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-only", action="store_true", help="skip the grounded eval and controls")
    args = parser.parse_args()

    if args.smoke_only:
        return 0 if run_smoke() else 1

    # list(), not all(): a generator short-circuits on the first failure and the
    # holdout section would never print, showing half the picture on a red build.
    grounded_ok = all([run_grounded(variant)[1] for variant in RATCHET])
    controls_ok = run_controls()
    smoke_ok = run_smoke()

    print("\n=== Summary ===")
    print(f"  grounded eval:     {'PASS' if grounded_ok else 'FAIL'}  (blocking: ratchet)")
    print(f"  negative controls: {'PASS' if controls_ok else 'FAIL'}  (blocking)")
    print(f"  smoke:             {'PASS' if smoke_ok else 'FAIL'}  (blocking: advice leaks only)")

    failed = (not controls_ok) or (not smoke_ok) or (not grounded_ok and not ALLOW_REGRESSION)
    if not grounded_ok and ALLOW_REGRESSION:
        print("\n  EVAL_ALLOW_REGRESSION=1 — grounded regression demoted to a warning.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
