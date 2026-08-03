"""The source distribution may contain only files git tracks.

An sdist is built from the *directory*, not from the git index. Whatever is
sitting in the package root when someone runs a build is a candidate for
publication, and a publication cannot be recalled.

The usual defence is an ignore file, and here it is doing less than it appears
to. This project's `.gitignore` lives one level up, at the repository root, and
it does cover the directories that happen to exist in `backend/` today —
`.venv/`, `.data/`, `.pytest_cache/`, `.ruff_cache/`. But `.mypy_cache/` is not
in it. That directory stays out of the artifact only because mypy writes its own
self-ignoring `.gitignore` inside itself. Nothing the project controls excluded
it, and nothing would exclude the next such directory: a probe that dropped
three untracked files into the package root moved the selection from 122 files
to 125, one of them a dot-directory carrying an absolute machine path.

That is what an exclude list does. It stops what someone thought to name and
fails open on everything else. The allowlist in `pyproject.toml` fails closed
instead.

Four properties are pinned, in ascending order of strength:

1. The selection stays an allowlist. Deleting it restores the fail-open
   behaviour, which is the regression that arms the defect.
2. No allowlist entry names a directory that is local-only for anyone.
3. Every allowlist entry still matches a tracked file, so a stale entry surfaces
   rather than hiding drift.
4. **Every member of the built sdist is git-tracked.** This is the check that
   stops the class rather than the instances. Local-only files are untracked by
   construction, so this fires without needing to know what anyone's tooling is
   called.

Property 4 BUILDS the sdist. A test that reads a build output it did not produce
is measuring a leftover.
"""

from __future__ import annotations

import contextlib
import subprocess
import tarfile
import tomllib
from pathlib import Path

import pytest

#: The package root — where pyproject.toml lives. Not the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: Directory names that are local-only for at least one contributor, whatever a
#: future edit to the allowlist thinks.
LOCAL_ONLY_MARKERS = (
    ".claude",
    ".agents",
    ".codex",
    "graphify-out",
    ".venv",
    "venv",
    ".data",
    "dist",
    "build",
    "logs",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "htmlcov",
    "node_modules",
)

#: Written by the build backend, so tracked-ness does not apply.
GENERATED_MEMBERS = frozenset({"PKG-INFO"})

#: Hatchling copies the VCS ignore file into the sdist so the artifact records
#: the exclusions it was built with. It takes that file from the REPOSITORY root,
#: which is one level above this package root — so `git ls-files` run here does
#: not list it and the stray check below would otherwise flag it.
#:
#: The exemption is narrow and comes with `test_injected_vcs_ignore_file_is_tracked`,
#: because the consequence is easy to miss: **the repository's .gitignore is part
#: of the published artifact.** Its entries and its comments ship. That is a
#: reason to keep internal vocabulary and internal document titles out of it.
INJECTED_VCS_FILES = frozenset({".gitignore"})

#: Credential shapes, checked against the artifact regardless of tracked-ness.
#: `.env` is matched as an exact filename so a tracked `.env.example` template
#: is not swept up with it.
SECRET_FILENAMES = frozenset({".env", ".netrc", "credentials.json", "service-account.json", "gcp-key.json", "id_rsa"})
SECRET_SUFFIXES = (".pem", ".key", ".pfx", ".p12", ".keystore", ".jks", ".ppk")


def _sdist_include() -> list[str]:
    """The declared allowlist, or an empty list if the section was deleted.

    Deleting the section is the regression, so it must reach an assertion with a
    readable message rather than a KeyError. The cost is that every test looping
    over this list would then pass vacuously, so each of those asserts the list
    is non-empty first.
    """
    config = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    sdist = config.get("tool", {}).get("hatch", {}).get("build", {}).get("targets", {}).get("sdist", {})
    include = sdist.get("include", [])
    assert isinstance(include, list)
    return [str(entry) for entry in include]


def _tracked_paths() -> set[str]:
    """Tracked files under the package root, relative to it.

    `git ls-files` run from a subdirectory reports paths relative to that
    subdirectory, which is the same form the sdist member names take once the
    archive prefix is stripped.
    """
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


