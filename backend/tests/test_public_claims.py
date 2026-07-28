"""Public wording rules from docs/claims/claim-ledger.md, enforced.

A precision figure with no definition attached is exactly the defect this
repository exists to catch: a number travelling without the thing that makes it
meaningful. "Precision 0.400" alone is uninterpretable — a reader cannot tell
whether 40% of accepted claims are supported or 40% of rejections were correct,
and those are opposite readings of the same system.

The claim ledger already forbids this in prose. Prose rules decay; the tautology
survived as long as it did because nothing checked it. So the three rules that
can be checked mechanically are checked here.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

#: Every public surface that may quote a citation-accuracy figure.
PUBLIC_DOCS = [
    "README.md",
    "docs/EVAL_METHODOLOGY.md",
    "docs/claims/claim-ledger.md",
    "backend/app/evals/corpus/README.md",
]

#: The three things a figure must travel with: what is classified, what counts
#: as a positive, and over what population.
REQUIRED_DEFINITION_MARKERS = ("unit: one claim", "positive:", "population:")

#: The development-corpus figure. Never allowed to appear without the holdout
#: figure, because the rules were built against the dev corpus.
DEV_FIGURE = "0.579"
HOLDOUT_FIGURE = "0.400"

#: Matches a precision/recall figure being stated, e.g. "precision 0.400",
#: "citation precision | 0.579", "precision: 0.400".
FIGURE_RE = re.compile(
    r"\b(?:precision|recall)\b[^\n|]{0,20}[|:\s]\s*\*{0,2}(?:0\.\d{3}|1\.000)"
    # ...and the same figure written as prose percentage ("40% are genuinely supported"),
    # which the decimal-only pattern missed entirely.
    r"|\b\d{1,3}%\s+(?:are|of)\b[^\n]{0,60}\bsupported\b",
    re.IGNORECASE,
)


def read(doc: str) -> str:
    path = REPO / doc
    assert path.exists(), f"public doc missing: {doc}"
    return path.read_text(encoding="utf-8")


def normalised(text: str) -> str:
    """Lower-case with markdown emphasis stripped.

    The rule is about content, not formatting: "**Unit:** one claim" must satisfy
    the same check as "Unit: one claim". Matching the raw text made the guard
    depend on how the definition happened to be styled.
    """
    return re.sub(r"[*_`]", "", text.lower())


@pytest.mark.parametrize("doc", PUBLIC_DOCS)
def test_every_doc_quoting_a_figure_defines_it(doc: str) -> None:
    text = read(doc)
    if not FIGURE_RE.search(text):
        pytest.skip(f"{doc} quotes no precision/recall figure")

    lowered = normalised(text)
    missing = [m for m in REQUIRED_DEFINITION_MARKERS if m not in lowered]
    assert not missing, (
        f"{doc} states a precision or recall figure but is missing {missing} from its "
        "definition. Every public statement of these numbers must say what is being "
        "classified, what counts as a positive, and over what population — see the "
        "'How to read the citation-accuracy numbers' block in docs/claims/claim-ledger.md."
    )


@pytest.mark.parametrize("doc", PUBLIC_DOCS)
def test_dev_figure_never_appears_without_the_holdout_figure(doc: str) -> None:
    text = read(doc)
    if DEV_FIGURE not in text:
        pytest.skip(f"{doc} does not quote the dev figure")
    assert HOLDOUT_FIGURE in text, (
        f"{doc} quotes the development-corpus figure {DEV_FIGURE} without the held-out "
        f"figure {HOLDOUT_FIGURE}. The dev corpus is the one the consistency rules were "
        "built against, so it overstates the system on unseen documents."
    )


@pytest.mark.parametrize("doc", ["README.md", "docs/EVAL_METHODOLOGY.md"])
def test_holdout_figure_is_the_headline(doc: str) -> None:
    """The dev figure must never be the first one a reader meets."""
    text = read(doc)
    first_dev = text.find(DEV_FIGURE)
    first_holdout = text.find(HOLDOUT_FIGURE)
    assert first_holdout != -1, f"{doc} does not state the held-out figure at all"
    if first_dev == -1:
        return
    # Same table row is fine (dev and holdout side by side); leading with dev is not.
    dev_line = text.count("\n", 0, first_dev)
    holdout_line = text.count("\n", 0, first_holdout)
    assert holdout_line <= dev_line, (
        f"{doc} states the development figure on line {dev_line + 1} before the held-out "
        f"figure on line {holdout_line + 1}. The headline is the held-out number."
    )


def test_claim_ledger_prohibits_undefined_figures() -> None:
    """The rule itself must stay written down, not just enforced here."""
    ledger = read("docs/claims/claim-ledger.md").lower()
    assert "prohibited wording" in ledger
    assert "without the definition" in ledger, (
        "the claim ledger no longer prohibits stating a figure without its definition; "
        "this test enforces a rule that must remain documented"
    )


def test_per_shape_result_is_not_the_headline() -> None:
    """3/3 on two trap shapes is supporting detail, not the top-line result."""
    for doc in ("README.md", "docs/EVAL_METHODOLOGY.md"):
        text = read(doc)
        first_shape = text.find("3/3")
        first_holdout = text.find(HOLDOUT_FIGURE)
        if first_shape == -1:
            continue
        assert first_holdout < first_shape, (
            f"{doc} leads with the per-shape generalisation result before the held-out "
            "precision figure. 3/3 explains why the number lands where it does; it is "
            "not the number."
        )


@pytest.mark.parametrize("doc", PUBLIC_DOCS)
def test_definition_precedes_the_first_figure(doc: str) -> None:
    """A definition buried after the number does not travel with it.

    Document-scoped presence is not enough: a reader who stops at the headline
    must already have been told what the number means.
    """
    lowered = normalised(read(doc))
    match = FIGURE_RE.search(lowered)
    if match is None:
        pytest.skip(f"{doc} quotes no precision/recall figure")

    first_figure = match.start()
    for marker in REQUIRED_DEFINITION_MARKERS:
        position = lowered.find(marker)
        assert position != -1 and position < first_figure, (
            f"{doc}: '{marker}' is at {position} but the first figure is at {first_figure}. "
            "The definition must come before the number, not after it."
        )
