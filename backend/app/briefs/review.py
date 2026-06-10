"""Analyst review workflow (plan Phase 3 exit criterion: accept, edit, reject, or
request more source support per section).

user_edits shape on Brief:
{
  "sections": {
    "0": {"action": "accept|reject|edit|needs_source", "content": "...", "at": iso, "by": email}
  }
}

Status flow: draft -> in_review (first action) -> approved (explicit approve, all
sections resolved). Approved briefs are immutable to section actions.
"""

from datetime import datetime, timezone

ALLOWED_ACTIONS = {"accept", "reject", "edit", "needs_source"}


class ReviewError(ValueError):
    pass


def apply_section_action(
    user_edits: dict,
    *,
    section_index: int,
    section_count: int,
    action: str,
    content: str | None,
    actor: str,
) -> dict:
    """Pure: returns a NEW user_edits dict with the action applied."""
    if action not in ALLOWED_ACTIONS:
        raise ReviewError(f"action must be one of {sorted(ALLOWED_ACTIONS)}")
    if not 0 <= section_index < section_count:
        raise ReviewError(f"section_index out of range (0..{section_count - 1})")
    if action == "edit" and not (content or "").strip():
        raise ReviewError("edit requires non-empty content")

    edits = {**user_edits}
    sections = {**edits.get("sections", {})}
    sections[str(section_index)] = {
        "action": action,
        "content": content if action == "edit" else None,
        "at": datetime.now(timezone.utc).isoformat(),
        "by": actor,
    }
    edits["sections"] = sections
    return edits


def all_sections_resolved(user_edits: dict, section_count: int) -> bool:
    """Approvable when every section is accepted/edited/rejected (needs_source blocks)."""
    sections = user_edits.get("sections", {})
    for i in range(section_count):
        entry = sections.get(str(i))
        if entry is None or entry.get("action") == "needs_source":
            return False
    return True
