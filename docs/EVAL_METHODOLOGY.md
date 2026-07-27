# Citation-support evaluation — methodology and measured baseline

*Last measured: 2026-07-27. Dev corpus v1.0.0, holdout corpus v1.0.0-holdout.*

## Summary

**How to read these numbers.** Unit: one claim. Positive: the system marks a
claim *supported*. Ground truth: a human label, recorded independently of the
system's output, answering "does the cited span support this claim?".
Population: every labelled claim in the named corpus.

- **precision** — of the claims the system accepted, the share the cited span
  really supports
- **recall** — of the claims the cited span really supports, the share the
  system accepted

A bare "precision 0.400" is uninterpretable: without the definition a reader
cannot tell whether it means 40% of accepted claims are supported or 40% of
rejections were correct, and those are opposite readings of the same system.
Preventing a number from travelling without the thing that makes it meaningful
is what this repository is for, so every public statement of these figures
carries the definition inline. `tests/test_public_claims.py` enforces it.

| | dev corpus | holdout corpus |
|---|---|---|
| citation precision | 0.579 | **0.400** |
| citation recall | 1.000 | 1.000 |
| false negatives | 0 | 0 |
| true-but-unsupported refusal rate | 0.750 | 0.333 |
| n | 31 | 28 |

**The figure that describes this system is precision 0.400 on the holdout
corpus**: of the claims it accepts, 40% are genuinely supported by the span they
cite and 60% are not. Recall 1.000 means it accepted every genuinely supported
claim, rejecting none. 0.579 is the dev corpus — the one the rules were built
against — and is never quoted on its own.

The validator checks **provenance** (where a quote came from) plus two
**consistency** rules (does the claim assert a quantity or a period the cited
evidence lacks). It does **not** check entailment. Claims whose defect is
semantic — "licensed to ship" read as "shipped", a real effect with an invented
cause, an all-time superlative from a three-week series — are accepted, and no
lexical rule reaches them.

Do not quote the dev figure alone as the system's accuracy. The holdout number
is the one that describes behaviour on documents the rules were not built
against, and it is lower.

## History

Round 1 found the gate was a tautology: `backend/scripts/run_evals.py` defaulted to
`generate_deterministic`, which copies its `evidence_quote` out of the span it
cites, and `validate_claims` passes a citation when that quote appears in that
span. The reported 1.000/1.000 was the system marking its own homework.
Replacing it with labelled ground truth put the real figure at **0.393**, with
**0 of 8** true-but-unsupported claims caught.

Round 2 added the two consistency rules and measured again. The deterministic
path is retained as a smoke test and prints its own uninformativeness.

## What the validator does now

Five rules, in `app/briefs/validator.py`:

1. No citations → UNSUPPORTED.
2. Citation naming an unknown `span_id` → FAILS.
3. Non-empty `evidence_quote` not appearing verbatim in the cited span → FAILS.
4. SUPPORTED if at least one citation passes.
5. Otherwise-supported claim FLAGGED if it fails a consistency check.

Rules 1–4 are provenance. Rule 5 (`app/briefs/consistency.py`) is two checks:

- **numeric** — every numeric literal in the claim must appear in the cited
  span text. Three kinds of token are skipped on the claim side, because they
  are identifiers rather than asserted quantities and comparing identifiers is
  a different rule: letter-fused tokens (`H200`, `10-Q`, `CPIAUCSL`), document
  identifiers (accession numbers, ISO dates), and document locators (`Item 8.01`,
  `Exhibit 99.1`).
- **temporal** — any fiscal-quarter ordinal, or month name **with a number next
  to it**, must appear in the cited evidence, allowing month-name ↔ `-MM-` for
  FRED series. The adjacency requirement exists because "may" is the commonest
  modal verb in filing prose; matching it bare rejected any hedged claim whose
  evidence happened not to contain the word. That was a live false-rejection
  path into the production pipeline, found in independent review and pinned by
  `backend/tests/test_consistency.py`.

Both run against the **union** of a claim's cited spans, so a claim legitimately
drawing one figure from each of two spans is not rejected for splitting them.

Document labels are handled asymmetrically and deliberately. They feed the
**temporal** check in full — a label legitimately carries period information —
but contribute only **year-like values** to the numeric check. Admitting a
label's structural integers (`10-Q Q1 · Item 2` yields 1, 2 and 10) would let a
claim assert quantities no span states; that loosening was found in review and
closed.

### Why only these two rules

Both are derivable without looking at the evaluation set: a factual claim about
a filing should not assert a number the filing does not state, nor attribute a
figure to a period the filing does not discuss. That matters, because a checker
tuned against the corpus that scores it reproduces the original tautology one
level up.

An open-ended named-entity rule was prototyped and **rejected**. It raised dev
precision to 0.727 but dropped recall to 0.727, wrongly rejecting three
genuinely supported claims, and every repair attempt amounted to fitting the
fixture. The cost of that trade is unacceptable under the recall floor below.

