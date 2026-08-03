# The ignore file is part of the artifact

*A packaging allowlist scoped to the package root cannot exclude a file the build
backend fetches from above it.*

---

## Summary

Hatchling copies the repository's `.gitignore` into the source distribution it
builds. Not a rendering of it, not a summary — the file, with its entries and its
comments, as a member of the archive.

That is defensible on its own terms: the artifact records the exclusions it was
built under. The consequence is the part nobody plans for. **An ignore file is
written as private bookkeeping.** It is where a developer lists the things they
do not want in the repository, and the natural way to write it is to say why —
which means naming internal documents, internal processes, and occasionally
internal vocabulary. None of that is written to be read by a stranger.

In this project the packaged `.gitignore` named seven internal planning documents
by title and carried a comment written in internal release vocabulary.

The sharper structural point:

> **The file comes from outside the package root, so an allowlist scoped to the
> package root cannot exclude it.**

This repository's `pyproject.toml` lives in `backend/`. The allowlist there names
`/app`, `/tests`, `/scripts` and so on, and it fails closed correctly for
everything inside `backend/`. The `.gitignore` it packages lives one directory
up. No entry in the allowlist mentions it, no entry could, and it is packaged
anyway. `git ls-files` run from the package root does not list it either, so a
tracked-members test flags it as a stray without explaining why.

## Correction: the sibling finding's stated mechanism is false as written

**This section overturns existing text rather than adding to it.** Anyone lifting
the earlier note needs to read this first.

The finding written up in a sibling project (`agent-release-gates`,
`docs/finding_gitignore_not_a_packaging_control.md`) states its mechanism
precisely, and describes it as verified empirically rather than assumed:
hatchling reads `.gitignore` files it finds *inside* the project, does not
consult `core.excludesFile`, and therefore packages anything hidden only by a
contributor's **global** gitignore. Four instances across two repositories were
found by applying it.

**Observed here, that mechanism is false.** Hatchling read the **repository-root**
`.gitignore` — a file outside the declared project directory, one level above the
`pyproject.toml` it was building — and applied every pattern in it. Asking the
build backend for its own exclude specification returns the repo-root patterns
verbatim, including `node_modules/` and `/docs/PRODUCTION_PLAN.md`, neither of
which has anything to do with a Python package in `backend/`.

Do not carry the stated rule forward as a fact. The replacement claim is weaker,
and it survives:

> **The set of files a build backend packages is not the set of files your
> repository tracks, and the relationship between them cannot be derived by
> reading either one.**

Which leaves only one reliable practice: **build the artifact and read the file
list.**

### This is the second correction to that document, and they are different kinds

The first came out of the `telemeval` pass, which found that document's own audit
table wrong: the `telemeval` row records "local-only directories packaged: none"
across eight published sdists, and those sdists in fact carry an untracked
`.hypothesis/` cache. *(Recorded here as reported by that pass; not independently
re-verified in this repository.)*

The two failures are not the same shape, and the distinction is the point:

| | What was wrong | How it behaved |
|---|---|---|
| First correction | A **data row** — an audit result | Visibly wrong once anyone re-ran the audit |
| This correction | The **stated cause** | Invisible, because the conclusion it supports is correct |

A document that is right in its conclusion and wrong in its stated cause is a
specific and nasty failure mode. Nothing looks broken. The advice it gives —
declare an allowlist, inspect the artifact — is good advice, and following it
works. So the error is never contradicted by experience, and **everyone who
lifted the cause carried the error forward while the conclusion kept looking
right.** It only surfaces when someone reasons *from* the mechanism instead of
just obeying the conclusion — as happened here, where the expectation was that
`backend/` having no `.gitignore` of its own meant `.venv/` would be packaged,
and the artifact said otherwise.

Which is the general lesson worth more than either correction: **a conclusion
holding up is not evidence that the reason given for it is true.**

## The luck that was mistaken for a control

Before the allowlist, the sdist looked clean. It contained exactly the 122
git-tracked files under `backend/` and no local-only directory, despite `.venv/`
(489 MB, 19,226 files), `.data/`, `.pytest_cache/`, `.ruff_cache/` and
`.mypy_cache/` all sitting in the package root at build time.

Four of those five are named in the repository's `.gitignore`. The fifth is not.

**`.mypy_cache/` stays out of the artifact only because mypy writes its own
`.gitignore` inside itself**, containing `*`. Hatchling reads that file, because
it is in-project, and excludes the directory. Nothing the project decided
excluded it. If a future mypy release stopped writing that file, or if any other
tool wrote a cache directory without one, it would be packaged silently.

That is the whole finding in one line: **the sdist was clean by luck, and luck
that has already been observed to work is the hardest kind to notice.**

Demonstrated rather than argued — three untracked files dropped into the package
root, then the backend asked what it would select:

| | files selected |
|---|---|
| before | 122 |
| after `.probe_dotdir/`, `_probe_local_tooling/`, `probe_loose_file.md` | **125** |

`git status` showed all three as `??`. Nothing else objected.

## The remedy, and its one hole

An **allowlist**, because it fails closed. An exclude list stops what someone
thought to name and packages everything else; the next cache directory to appear
is published with no code change and no warning.

```toml
[tool.hatch.build.targets.sdist]
include = ["/app", "/tests", "/scripts", "/alembic", "/pyproject.toml"]
```

Then enforce it, because configuration nobody checks drifts. The strongest
assertion builds the sdist and requires **every member to be tracked by git** —
that stops the class rather than the instances, since local-only files are
untracked by construction and the rule needs no list of what anyone's tooling
happens to be called.

The hole is the file this document is about. The injected `.gitignore` is not
tracked *relative to the package root*, so it trips the tracked-members
assertion, and the allowlist cannot remove it. The honest resolution is a narrow,
documented exemption plus a second assertion that the exempted member is tracked
**somewhere in the repository** — a tracked file has been through review; an
untracked one is exactly what the suite exists to keep out.

Both live in [`backend/tests/test_sdist_contents.py`](../backend/tests/test_sdist_contents.py).

And then the part the test cannot do: **write the ignore file as though it
ships, because it does.** Entries are unavoidable. Comments are a choice.

## Check your own

Whatever backend you use, on any project:

```bash
python -m build --sdist --outdir /tmp/check .
```

```bash
tar tzf /tmp/check/*.tar.gz | sed 's|^[^/]*/||' | sort
```

Then read the list, and open anything you did not expect to be there:

```bash
tar xzOf /tmp/check/*.tar.gz --wildcards '*/.gitignore'
```

Reading that once is worth more than any amount of confidence about which ignore
files your backend consults.
