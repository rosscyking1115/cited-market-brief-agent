from app.changes.filing_diff import blocks_to_chunk_ids, diff_filings, diff_section
from app.ingestion.sec_parser import parse_filing_html

PARA_EQUAL = (
    "Our business depends on continued demand for accelerated computing platforms "
    "across datacenter and client markets worldwide."
)
PARA_OLD_MOD = "Demand may fluctuate based on datacenter capital expenditure cycles in major markets."
PARA_NEW_MOD = (
    "Demand may fluctuate based on datacenter capital expenditure cycles and hyperscaler build plans in major markets."
)
PARA_REMOVED = "We rely on a limited number of foundry partners for wafer supply and capacity allocation."
PARA_ADDED = (
    "We are subject to new export control licensing requirements for advanced accelerator "
    "products, which could materially reduce revenue from affected regions."
)


def test_diff_section_detects_added_removed_modified() -> None:
    old = "\n".join([PARA_EQUAL, PARA_OLD_MOD, PARA_REMOVED])
    new = "\n".join([PARA_EQUAL, PARA_NEW_MOD, PARA_ADDED])
    result = diff_section(old, new, "Item 1A")

    assert result.changed
    assert result.modified >= 1
    assert result.added >= 1
    assert result.removed >= 1
    kinds = {b.kind for b in result.blocks}
    assert kinds == {"added", "removed", "modified"}


def test_diff_spans_map_back_into_new_text() -> None:
    old = "\n".join([PARA_EQUAL, PARA_OLD_MOD])
    new = "\n".join([PARA_EQUAL, PARA_NEW_MOD, PARA_ADDED])
    result = diff_section(old, new, "Item 1A")

    for block in result.blocks:
        if block.new_span is not None:
            start, end = block.new_span
            assert new[start:end] == block.new_text


def test_identical_sections_produce_no_diff() -> None:
    text = "\n".join([PARA_EQUAL, PARA_OLD_MOD])
    assert not diff_section(text, text, "Item 1A").changed


def _filing_html(paragraphs: list[str]) -> str:
    body = "".join(f"<p>{p}</p>" for p in paragraphs)
    return (
        "<html><body><p>FORM 10-Q</p><p><b>Item 1A.</b> Risk Factors</p>"
        f"{body}<p><b>Item 2.</b> MD&A</p><p>{PARA_EQUAL}</p></body></html>"
    )


def test_diff_filings_end_to_end_with_chunk_mapping() -> None:
    old_parsed = parse_filing_html(_filing_html([PARA_EQUAL, PARA_OLD_MOD]))
    new_parsed = parse_filing_html(_filing_html([PARA_EQUAL, PARA_NEW_MOD, PARA_ADDED]))

    diffs = diff_filings(
        old_parsed.normalized_text,
        old_parsed.sections,
        new_parsed.normalized_text,
        new_parsed.sections,
    )
    item_1a = next((d for d in diffs if d.section == "Item 1A"), None)
    assert item_1a is not None and item_1a.changed

    # Changed blocks must map to the new document's stored chunk spans
    chunk_spans = [(f"chunk-{i}", c.span_start, c.span_end) for i, c in enumerate(new_parsed.chunks)]
    ids = blocks_to_chunk_ids(item_1a.blocks, chunk_spans)
    assert ids, "expected changed blocks to overlap at least one chunk"


def test_blocks_to_chunk_ids_overlap_logic() -> None:
    from app.changes.filing_diff import DiffBlock

    blocks = [
        DiffBlock("added", "Item 1A", "", "x" * 60, (95, 150)),
        DiffBlock("removed", "Item 1A", "y" * 60, "", None),  # no span -> skipped
    ]
    spans = [("c1", 0, 100), ("c2", 90, 200), ("c3", 400, 500)]
    assert blocks_to_chunk_ids(blocks, spans) == ["c1", "c2"]
