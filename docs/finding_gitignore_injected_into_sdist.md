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

## Reached by a different route than the siblings — and the stated mechanism does not reproduce

This matters more than the leak, because it is the part that generalises.

A related finding written up in a sibling project
(`agent-release-gates`, `docs/finding_gitignore_not_a_packaging_control.md`)
states that hatchling reads `.gitignore` files it finds *inside* the project
and therefore ignores anything covered only by a contributor's **global**
gitignore. Four instances across two repositories were found that way.

**That mechanism does not reproduce here.** Hatchling found the repository-root
`.gitignore` — a file *outside* the declared project directory — and applied
every pattern in it. Asking the build backend directly for its own exclude
specification returns the repo-root patterns verbatim, `node_modules/` and
`/docs/PRODUCTION_PLAN.md` included, neither of which has anything to do with a
Python package in `backend/`.

So the sibling's rule — *in-project ignore files are honoured, ones above are
not* — is wrong as stated, or at least version- and layout-dependent. Do not
carry it forward as a fact. Carry forward the habit instead:

> **Do not reason about what your build backend selects. Build the artifact and
> read the file list.**

The correct general claim is weaker and more useful: **the set of files a build
backend packages is not the set of files your repository tracks, and the
relationship between them is not something you can derive by reading either one.**

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
