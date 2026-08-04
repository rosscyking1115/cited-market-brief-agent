# Changelog

Notable changes to this project. Corrections to published claims get their own
heading and are never folded into a tidy-up — a visible correction reads as
trustworthy, a silent edit reads as nothing until someone finds the diff.

## Unreleased

### Changed — the copy now says what the checks establish

The interface described the translated brief as a "reading aid", which implies a
verified relationship to the English source that nothing measured. The first fix
for that was the word "unevaluated", and in a user interface it went too far the
other way: the shape checks *do* run, and telling a reader nothing is checked is
its own inaccuracy.

Every surface now states what is established and what is not — structure and
citations checked automatically, wording not evaluated, review and approval tied
to the English original — fitted to the space each surface has. A button tooltip
carries only the limit; a panel carries all three clauses. No surface carries the
reassurance alone.

**The radar is not the brief, and the copy no longer pretends otherwise.**
`check_translation_shape` is reached only from `translate_brief_payload`;
`translate_news_items` calls nothing. Radar news translations therefore have no
automatic checks at all, and the radar footer, the Taiwan onboarding step and
`docs/MARKET_RADAR.md` say so plainly. `MARKET_RADAR.md` had the comparison
backwards — it said the caveat applied "more seriously" to the brief, when the
brief is now the better-guarded of the two.

Fifteen occurrences were found, not the five in the product code. The extra ten
included a Traditional Chinese string in the onboarding guide that an
English-language search cannot match, and claim 9 in the public claim ledger,
which quoted README wording that no longer existed and marked it Supported. Claim
9 is rewritten and claim 9a added for the radar's weaker position.

`docs/adr/0001-two-workspace-routes.md` keeps its Decision text unedited, because
an ADR records what was decided at the time. A note below it marks the superseded
phrase and points at the ledger.

### Removed

- `docs/screenshots/evidence-ledger.png` and `docs/screenshots/etf-attribution.png`.
  Both were referenced by nothing — not the README, not any document — and both
  rendered a single-shell interface from before the two-route split the README now
  leads with. Unreferenced is not unreachable: they are browsable in the
  repository, so a reader could meet an interface that no longer exists with
  nothing marking it historical. **An unreferenced stale screenshot is a claim
  nobody chose to make.** `docs/screenshots/brief-workspace.png` was re-captured
  against the new copy and verified by reading the image, not by trusting that
  the file changed.

### Corrected

- **The README claimed a backend suite of "122 backend tests". The real figure was
  410.** The number was wrong by a factor of more than three and had been on the
  public README since it was written. It has been removed rather than updated,
  along with the frontend counts beside it — those two were accurate (29 unit
  tests, 8 browser cases), but a count that routine work changes should not be
  published anywhere it cannot be regenerated. The suite total is now quoted only
  where running the suite prints it.

  No measured result depended on the figure. The citation precision and recall
  numbers were reproduced from a clean run during the same pass and are unchanged.

### Added

- **The always-accept baseline is now a column in the README's results table**,
  beside specificity and the true-but-unsupported refusal rate. Recall 1.000 and
  zero false negatives are reproduced exactly by a system that accepts every
  claim, so reported alone they do not separate this system from a null one. The
  figures that do — specificity 0.600 dev / 0.400 held-out against a null 0.000,
  and 6/8 and 2/6 true-but-unsupported refused against 0/8 and 0/6 — were already
  measured and were not being shown. No figure changed; the comparison that makes
  them judgeable was added.

  Recall 1.000 is kept and qualified: it means no genuinely supported claim in
  either corpus was refused, which is a property of these corpora rather than a
  guarantee.

- **A documented false negative.** The numeric rule is set-subset over
  canonicalised numeric literals, so a supported claim restating its span's own
  figure in equivalent notation is refused — `$5,000 million` against a span
  reading `$5.0 billion`. The README carries it beside the three examples of what
  the check wrongly *accepts*, and `backend/tests/test_consistency.py` pins it so
  it cannot silently stop being true if canonicalisation changes.

- **Shape enforcement on the translation path.** `SYSTEM_PROMPT` already required
  preserved citation markers and a sections array of the same length and order;
  nothing verified any of it. A translation that dropped both markers, dropped a
  section and asserted a gross margin the English draft never mentioned was
  parsed, schema-validated and returned normally with the review state untouched.

  Three mechanical checks now run — section count, citation markers per section
  position, and no numeric literal absent from the source — and a failure sets
  `requires_review` with the failed rule names. The translation is still
  returned: marked, not withheld. Each check was verified to fire on a distinct
  defect.

  These are shape guarantees and not a translation evaluation. The fidelity of
  the non-English output remains unmeasured and the README still says so.

- [`docs/finding_gitignore_injected_into_sdist.md`](docs/finding_gitignore_injected_into_sdist.md)
  — hatchling packages the repository-root `.gitignore`, a file from outside the
  package root that an allowlist scoped to that root cannot exclude.

  It also records a correction to a sibling project's finding: that document
  states hatchling reads only ignore files found *inside* the project, and that
  is false as written — hatchling read the repository-root file, one level above
  the package being built, and applied every pattern in it. The conclusion that
  document reaches is sound; the cause it gives for it is not, which is the
  harder failure to notice, because good advice that works never contradicts the
  wrong reason offered for it.

- An **sdist allowlist** in `backend/pyproject.toml`, with
  `backend/tests/test_sdist_contents.py` enforcing it. The strongest of its seven
  assertions builds the source distribution and requires every member to be
  tracked by git.

  The previous configuration declared no file selection at all, which left the
  repository's `.gitignore` acting as an exclude list — and an exclude list fails
  open. It happened to cover the local-only directories that exist in the package
  root today, but not by design: `.mypy_cache/` is absent from that file and stays
  out of the artifact only because mypy writes its own self-ignoring `.gitignore`.
  A probe that dropped three untracked files into the package root moved the sdist
  from 122 files to 125, one of them a dot-directory holding an absolute machine
  path. Nothing shipped — this package has never been published to a package
  index — and the mechanism is now closed.

- Module docstrings for `market_radar` and `fund_attribution`, the two modules a
  reader is most likely to open after the citation validator.

- A recorded docstring convention (`google`) in `backend/pyproject.toml`, with
  `D2`/`D4` enabled and `D1` deliberately off.

### Changed

- The README now leads with the citation-validation question and result, and links
  the Morning Market Radar rather than describing both products on one page. The
  radar moves to [`docs/MARKET_RADAR.md`](docs/MARKET_RADAR.md); setup,
  configuration, verification and the project map move to
  [`docs/DEVELOPING.md`](docs/DEVELOPING.md).

- The README now states plainly that the **Traditional Chinese and Korean output is
  unevaluated**. It previously described those versions as "reading aids", which
  implies a known relationship to the English source. No such relationship has been
  measured: nothing checks translation fidelity, claim preservation, or whether a
  citation still supports its claim after translation.

## v1.0.0 — 2026-07-17

First public release. Tagged `v1.0.0` at `f63d118`, published as a GitHub Release.
Not published to PyPI, then or since.