@pytest.fixture(scope="module")
def sdist_members(tmp_path_factory: pytest.TempPathFactory) -> frozenset[str]:
    """Build the sdist and return its member paths, archive prefix stripped.

    Built from the package root into a temporary directory — never read from
    `dist/`, which holds whatever a previous build happened to leave behind.

    `hatchling` is a dev dependency precisely so this import raises rather than
    skips. A packaging control that quietly skips is not a control.
    """
    from hatchling.build import build_sdist

    out = tmp_path_factory.mktemp("sdist")

    with contextlib.chdir(PROJECT_ROOT):
        name = build_sdist(str(out))

    with tarfile.open(out / name) as archive:
        names = archive.getnames()

    # Every member is prefixed with `<name>-<version>/`.
    return frozenset(n.split("/", 1)[1] for n in names if "/" in n)


def test_sdist_selection_is_an_allowlist() -> None:
    assert _sdist_include(), (
        "The sdist include allowlist is empty. Without it hatchling packages the whole "
        "package directory minus whatever the ignore files name, which is an exclude "
        "list that fails open: the next local-only directory to appear here is "
        "published with no code change and no warning."
    )


def test_allowlist_names_no_local_only_directory() -> None:
    include = _sdist_include()
    assert include, "nothing to check — see test_sdist_selection_is_an_allowlist"
    for entry in include:
        parts = entry.strip("/").split("/")
        for marker in LOCAL_ONLY_MARKERS:
            assert marker not in parts, (
                f"sdist allowlist entry {entry!r} names {marker!r}, which is local-only "
                "for at least one contributor and must not be published."
            )


def test_every_allowlist_entry_matches_a_tracked_file() -> None:
    """A stale entry is as much a defect as a dangerous one — it hides drift."""
    include = _sdist_include()
    assert include, "nothing to check — see test_sdist_selection_is_an_allowlist"
    tracked = _tracked_paths()
    for entry in include:
        rel = entry.strip("/")
        matched = rel in tracked or any(path.startswith(f"{rel}/") for path in tracked)
        assert matched, (
            f"sdist allowlist entry {entry!r} matches no git-tracked file. Either it is "
            "stale, or it names something untracked — which must never be packaged."
        )


def test_built_sdist_contains_only_tracked_files(sdist_members: frozenset[str]) -> None:
    """The check that stops the class.

    Named directories are not the danger; unnamed ones are. Anything local-only
    is untracked by construction, so this fires without knowing its name.
    """
    strays = sorted(sdist_members - _tracked_paths() - GENERATED_MEMBERS - INJECTED_VCS_FILES)
    assert strays == [], (
        f"the built sdist contains {len(strays)} file(s) git does not track: {strays}. "
        "Untracked files are exactly what an ignore file hides from review, and "
        "publication is permanent."
    )


def test_injected_vcs_ignore_file_is_tracked(sdist_members: frozenset[str]) -> None:
    """The one exempted member must still be reviewable.

    `.gitignore` is exempted from the stray check because hatchling injects it
    from the repository root rather than from this package. That exemption is
    only safe while the file is tracked *somewhere* — a tracked file has been
    through review; an untracked one is precisely the shape this suite exists to
    keep out of the artifact.
    """
    repo_root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    for member in sorted(sdist_members & INJECTED_VCS_FILES):
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", member],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert tracked.returncode == 0, (
            f"the sdist carries {member!r}, injected from the repository root, but git "
            "does not track it there. An untracked file in the artifact is the defect "
            "this suite exists to catch, exemption or not."
        )


def test_built_sdist_carries_no_credential_shaped_file(sdist_members: frozenset[str]) -> None:
    """Checked against the artifact, independently of what git thinks.

    A secret committed by mistake is tracked, so the test above would pass it.
    This one does not care how it got there.
    """
    offenders = sorted(
        member for member in sdist_members if Path(member).name in SECRET_FILENAMES or member.endswith(SECRET_SUFFIXES)
    )
    assert offenders == [], f"credential-shaped files in the sdist: {offenders}"


def test_built_sdist_carries_what_the_package_needs(sdist_members: frozenset[str]) -> None:
    """An allowlist fails closed, so it can also fail closed on something needed."""
    for required in (
        "pyproject.toml",
        "app/__init__.py",
        "app/briefs/validator.py",
        "app/evals/corpus/claims.json",
        "app/evals/corpus/holdout_claims.json",
        "alembic.ini",
        "tests/test_sdist_contents.py",
    ):
        assert required in sdist_members, f"{required!r} missing from the sdist"
