"""Self-contained HTML report for PDF rendering (plan §9 output safety).

Security posture:
- ALL dynamic text passes through html.escape — the LLM never injects markup
- zero external resources (no fonts, images, scripts) — nothing to exfiltrate to
- rendered by a sandboxed browser with JavaScript and network disabled (pdf.py)
- print palette: light theme (paper), Salt-derived inks
"""

from html import escape

from app.exports.bundle import ExportBundle, strip_claim_refs

_CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }
* { box-sizing: border-box; }
body { font-family: Georgia, 'Times New Roman', serif; color: #161616; font-size: 11pt;
       line-height: 1.45; margin: 0; }
.sans { font-family: Arial, Helvetica, sans-serif; }
.mono { font-family: 'Courier New', monospace; }
header { border-bottom: 3px solid #00477B; padding-bottom: 8px; margin-bottom: 14px; }
.brand { font-size: 16pt; font-weight: bold; color: #00477B; }
.meta { font-size: 8.5pt; color: #545B63; }
.watermark { border: 1.5px solid #D65513; color: #D65513; font-size: 9pt; font-weight: bold;
             letter-spacing: 0.06em; padding: 5px 10px; margin: 10px 0; text-align: center; }
.watermark.approved { border-color: #24874B; color: #24874B; }
h1 { font-size: 17pt; margin: 6px 0 2px 0; }
h2 { font-size: 12pt; color: #00477B; border-bottom: 1px solid #CED2D9;
     padding-bottom: 3px; margin: 16px 0 6px 0; }
p { margin: 5px 0; }
.chip { font-family: 'Courier New', monospace; font-size: 8pt; color: #2670A9; }
table { width: 100%; border-collapse: collapse; font-size: 8.5pt; margin-top: 6px; }
th { text-align: left; font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.05em;
     color: #545B63; border-bottom: 1.5px solid #161616; padding: 3px 6px 3px 0; }
td { border-bottom: 0.5px solid #CED2D9; padding: 4px 6px 4px 0; vertical-align: top; }
.pass { color: #24874B; font-weight: bold; }
.flag { color: #D65513; font-weight: bold; }
.review { background: #FBF3EC; border-left: 3px solid #D65513; padding: 6px 10px;
          font-size: 9pt; margin: 4px 0; }
footer { margin-top: 18px; border-top: 1px solid #CED2D9; padding-top: 8px;
         font-size: 7.5pt; color: #545B63; }
"""


def build_report_html(bundle: ExportBundle) -> str:
    e = escape
    parts: list[str] = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        f"<title>{e(bundle.watchlist)} — Cited Market Brief Agent</title>",
        f"<style>{_CSS}</style></head><body>",
        "<header>",
        "<div class='brand sans'>Cited Market Brief Agent</div>",
        f"<div class='meta sans'>Watchlist: {e(bundle.watchlist)} · generated "
        f"{bundle.generated_at.strftime('%Y-%m-%d %H:%M UTC')} · model {e(bundle.model)} · "
        f"prompt {e(bundle.prompt_version)} · {len(bundle.supported_claims)} validated claims</div>",
        "</header>",
        f"<div class='watermark sans{' approved' if bundle.status == 'approved' else ''}'>{e(bundle.watermark)}</div>",
    ]
    if bundle.approval_line:
        parts.append(f"<div class='meta sans'>{e(bundle.approval_line)}</div>")

    parts.append("<h1>What changed since yesterday?</h1>")

    for section in bundle.sections:
        edited = " <span class='chip'>(analyst-edited)</span>" if section.action == "edit" else ""
        parts.append(f"<h2>{e(section.title)}{edited}</h2>")
        parts.append(f"<p>{e(strip_claim_refs(section.content))}</p>")

    parts.append("<h2>Evidence ledger</h2>")
    parts.append(
        "<table><thead><tr><th>ID</th><th>Claim</th><th>Type</th><th>Sources</th><th>Validator</th></tr></thead><tbody>"
    )
    for claim in bundle.supported_claims:
        sources = "; ".join(e(s) for s in claim.sources)
        parts.append(
            f"<tr><td class='mono'>{e(claim.cid)}</td><td>{e(claim.text)}</td>"
            f"<td class='mono'>{e(claim.claim_type)}</td><td class='mono'>{sources}</td>"
            f"<td class='pass'>PASS</td></tr>"
        )
    parts.append("</tbody></table>")

    if bundle.review_claims:
        parts.append("<h2>Needs review — not validated, do not cite</h2>")
        for claim in bundle.review_claims:
            parts.append(
                f"<div class='review'><span class='flag'>⚑ {e(claim.cid)}</span> "
                f"{e(claim.text)} — <i>{e(claim.reason)}</i></div>"
            )

    if bundle.open_questions:
        parts.append("<h2>Analyst open questions</h2>")
        for q in bundle.open_questions:
            parts.append(f"<p>• {e(q)}</p>")

    parts.append(f"<footer class='sans'>{e(bundle.disclaimer)}</footer>")
    parts.append("</body></html>")
    return "".join(parts)
