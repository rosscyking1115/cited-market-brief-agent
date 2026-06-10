// LedgerBrief dashboard — RSC-first. Fetches the latest brief's evidence payload
// from the API; falls back to demo data when the backend isn't running so the
// design system always renders. The evidence ledger is the only client island.

import EvidenceLedger from "@/app/components/EvidenceLedger";
import { API_URL, getLatestEvidence, type EvidencePayload } from "@/lib/api";

export const dynamic = "force-dynamic";

// --- Demo fallback (same shape as GET /briefs/{id}/evidence) ---
const DEMO: EvidencePayload = {
  brief_id: "demo",
  watchlist: "US Semis + Macro (sample)",
  status: "draft",
  created_at: "2026-06-10T06:21:00+00:00",
  sections: [
    {
      title: "Filing changes",
      content_markdown:
        "NVIDIA's 10-Q introduces a new export-control risk factor not present in the prior quarter [#0]. AMD disclosed a datacenter segment leadership change via 8-K [#1].",
    },
    {
      title: "Macro context",
      content_markdown:
        "May CPI decelerated 10bps versus the April vintage [#2]; the 10-year held near 4.18% into the print.",
    },
  ],
  open_questions: ["What drove the sequential gross-margin change?"],
  claims: [
    {
      claim_id: "demo-0",
      index: 0,
      text: "NVDA 10-Q adds a new export-control risk factor vs. prior quarter",
      type: "filing_change",
      confidence: "high",
      support_status: "supported",
      needs_review: false,
      citations: [
        {
          span_id: "demo-span-0",
          validator: "pass",
          validated_at: "2026-06-10T06:21:05+00:00",
          evidence_quote:
            "new export control licensing requirements for advanced accelerator products",
          span: [10412, 12110],
          section: "Item 1A",
          chunk_text:
            "We are subject to new export control licensing requirements for advanced accelerator products. These requirements could materially reduce revenue from affected regions and increase compliance costs…",
          doc_type: "10-Q",
          accession: "0001045810-26-000089",
          source_url: "https://www.sec.gov/Archives/edgar/data/1045810/…",
          publisher: "SEC EDGAR (NVDA)",
          retrieved_at: "2026-06-10T05:58:11+00:00",
          checksum_sha256: "9f2c1a7e44b85d3c0aa1",
        },
      ],
    },
    {
      claim_id: "demo-1",
      index: 1,
      text: "AMD 8-K discloses datacenter segment leadership change",
      type: "filing_change",
      confidence: "high",
      support_status: "supported",
      needs_review: false,
      citations: [
        {
          span_id: "demo-span-1",
          validator: "pass",
          validated_at: "2026-06-10T06:21:05+00:00",
          evidence_quote: "appointment of a new senior vice president, datacenter",
          span: [220, 1444],
          section: "Item 5.02",
          chunk_text:
            "On June 9, 2026, the company announced the appointment of a new senior vice president, datacenter, effective July 1, 2026…",
          doc_type: "8-K",
          accession: "0000002488-26-000041",
          source_url: "https://www.sec.gov/Archives/edgar/data/2488/…",
          publisher: "SEC EDGAR (AMD)",
          retrieved_at: "2026-06-10T05:58:40+00:00",
          checksum_sha256: "41bb02de91c77a08f3e2",
        },
      ],
    },
    {
      claim_id: "demo-2",
      index: 2,
      text: "May CPI print decelerated 10bps vs. April vintage",
      type: "macro_delta",
      confidence: "high",
      support_status: "supported",
      needs_review: false,
      citations: [
        {
          span_id: "demo-span-2",
          validator: "pass",
          validated_at: "2026-06-10T06:21:05+00:00",
          evidence_quote: "2026-05: 327.1",
          span: [0, 214],
          section: "CPIAUCSL",
          chunk_text:
            "Consumer Price Index for All Urban Consumers (CPIAUCSL). Units: Index 1982-1984=100. Frequency: Monthly. Data vintage: 2026-06-10.\nObservations:\n2026-03: 325.8\n2026-04: 326.6\n2026-05: 327.1",
          doc_type: "macro_series",
          accession: null,
          source_url: "https://fred.stlouisfed.org/series/CPIAUCSL",
          publisher: "FRED, Federal Reserve Bank of St. Louis",
          retrieved_at: "2026-06-10T05:59:02+00:00",
          checksum_sha256: "77ac41b09cd2e6f01b53",
        },
      ],
    },
    {
      claim_id: "demo-3",
      index: 3,
      text: "TSM June revenue guidance implies HPC mix above 60%",
      type: "factual_summary",
      confidence: "low",
      support_status: "flagged",
      needs_review: true,
      citations: [],
    },
  ],
};

