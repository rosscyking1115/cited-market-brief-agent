"""HTML -> PDF via sandboxed Playwright (plan §9: JavaScript disabled, all network
requests aborted — the renderer cannot execute LLM-influenced code or exfiltrate).

Requires the 'exports' extra: pip install -e ".[exports]" && playwright install chromium
"""


def html_to_pdf(html: str) -> bytes:
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "PDF export requires Playwright: pip install -e '.[exports]' && playwright install chromium"
        ) from exc

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(java_script_enabled=False)  # no script execution
        page = context.new_page()
        page.route("**/*", lambda route: route.abort())  # no network, ever
        page.set_content(html, wait_until="domcontentloaded")
        pdf_bytes = page.pdf(format="A4", print_background=True)
        browser.close()
    return pdf_bytes
