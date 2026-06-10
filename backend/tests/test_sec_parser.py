from app.ingestion.sec_parser import normalize_html, parse_filing_html

FIXTURE_10Q = """
<html><head><style>p { color: red }</style><script>alert(1)</script></head>
<body>
<div style="display:none">hidden xbrl noise</div>
<p>UNITED STATES SECURITIES AND EXCHANGE COMMISSION</p>
<p>FORM 10-Q</p>
<p><b>Item 1A.</b> Risk Factors</p>
<p>Our business faces new export control licensing requirements for advanced
accelerator products, which could materially affect revenue in affected regions.</p>
<p>Demand may fluctuate based on datacenter capital expenditure cycles.</p>
<p><b>Item 2.</b> Management's Discussion and Analysis</p>
<p>Revenue for the quarter increased compared to the prior year period, driven by
datacenter segment growth.</p>
</body></html>
"""


def test_normalize_strips_script_style_hidden() -> None:
    text = normalize_html(FIXTURE_10Q)
    assert "alert(1)" not in text
    assert "color: red" not in text
    assert "hidden xbrl noise" not in text
    assert "FORM 10-Q" in text


def test_sections_detected() -> None:
    parsed = parse_filing_html(FIXTURE_10Q)
    names = [name for name, _ in parsed.sections]
    assert "preamble" in names
    assert "Item 1A" in names
    assert "Item 2" in names


def test_chunk_spans_map_back_exactly() -> None:
    parsed = parse_filing_html(FIXTURE_10Q)
    assert parsed.chunks, "expected at least one chunk"
    for chunk in parsed.chunks:
        assert parsed.normalized_text[chunk.span_start : chunk.span_end] == chunk.text


def test_risk_factor_text_lands_in_item_1a() -> None:
    parsed = parse_filing_html(FIXTURE_10Q)
    item_1a_chunks = [c for c in parsed.chunks if c.section == "Item 1A"]
    assert any("export control licensing" in c.text for c in item_1a_chunks)
