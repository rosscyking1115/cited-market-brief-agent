# Changelog

Notable changes to this project. Corrections to published claims get their own
heading and are never folded into a tidy-up — a visible correction reads as
trustworthy, a silent edit reads as nothing until someone finds the diff.

## Unreleased

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
