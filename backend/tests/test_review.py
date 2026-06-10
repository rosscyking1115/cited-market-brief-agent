import pytest

from app.briefs.review import (
    ReviewError,
    all_sections_resolved,
    apply_section_action,
)


def _apply(edits: dict, index: int, action: str, content: str | None = None) -> dict:
    return apply_section_action(
        edits,
        section_index=index,
        section_count=3,
        action=action,
        content=content,
        actor="dev@ledgerbrief.local",
    )


def test_accept_records_action_and_actor() -> None:
    edits = _apply({}, 0, "accept")
    entry = edits["sections"]["0"]
    assert entry["action"] == "accept"
    assert entry["by"] == "dev@ledgerbrief.local"
    assert entry["content"] is None


def test_original_dict_not_mutated() -> None:
    original: dict = {"sections": {}}
    _apply(original, 1, "reject")
    assert original["sections"] == {}


def test_edit_requires_content() -> None:
    with pytest.raises(ReviewError):
        _apply({}, 0, "edit", content="   ")
    edits = _apply({}, 0, "edit", content="Revised section text")
    assert edits["sections"]["0"]["content"] == "Revised section text"


def test_invalid_action_and_index_rejected() -> None:
    with pytest.raises(ReviewError):
        _apply({}, 0, "approve")  # not a section action
    with pytest.raises(ReviewError):
        _apply({}, 3, "accept")  # out of range (count=3)


def test_all_sections_resolved_gate() -> None:
    edits: dict = {}
    assert not all_sections_resolved(edits, 2)

    edits = _apply(edits, 0, "accept")
    assert not all_sections_resolved(edits, 2)

    edits = _apply(edits, 1, "needs_source")
    assert not all_sections_resolved(edits, 2)  # needs_source blocks approval

    edits = _apply(edits, 1, "edit", content="rewritten")
    assert all_sections_resolved(edits, 2)
