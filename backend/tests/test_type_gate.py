"""The narrow type gate must exist, cover the right modules, and actually bite.

Same discipline as the eval mutations: a gate nobody has shown can fail is
indistinguishable from no gate. Two things are checked here — that the perimeter
still contains the modules it was adopted for, and that mypy genuinely rejects a
type error inside it.

Scope rule for the perimeter: modules where a type error would corrupt a
REPORTED NUMBER. That is the citation validator, the eval scoring path, and the
script that prints the figures. The rest of the backend is annotated but
deliberately unchecked.
"""

import importlib.util
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
PYPROJECT = BACKEND / "pyproject.toml"

# The subprocess calls below run `sys.executable -m mypy`, so importability is the
# right condition — checking PATH would skip silently whenever mypy is installed
# in a venv but not exposed as a console script, which is the usual case.
needs_mypy = pytest.mark.skipif(
    importlib.util.find_spec("mypy") is None,
    reason="mypy not installed (pip install -e '.[dev]')",
)

#: Removing any of these from the perimeter silently is the failure this guards.
REQUIRED_IN_PERIMETER = (
    "app/briefs/validator.py",
    # consistency.py produces rule 5 and therefore the reported precision
    # figure. It was missing from the perimeter in the first cut of this gate
    # while the docs claimed it was covered — mypy followed it as an import and
    # reported nothing in it. Found in review.
    "app/briefs/consistency.py",
    "app/evals",
    "scripts/run_evals.py",
)


@pytest.fixture(scope="module")
def mypy_config() -> dict:
    with open(PYPROJECT, "rb") as f:
        return tomllib.load(f)["tool"]["mypy"]


def test_type_gate_is_configured_and_strict(mypy_config: dict) -> None:
    assert mypy_config["strict"] is True, "the narrow gate is only worth having at --strict"
    assert mypy_config["files"], "perimeter is empty — the gate checks nothing"


def test_perimeter_covers_the_number_producing_modules(mypy_config: dict) -> None:
    perimeter = set(mypy_config["files"])
    missing = [m for m in REQUIRED_IN_PERIMETER if m not in perimeter]
    assert not missing, (
        f"dropped from the mypy perimeter: {missing}. These are the modules where a "
        "type error would corrupt a reported number; removing one needs a deliberate "
        "decision and a note in docs/EVAL_METHODOLOGY.md, not a silent edit."
    )


def test_every_perimeter_entry_exists(mypy_config: dict) -> None:
    for entry in mypy_config["files"]:
        assert (BACKEND / entry).exists(), f"perimeter names a path that does not exist: {entry}"


@needs_mypy
def test_mypy_rejects_a_type_error(tmp_path: Path) -> None:
    """Prove the checker bites rather than trusting that it is wired up."""
    broken = tmp_path / "broken.py"
    broken.write_text("def f() -> dict[str, str]:\n    return ['not', 'a', 'dict']\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "mypy", "--strict", "--no-incremental", str(broken)],
        capture_output=True,
        text=True,
        cwd=BACKEND,
    )
    assert result.returncode != 0, f"mypy accepted a wrong return type:\n{result.stdout}"
    assert "return-value" in result.stdout, result.stdout


@needs_mypy
def test_perimeter_is_currently_clean() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "mypy"],
        capture_output=True,
        text=True,
        cwd=BACKEND,
    )
    assert result.returncode == 0, result.stdout + result.stderr