## Method

Claims are scored against ground-truth labels as a confusion matrix:

|                      | truth: supported | truth: not supported |
|----------------------|------------------|----------------------|
| **system: supported**    | TP               | FP ← the dangerous cell |
| **system: rejected**     | FN               | TN                   |

Each claim carries **`label`** (does the cited span support it?) separately from
**`world_truth`** (is it true at all?). Their intersection —
`world_truth = true` **and** `label = not_supported` — is the failure mode the
literature calls hardest, and the `true_but_unsupported_refusal_rate` isolates
it.

`precision` and `recall` are `None`, not `1.0`, when their denominator is empty;
an abstaining system should not be flattered by a vacuous score.

## The two corpora

**dev** (`backend/app/evals/corpus/spans.json`, `backend/app/evals/corpus/claims.json`) — 31 claims over 12 verbatim spans
from NVDA, AMD and AVGO 10-Qs and two FRED vintages. The consistency rules were
developed against it.

**holdout** (`backend/app/evals/corpus/holdout_spans.json`, `backend/app/evals/corpus/holdout_claims.json`) — 28 claims
over 8 spans: two 8-K filings, the second FRED vintage of each series, and
unused 10-Q sections.

It was authored after the rules were frozen and scored once — **attested by the
author, not corroborated.** Nothing committed establishes that ordering, and the
corpus and the rules share an author. Treat it as a stated procedure rather than
an audited property. Committing a holdout before touching the rules it will
judge would make the next round auditable for free; that was not done here.

Its independence is not total, and the exact overlap matters more than the
slogan. Three of the eight holdout spans share a source document **and section** with
a dev span: `ho-avgo-semis-operating-income` is a different passage of the same
AVGO 10-Q section, and the two FRED series are the same files at a different
vintage. Excluding the 8 claims citing them gives precision **0.429** against
the headline 0.400.

A second, tighter criterion gives a second number. Excluding spans whose source
file is byte-identical to a dev source — `ho-avgo-semis-operating-income` and
`ho-amd-datacenter-scope`, but not the FRED spans, whose sha256 differ because a
new vintage is genuinely new content — gives **0.438**. Both were reproduced
independently in review. Either way the overlap depresses the headline rather
than flattering it, which is why "documents the dev corpus never used" would
have been an overstatement and is not the wording used.

The holdout guards against tuning the checker to the fixture. It does **not**
guard against a blind spot shared by the checker's author and the corpus's
author, because they are the same author. It is a held-out test set, not an
independent replication.

## Results by trap

The holdout deliberately contains **no provenance-shaped traps** — no missing
citations, phantom spans, fabricated quotes or empty quotes. Those are the four
easy shapes the validator has always caught, and excluding them makes the
holdout harder by construction. Most of the 0.579 → 0.400 gap is that
composition difference, not a failure to generalise.

Compare only the shapes present in both:

| Trap | dev | holdout | reads as |
|---|---|---|---|
| `numeric_alteration` | 1/1 | **3/3** | the numeric rule generalises cleanly |
| `temporal_shift` | 1/1 | **3/3** | the temporal rule generalises cleanly |
| `wrong_span` | 3/4 | 2/4 | caught only when a quantity happens to differ |
| `partial_support` | 1/1 | 0/1 | dev case had a stray figure; holdout case did not |
| `modal_strength` | 0/2 | 0/3 | untouched — needs entailment |
| `causal_swap` | 0/1 | 0/1 | untouched |
| `unsupported_superlative` | 0/1 | 0/1 | untouched |

Holdout-only shapes, all uncaught, each a named limitation:

| Trap | Why it survives |
|---|---|
| `spelled_number` | "three-year" vs "five-year" — a numeric-literal rule cannot see a spelled-out quantity |
| `wrong_entity` | Wells Fargo named where the span says JPMorgan; no quantity or period differs |
| `vintage_mismatch` | Right value, wrong vintage attributed — the digits of the wrong vintage happen to appear elsewhere in the span |
| `fabricated_addition` | An invented item appended to an otherwise accurate list |

**The honest reading:** conditional on the shapes they target, the rules
generalise perfectly to unseen documents (6/6). Unconditionally, precision is
lower on the holdout because it is loaded with defects the rules were never
designed to catch. Both statements are true and neither alone is the headline.

### Recall held at 1.000 on unseen data

Zero false negatives on both corpora. The rules never rejected a genuinely
supported claim, including on documents they were not built against. That is the
property the recall ratchet protects, and it is the reason a further check
should only be added if it preserves it.

## The gate: a ratchet, not a target

Floors are the **measured** figures, not the aspiration:

```
RATCHET = {
    "dev":     {"precision": 0.578, "recall": 1.000},
    "holdout": {"precision": 0.400, "recall": 1.000},
}
TARGET_PRECISION = 0.95   # not a gate
```