function SectionContent({
  text,
  claims,
}: {
  text: string;
  claims: EvidencePayload["claims"];
}) {
  const parts = text.split(/(\[#\d+\])/g);
  return (
    <p className="mt-1.5 leading-relaxed text-neutral-50">
      {parts.map((part, i) => {
        const match = /^\[#(\d+)\]$/.exec(part);
        if (!match) return <span key={i}>{part}</span>;
        const idx = Number(match[1]);
        const claim = claims.find((c) => c.index === idx);
        const ok = claim?.support_status === "supported";
        return (
          <a
            key={i}
            href="#ledger"
            className={`mx-0.5 inline-block rounded-(--radius-ctl) border px-1 py-px align-middle font-mono text-[10px] leading-none ${
              ok
                ? "border-elevated text-neutral-90 hover:border-action hover:text-neutral-30"
                : "border-flag/60 text-flag"
            }`}
          >
            C-{String(idx).padStart(3, "0")}
            {!ok && " ⚑"}
          </a>
        );
      })}
    </p>
  );
}

export default async function Page() {
  const live = await getLatestEvidence();
  const data = live ?? DEMO;
  const isLive = live !== null;
  const ts = data.created_at.slice(0, 16).replace("T", " ");
  const supported = data.claims.filter((c) => c.support_status === "supported").length;
  const flagged = data.claims.length - supported;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-hairline bg-bar">
        <div className="mx-auto flex h-12 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <span className="block h-5 w-1.5 bg-navy-700" aria-hidden />
            <span className="font-serif text-[17px] font-semibold tracking-tight text-neutral-30">
              LedgerBrief
            </span>
            <span className="th-label mt-px">Evidence ledger · Morning brief</span>
          </div>
          <div className="flex items-center gap-3">
            <span
              className={`rounded-(--radius-ctl) border px-2 py-0.5 font-mono text-[10px] ${
                isLive ? "border-up/60 text-up" : "border-elevated text-neutral-90"
              }`}
            >
              {isLive ? "● LIVE" : "○ DEMO DATA"}
            </span>
            <span className="rounded-(--radius-ctl) border border-flag/60 px-2 py-0.5 text-[11px] font-medium text-flag">
              INTERNAL RESEARCH DRAFT
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-4 px-6 py-5">
        <article className="rounded-(--radius-card) border border-hairline bg-card px-6 py-5">
          <p className="th-label mb-2">Morning brief · Watchlist: {data.watchlist}</p>
          <h1 className="font-serif text-2xl font-semibold text-neutral-30">
            What changed since yesterday?
          </h1>
          <p className="mt-1 font-mono text-[11px] text-neutral-90">
            generated {ts} UTC · {data.claims.length} claims · {supported} validated ·{" "}
            {flagged} flagged · status {data.status}
          </p>

          {data.sections.map((section) => (
            <section key={section.title} className="mt-5">
              <h3 className="text-sm font-semibold text-neutral-30">{section.title}</h3>
              <SectionContent text={section.content_markdown} claims={data.claims} />
            </section>
          ))}

          {data.open_questions.length > 0 && (
            <section className="mt-5 rounded-(--radius-ctl) border-l-2 border-action bg-page/60 px-4 py-3">
              <p className="th-label">Analyst open questions</p>
              <ul className="mt-1 list-inside list-disc text-[13px] text-neutral-50">
                {data.open_questions.map((q) => (
                  <li key={q}>{q}</li>
                ))}
              </ul>
            </section>
          )}
        </article>

        <EvidenceLedger claims={data.claims} apiUrl={API_URL} live={isLive} />

        <footer className="px-1 pb-6 text-[11px] leading-relaxed text-neutral-90">
          Internal research draft. Factual, cited, non-personalized. Not investment advice, not a
          recommendation, and not an offer to buy or sell any security. AI-assisted content —
          human review required before external use. Sources: SEC EDGAR, FRED (this product uses
          the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St.
          Louis).
        </footer>
      </main>
    </div>
  );
}
