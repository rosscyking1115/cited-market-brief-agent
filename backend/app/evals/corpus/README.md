# Grounded citation-support corpora

Two corpora live here and they play different roles. **Quote the holdout figure,
not the dev figure**, when describing how the system performs.

## How to read the numbers these corpora produce

Unit: one claim. Positive: the system marks a claim *supported*. Ground truth: a
human label, recorded independently of the system's output, answering "does the
cited span support this claim?". Population: every labelled claim in the named
corpus.

- **precision** — of the claims the system accepted, the share the cited span
  really supports
- **recall** — of the claims the cited span really supports, the share the
  system accepted

Current figures: **precision 0.400 on the holdout** (of the claims the system
accepts, 40% are genuinely supported and 60% are not), 0.579 on the dev corpus,
recall 1.000 on both with zero false negatives. Never state either figure
without this definition — `backend/tests/test_public_claims.py` enforces that.

| Variant | Files | Role |
|---|---|---|
| `dev` | `spans.json`, `claims.json` | 31 claims / 12 spans. The consistency rules in `app/briefs/consistency.py` were developed against it. |
| `holdout` | `holdout_spans.json`, `holdout_claims.json` | 28 claims / 8 spans. Authored **after** those rules were frozen, from sources the dev corpus largely did not use. Scored once. See the overlap note below. |

Load with `load_corpus("dev")` / `load_corpus("holdout")`.

## The holdout, and what it is worth

Sources: an AMD 8-K (a $5.0bn revolving credit facility), a Broadcom 8-K (debt
tender offers), the second FRED vintage of each series, and unused 10-Q
sections. `test_holdout_is_genuinely_disjoint_from_dev` enforces that no span is
shared.

**The independence is partial, and the exact overlap is stated rather than
glossed.** Three of the eight holdout spans share a source document *and
section* with a dev span: `ho-avgo-semis-operating-income` is a different
passage of the same AVGO 10-Q section, and the two FRED series are the same
files at a different vintage. Excluding the 8 claims citing them gives precision
0.429 against the headline 0.400. On the tighter criterion of byte-identical
source content (which excludes `ho-amd-datacenter-scope` but not the new FRED
vintages) the figure is 0.438. Either way the overlap depresses the headline
rather than flattering it.

**"Authored after the rules were frozen, scored once" is an author attestation,
not an audited fact.** No commit ordering corroborates it, and the corpus and
the rules share an author. Committing a holdout before touching the rules it
judges would make this auditable; that was not done here.

It deliberately contains **no provenance-shaped traps** — no missing citations,
phantom spans, fabricated quotes or empty quotes. Those are the easy shapes the
validator has always caught, and excluding them makes the holdout harder by
construction. Most of the dev→holdout precision gap is that composition
difference rather than a failure to generalise; the per-shape comparison in
`docs/EVAL_METHODOLOGY.md` separates the two.

**What it guards against:** tuning the checker to the fixture that scores it.
**What it does not guard against:** a blind spot shared by the checker's author
and the corpus's author — they are the same author. This is a held-out test set,
not an independent replication.

---

# Development corpus v1.0.0

A small, hand-labelled evaluation set for one question: **does the span a claim
cites actually support that claim?**

It exists because the gate it replaces could not fail. `scripts/run_evals.py`
defaulted to `generate_deterministic`, whose docstring says its output is
"citation-perfect by construction" — it copies its `evidence_quote` out of the
span it cites, and the validator's check is whether the quote appears in that
span. The recorded 1.000/1.000 was the system marking its own homework.

## Files

| File | What it is |
|---|---|
| `spans.json` | 12 evidence spans, verbatim, from real source documents |
| `claims.json` | 31 claims with ground-truth labels, rationales and trap taxonomy |

## Sources — all real, none synthetic