Both precision and recall are ratcheted. A precision-only floor is gamed by
rejecting more; the recall floor of 1.000 is what makes new checks safe to add.
When a number improves, its floor is raised in the same commit —
`test_ratchet_floor_has_not_drifted_below_reality` fails if a gain is left
unlocked, and `test_ratchet_floor_is_not_above_the_measured_figures` fails on
regression. `EVAL_ALLOW_REGRESSION=1` demotes a grounded failure to a warning;
it is for a deliberate, explained trade, not for turning a red build green.

Advisory gating was dropped. An advisory gate is one people stop reading, which
is roughly how the original tautology survived.

## Negative controls

Each deliberately breaks the pipeline and must score badly.

| Control | Corruption | Metric | Ceiling | Observed |
|---|---|---|---|---|
| `shuffle_citations` | citations repointed at spans not containing their quote | recall | ≤ 0.05 | **0.000** |
| `fabricate_all_quotes` | every quote replaced with plausible non-verbatim text | recall | ≤ 0.00 | **0.000** |
| `phantom_spans` | every citation replaced with an absent span id | recall | ≤ 0.00 | **0.000** |

All deterministic — no RNG — so CI is reproducible.

### Known-hole probes

`strip_evidence_quotes` was a control in round 1. It no longer collapses
anything and has been **demoted, not re-tuned**:

> Removing every evidence quote leaves the score **completely unchanged**
> (precision 0.579, recall 1.000 — identical to the uncorrupted run).

Two causes compound. Rule 3 runs the verbatim comparison only
`if claim.evidence_quote:`, so an empty quote skips provenance entirely; and the
consistency rules read the claim text, not the quote. On this corpus the
`evidence_quote` is doing **no work at all** — every claim it would reject is
already rejected on numeric or temporal grounds.

The remedy is to treat a missing quote as a failed citation rather than a
skipped check. That is a provenance fix, deliberately left out of scope in the
round that added the consistency rules. It is pinned by
`test_known_hole_probe_still_shows_the_hole`, which fails when the hole closes.

Demotion is only legal with the defect and the remedy written down —
`test_a_control_is_never_silently_demoted` enforces that, because lowering a
ceiling is exactly how a control suite quietly loses its teeth.

## Guards on the eval itself

The eval can fail in two opposite ways and both are tested:

- **It cannot fail** — the original mistake. Guarded by
  `test_current_system_is_not_perfect` and the negative controls.
- **It cannot pass** — equally useless. Guarded by
  `test_oracle_scores_perfectly`: a verdict function returning ground truth must
  score 1.000/1.000.

`tests/test_eval_mutations.py` proves each corpus-integrity rule fires when, and
only when, it is violated — eight mutations, each tripping exactly one rule —
and that a do-nothing control fails its own ceiling.

## Type checking

A narrow mypy gate runs at `--strict` over the modules where a type error would
corrupt a reported number: the validator, the consistency rules, the eval
scoring path, and the script that prints the figures. Perimeter is
`[tool.mypy].files` in `backend/pyproject.toml`; it passed with zero errors on
first run. The rest of the backend is annotated but deliberately unchecked, and
no claim asserts otherwise. `tests/test_type_gate.py` proves the checker rejects
a wrong return type and that the perimeter still names the critical modules.

## Limits

- **Single-annotator ground truth, unreviewed, both corpora, same annotator.**
  No adjudication, no agreement statistic.
- **59 claims total.** Enough to show the rules generalise on the shapes they
  target and that the semantic residual is untouched; not enough for a precise
  effect size. No confidence intervals are offered.
- **One domain.** US large-cap semiconductor filings and two macro series.
- **The residual is real and named.** Modal strength, causal attribution,
  superlatives, spelled-out quantities, entity substitution and vintage
  attribution all pass today.
- **The temporal rule's date-shape requirement costs real detection, and the
  cost is not visible in either score.** A wrong-month claim that omits the year
  ("the index for May stood at 334.5", cited to a span saying June 2026) is no
  longer caught; with the year it is. The requirement exists because the month
  "May" collides with the commonest modal verb in filing prose, and a bare-month
  rule flagged properly-cited hedged claims — a false rejection, which is the
  worse direction. The trade is deliberate and it is a loss, not a free fix.
- **The numeric rule ignores tokens it classifies as identifiers or locators.**
  Accession numbers, zero-padded CIKs and filing locators ("Item 8.01") are
  skipped on the claim side. ISO dates are deliberately NOT skipped — treating
  them as identifiers made a wrong observation date invisible on FRED series,
  where every observation is ISO-dated, and that regression was caught in review
  rather than by either corpus.
- **The empty-quote provenance hole is open**, pinned by a probe.

## What this does not claim

Nothing here measures citation accuracy in any other domain, and the consistency
rules are not an entailment checker. Describing this system as verifying that
claims are supported by their sources is prohibited by
`docs/claims/claim-ledger.md`.
