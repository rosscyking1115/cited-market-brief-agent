"""Structure-aware SEC filing parser (plan §7 step 2).

Phase 1 prototype: HTML -> normalized text -> Item-level sections -> overlapping
chunks with character-span metadata. Every chunk records (section, span_start,
span_end) into the normalized text, so citations can later resolve to an exact span.

Prompt-injection note (plan §9, LLM01): filing text is UNTRUSTED input. It is never
executed or rendered unsanitized; downstream prompts must spotlight/delimit it.
"""

import re
import warnings
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# "Item 1A." / "ITEM 7." style headings used in 10-K/10-Q/8-K
_ITEM_RE = re.compile(r"^item\s+(\d{1,2}[a-z]?)\s*[.:—-]", re.IGNORECASE)

CHUNK_SIZE = 1800
CHUNK_OVERLAP = 200


@dataclass
class ChunkData:
    text: str
    section: str
    span_start: int
    span_end: int
    is_table: bool = False
    page: int | None = None


@dataclass
class ParsedDocument:
    normalized_text: str
    sections: list[tuple[str, int]] = field(default_factory=list)  # (name, start offset)
    chunks: list[ChunkData] = field(default_factory=list)


def normalize_html(html: str) -> str:
    """HTML -> plain text with stable offsets: one paragraph per line, collapsed whitespace."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    # Hidden inline-XBRL blocks carry no analyst-readable content
    for tag in soup.find_all(attrs={"style": re.compile(r"display:\s*none", re.IGNORECASE)}):
        tag.decompose()

    raw = soup.get_text(separator="\n")
    lines = []
    for line in raw.split("\n"):
        cleaned = re.sub(r"[ \t\xa0]+", " ", line).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines)


def split_sections(normalized_text: str) -> list[tuple[str, int]]:
    """Locate Item headings; returns [(section_name, start_offset)], always starting
    with a 'preamble' section at offset 0."""
    sections: list[tuple[str, int]] = [("preamble", 0)]
    offset = 0
    for line in normalized_text.split("\n"):
        match = _ITEM_RE.match(line)
        if match and len(line) < 120:  # heading lines are short; avoid body-text mentions
            sections.append((f"Item {match.group(1).upper()}", offset))
        offset += len(line) + 1  # +1 for the newline
    return sections


def chunk_section(text: str, section: str, base_offset: int) -> list[ChunkData]:
    chunks: list[ChunkData] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        if end < len(text):
            # Prefer to break on a line boundary inside the window
            window_break = text.rfind("\n", start + CHUNK_SIZE - CHUNK_OVERLAP, end)
            if window_break > start:
                end = window_break
        window = text[start:end]
        piece = window.strip()
        if piece:
            # Exact span of the stripped piece: offset by the leading-whitespace length
            piece_start = base_offset + start + (len(window) - len(window.lstrip()))
            chunks.append(
                ChunkData(
                    text=piece,
                    section=section,
                    span_start=piece_start,
                    span_end=piece_start + len(piece),
                )
            )
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def parse_filing_html(html: str) -> ParsedDocument:
    normalized = normalize_html(html)
    sections = split_sections(normalized)

    chunks: list[ChunkData] = []
    for i, (name, start) in enumerate(sections):
        end = sections[i + 1][1] if i + 1 < len(sections) else len(normalized)
        body = normalized[start:end]
        if body.strip():
            chunks.extend(chunk_section(body, name, start))

    return ParsedDocument(normalized_text=normalized, sections=sections, chunks=chunks)