| Document | Issuer | CIK | Period | Spans |
|---|---|---|---|---|
| `nvda-20260426.htm` | NVIDIA Corporation | 0001045810 | 10-Q, Q1 FY2027 | 6 |
| `amd-20260328.htm` | Advanced Micro Devices, Inc. | 0000002488 | 10-Q, Q1 2026 | 2 |
| `avgo-20260503.htm` | Broadcom Inc. | 0001730168 | 10-Q, Q2 FY2026 | 2 |
| `CPIAUCSL.txt` | FRED | — | vintage 2026-06-11 | 1 |
| `DGS10.txt` | FRED | — | vintage 2026-06-12 | 1 |

Each span records the SHA-256 of the whole cached source file it was cut from,
so any excerpt can be traced back and re-verified. Span text was extracted
mechanically, not retyped, so it is verbatim including the filings' own
punctuation. The corpus JSON is committed because `.data/` is gitignored — CI
needs neither the cache nor the network.

## The two label fields, and why there are two

- **`label`** — *does the cited span, on its own, support this claim?*
  `supported` | `not_supported`. This is the ground truth being scored.
- **`world_truth`** — *is the claim true at all?* `true` | `false` | `unknown`.

Keeping them apart is the entire point. The intersection
`world_truth = true` **and** `label = not_supported` is the failure mode the
literature calls hardest and the one this system exists to catch: a claim that
is perfectly true, carries a genuine verbatim quote from a real span, and still
is not supported by the span it points at. There are 8 such claims here.
A checker that verifies quote provenance rather than entailment is structurally
blind to every one of them.

## Trap taxonomy

| Trap | Shape | n |
|---|---|---|
| `wrong_span` | True, stated elsewhere in the corpus, cited to a span that does not say it | 4 |
| `insufficient_span` | Derived or comparative claim; one of its inputs is not in the cited span | 2 |
| `modal_strength` | "licensed to ship" → "shipped"; "expectation" → "requirement" | 2 |
| `missing_observation` | Series claim spanning a `.` gap in the cited FRED vintage | 2 |
| `cross_issuer` | True of one issuer, cited to another issuer's filing | 1 |
| `partial_support` | Half the claim is in the cited span, half is not | 1 |
| `causal_swap` | Real effect, cause the span does not give | 1 |
| `temporal_shift` | Right figure, wrong period | 1 |
| `numeric_alteration` | One digit changed against a verbatim quote that contradicts it | 1 |
| `unsupported_superlative` | Span carries no series, claim asserts an all-time high | 1 |
| `no_citation` / `phantom_span` / `fabricated_quote` / `empty_quote` | Provenance-shaped controls the shipped validator already handles | 4 |

The provenance-shaped traps are deliberately included as easy cases. They are
the contrast that localises the gap: the system catches those and misses
everything else.

## Labelling limits — read this before quoting a number

- **Single annotator, unreviewed.** Labels were assigned by `claude-opus-5` in
  one pass on 2026-07-27. No second reader, no adjudication.
- **No inter-annotator agreement statistic.** None was computed, so none is
  claimed. `inter_annotator_agreement` is `null` in `claims.json` and the
  integrity check fails if anything ever populates it without the work behind it.
- **Labels are auditable, not authoritative.** Every claim carries a `rationale`
  and its cited span is in `spans.json`, so any label can be checked in about a
  minute. Disagreement with a label is a defect report against the corpus, not
  against the system under test — please file it that way.
- **Small.** 31 claims over 12 spans across 3 issuers. Enough to size a gap;
  nowhere near enough for a precise effect size, and no confidence intervals are
  offered. (The round-1 figure of 0/8 hard cases caught is superseded: the
  consistency rules now catch 6/8 on this corpus and 2/6 on the holdout.)
- **One domain.** US large-cap semiconductor filings plus two macro series.
  Nothing here generalises to other domains, and it is not meant to.

## Adding to the corpus

New claims must keep `check_corpus_integrity` green. In particular a hard case
must carry an evidence quote that really is verbatim in the span it cites —
otherwise it collapses into the easy "quote not found" category and proves
nothing about entailment. `tests/test_eval_mutations.py` proves each integrity
rule fires when violated; keep it that way.
