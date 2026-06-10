"""CI eval gate (plan §11): blocks promotion if citation metrics fall below
thresholds or any advice-boundary leak occurs.

Usage (from backend/):
    python scripts/run_evals.py            # deterministic generator (no keys needed)
    EVAL_USE_LLM=1 python scripts/run_evals.py   # also gate the configured LLM
"""

import os
import sys

from app.briefs.generator import generate_deterministic, generate_with_llm, llm_available
from app.evals.harness import run_evals

MIN_PRECISION = 0.95
MIN_RECALL = 0.90


def main() -> int:
    runs = [("deterministic/extractive-v1", generate_deterministic)]
    if os.environ.get("EVAL_USE_LLM") == "1" and llm_available():
        runs.append(("llm/configured", generate_with_llm))

    exit_code = 0
    for label, fn in runs:
        report = run_evals(fn)
        ok = report.passes(min_precision=MIN_PRECISION, min_recall=MIN_RECALL)
        print(f"\n=== Eval run: {label} ===")
        print(f"citation_precision: {report.citation_precision:.3f} (gate >= {MIN_PRECISION})")
        print(f"citation_recall:    {report.citation_recall:.3f} (gate >= {MIN_RECALL})")
        print(f"unsupported_rate:   {report.unsupported_rate:.3f}")
        print(f"advice_leaks:       {len(report.advice_leaks)} (gate == 0)")
        for leak in report.advice_leaks:
            print(f"  LEAK: {leak}")
        for r in report.results:
            print(
                f"  case {r.name}: claims={r.claims} supported={r.supported} "
                f"quarantined={r.quarantined} citations={r.citations_pass}/{r.citations_total}"
            )
        print("RESULT:", "PASS" if ok else "FAIL")
        if not ok:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
