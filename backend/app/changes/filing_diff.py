"""Filing change detection (plan §3, Phase 3): paragraph-level section diffs with
character spans in the NEW document's normalized text, so every changed block maps
back to stored chunks — change claims stay citable.

Risk-factor focus: Item 1A diffs are the highest-signal output for analysts.
"""

from dataclasses import dataclass, field
from difflib import SequenceMatcher

# Sections worth diffing in a morning brief (risk factors + MD&A + 8-K items)
DIFF_SECTIONS = ("Item 1A", "Item 2", "Item 7", "Item 7A", "Item 8.01", "Item 5.02")


@dataclass
class DiffBlock:
    kind: str  # added | removed | modified
    section: str
    old_text: str
    new_text: str
    new_span: tuple[int, int] | None  # char span in NEW normalized text (None for removals)
    similarity: float = 0.0


@dataclass
class SectionDiff:
    section: str
    added: int = 0
    removed: int = 0
    modified: int = 0
    blocks: list[DiffBlock] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.blocks)


def _paragraphs_with_offsets(text: str, base_offset: int) -> list[tuple[str, int, int]]:
    """Split section text into paragraphs (lines), tracking absolute char spans."""
    out: list[tuple[str, int, int]] = []
    offset = base_offset
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and len(stripped) > 40:  # skip headings/short boilerplate lines
            start = offset + (len(line) - len(line.lstrip()))
            out.append((stripped, start, start + len(stripped)))
        offset += len(line) + 1
    return out


def _section_bounds(sections: list[tuple[str, int]], text_len: int) -> dict[str, tuple[int, int]]:
    bounds: dict[str, tuple[int, int]] = {}
    for i, (name, start) in enumerate(sections):
        end = sections[i + 1][1] if i + 1 < len(sections) else text_len
        # Keep the LAST occurrence of a section name (10-K TOC lines can shadow real ones)
        bounds[name] = (start, end)
    return bounds


def diff_section(
    old_text: str,
    new_text: str,
    section: str,
    new_base_offset: int = 0,
    similarity_floor: float = 0.6,
) -> SectionDiff:
    """Paragraph-aligned diff. 'modified' pairs paragraphs with similarity >= floor;
    below the floor a replace decomposes into removed + added."""
    old_paras = _paragraphs_with_offsets(old_text, 0)
    new_paras = _paragraphs_with_offsets(new_text, new_base_offset)

    matcher = SequenceMatcher(
        a=[p[0] for p in old_paras], b=[p[0] for p in new_paras], autojunk=False
    )
    result = SectionDiff(section=section)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag in ("replace",):
            # Pair old/new greedily by order; leftovers become pure adds/removes
            pairs = min(i2 - i1, j2 - j1)
            for k in range(pairs):
                old_p, new_p = old_paras[i1 + k], new_paras[j1 + k]
                ratio = SequenceMatcher(a=old_p[0], b=new_p[0], autojunk=False).ratio()
                if ratio >= similarity_floor:
                    result.modified += 1
                    result.blocks.append(
                        DiffBlock(
                            kind="modified",
                            section=section,
                            old_text=old_p[0],
                            new_text=new_p[0],
                            new_span=(new_p[1], new_p[2]),
                            similarity=round(ratio, 3),
                        )
                    )
                else:
                    result.removed += 1
                    result.blocks.append(
                        DiffBlock("removed", section, old_p[0], "", None, round(ratio, 3))
                    )
                    result.added += 1
                    result.blocks.append(
                        DiffBlock("added", section, "", new_p[0], (new_p[1], new_p[2]))
                    )
            for k in range(i1 + pairs, i2):
                result.removed += 1
                result.blocks.append(DiffBlock("removed", section, old_paras[k][0], "", None))
            for k in range(j1 + pairs, j2):
                p = new_paras[k]
                result.added += 1
                result.blocks.append(DiffBlock("added", section, "", p[0], (p[1], p[2])))
        elif tag == "delete":
            for k in range(i1, i2):
                result.removed += 1
                result.blocks.append(DiffBlock("removed", section, old_paras[k][0], "", None))
        elif tag == "insert":
            for k in range(j1, j2):
                p = new_paras[k]
                result.added += 1
                result.blocks.append(DiffBlock("added", section, "", p[0], (p[1], p[2])))

    return result


def diff_filings(
    old_normalized: str,
    old_sections: list[tuple[str, int]],
    new_normalized: str,
    new_sections: list[tuple[str, int]],
    sections: tuple[str, ...] = DIFF_SECTIONS,
) -> list[SectionDiff]:
    """Diff matching sections between two parsed filings (sec_parser output)."""
    old_bounds = _section_bounds(old_sections, len(old_normalized))
    new_bounds = _section_bounds(new_sections, len(new_normalized))

    diffs: list[SectionDiff] = []
    for name in sections:
        if name not in new_bounds:
            continue
        ns, ne = new_bounds[name]
        new_text = new_normalized[ns:ne]
        if name in old_bounds:
            os_, oe = old_bounds[name]
            diff = diff_section(old_normalized[os_:oe], new_text, name, new_base_offset=ns)
        else:
            diff = diff_section("", new_text, name, new_base_offset=ns)  # whole section new
        if diff.changed:
            diffs.append(diff)
    return diffs


def blocks_to_chunk_ids(
    blocks: list[DiffBlock],
    chunk_spans: list[tuple[str, int | None, int | None]],
) -> list[str]:
    """Map changed blocks to stored chunk ids by span overlap in the new document.
    chunk_spans: [(chunk_id, span_start, span_end)]."""
    ids: list[str] = []
    for block in blocks:
        if block.new_span is None:
            continue
        bs, be = block.new_span
        for chunk_id, cs, ce in chunk_spans:
            if cs is None or ce is None:
                continue
            if cs < be and bs < ce and chunk_id not in ids:
                ids.append(chunk_id)
    return ids
