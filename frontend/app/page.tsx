// LedgerBrief dashboard shell — Phase 1 static demo of the design system.
// Server component, zero client JS (perf budget). Live data wiring lands in Phase 1-2.
// DEMO DATA ONLY — values are illustrative, not market data.

type Quote = {
  ticker: string;
  last: string;
  delta: number;
  deltaPct: string;
  filing: string | null;
};

const watchlist: Quote[] = [
  { ticker: "NVDA", last: "1,284.40", delta: 1, deltaPct: "+2.14%", filing: "10-Q" },
  { ticker: "AVGO", last: "2,061.75", delta: 1, deltaPct: "+0.88%", filing: null },
  { ticker: "AMD", last: "228.16", delta: -1, deltaPct: "−1.32%", filing: "8-K" },
  { ticker: "TSM", last: "312.90", delta: 1, deltaPct: "+0.41%", filing: null },
  { ticker: "MU", last: "176.02", delta: -1, deltaPct: "−0.67%", filing: null },
];

const macro = [
  { id: "CPIAUCSL", label: "CPI (YoY)", value: "2.6%", vintage: "2026-06-10" },
  { id: "DGS10", label: "10Y Treasury", value: "4.18%", vintage: "2026-06-09" },
  { id: "FEDFUNDS", label: "Fed Funds", value: "3.75%", vintage: "2026-06-01" },
];

const ledger = [
  {
    id: "C-001",
    claim: "NVDA 10-Q adds a new export-control risk factor vs. prior quarter",
    source: "0001045810-26-000089 · Item 1A",
    span: "p.41 ¶3",
    status: "pass",
  },
  {
    id: "C-002",
    claim: "AMD 8-K discloses datacenter segment leadership change",
    source: "0000002488-26-000041 · Item 5.02",
    span: "p.2 ¶1",
    status: "pass",
  },
  {
    id: "C-003",
    claim: "May CPI print decelerated 10bps vs. April vintage",
    source: "FRED:CPIAUCSL · vintage 2026-06-10",
    span: "obs 2026-05",
    status: "pass",
  },
  {
    id: "C-004",
    claim: "TSM June revenue guidance implies HPC mix above 60%",
    source: "— no stored span —",
    span: "—",
    status: "flag",
  },
];

function DeltaCell({ delta, value }: { delta: number; value: string }) {
  // Direction is never color-only: glyph + sign always present (WCAG 1.4.1)
  return (
    <span className={`num ${delta >= 0 ? "text-up" : "text-down"}`}>
      {delta >= 0 ? "▲" : "▼"} {value}
    </span>
  );
}

function CitationChip({ id, flagged = false }: { id: string; flagged?: boolean }) {
  return (
    <a
      href="#ledger"
      className={`mx-0.5 inline-block rounded-(--radius-ctl) border px-1 py-px align-middle font-mono text-[10px] leading-none ${
        flagged
          ? "border-flag/60 text-flag"
          : "border-elevated text-neutral-90 hover:border-action hover:text-neutral-30"
      }`}
    >
      {id}
    </a>
  );
}

export default function Page() {
  return (
    <div className="min-h-screen">
      {/* Top bar */}
      <header className="sticky top-0 z-10 border-b border-hairline bg-bar">
        <div className="mx-auto flex h-12 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <span className="block h-5 w-1.5 bg-navy-700" aria-hidden />
            <span className="font-serif text-[17px] font-semibold tracking-tight text-neutral-30">
              LedgerBrief
            </span>
            <span className="th-label mt-px">Evidence ledger · Morning brief</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="font-mono text-[11px] text-neutral-90">
              WED 2026-06-10 · 06:30 ET
            </span>
            <span className="rounded-(--radius-ctl) border border-flag/60 px-2 py-0.5 text-[11px] font-medium text-flag">
              INTERNAL RESEARCH DRAFT
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-4 px-6 py-5 lg:grid-cols-[300px_1fr]">
        {/* Watchlist rail */}
        <aside className="space-y-4">
          <section className="rounded-(--radius-card) border border-hairline bg-card">
            <h2 className="th-label border-b border-hairline px-4 py-2.5">
              Watchlist — US Semis
            </h2>
            <table className="w-full text-[13px]">
              <caption className="sr-only">Watchlist quotes and filing flags</caption>
              <thead>
                <tr className="th-label">
                  <th scope="col" className="px-4 py-1.5 text-left font-semibold">Ticker</th>
                  <th scope="col" className="px-2 py-1.5 text-right font-semibold">Last</th>
                  <th scope="col" className="px-2 py-1.5 text-right font-semibold">Δ 1D</th>
                  <th scope="col" className="px-4 py-1.5 text-right font-semibold">Filing</th>
                </tr>
              </thead>
              <tbody>
                {watchlist.map((q) => (
                  <tr key={q.ticker} className="h-8 border-t border-hairline">
                    <td className="px-4 font-mono text-neutral-30">{q.ticker}</td>
                    <td className="num px-2 text-neutral-30">{q.last}</td>
                    <td className="px-2">
                      <DeltaCell delta={q.delta} value={q.deltaPct} />
                    </td>
                    <td className="px-4 text-right">
                      {q.filing ? (
                        <span className="rounded-(--radius-ctl) bg-navy-900 px-1.5 py-0.5 font-mono text-[10px] text-neutral-50">
                          {q.filing}
                        </span>
                      ) : (
                        <span className="text-neutral-90">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="rounded-(--radius-card) border border-hairline bg-card">
            <h2 className="th-label border-b border-hairline px-4 py-2.5">
              Macro — vintage-aware
            </h2>
            <ul>
              {macro.map((m) => (
                <li
                  key={m.id}
                  className="flex h-8 items-center justify-between border-t border-hairline px-4 first:border-t-0"
                >
                  <span className="text-neutral-50">{m.label}</span>
                  <span className="flex items-baseline gap-2">
                    <span className="num text-neutral-30">{m.value}</span>
                    <span className="font-mono text-[10px] text-neutral-90">{m.vintage}</span>
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </aside>

        {/* Brief canvas */}
        <section className="space-y-4">
          <article className="rounded-(--radius-card) border border-hairline bg-card px-6 py-5">
            <p className="th-label mb-2">Morning brief · Watchlist: US Semis + Macro</p>
            <h1 className="font-serif text-2xl font-semibold text-neutral-30">
              What changed since yesterday?
            </h1>
            <p className="mt-1 font-mono text-[11px] text-neutral-90">
              generated 2026-06-10 06:21 ET · model anthropic/claude · prompt v0.3 · 4 claims · 3
              validated · 1 flagged
            </p>

            <h3 className="mt-5 text-sm font-semibold text-neutral-30">Filing changes</h3>
            <p className="mt-1.5 leading-relaxed text-neutral-50">
              NVIDIA&rsquo;s 10-Q filed after yesterday&rsquo;s close introduces a new export-control
              risk factor not present in the prior quarter
              <CitationChip id="C-001" />, expanding language around licensing requirements for
              advanced accelerators. AMD disclosed a datacenter segment leadership change via 8-K
              <CitationChip id="C-002" />.
            </p>

            <h3 className="mt-5 text-sm font-semibold text-neutral-30">Macro context</h3>
            <p className="mt-1.5 leading-relaxed text-neutral-50">
              May CPI decelerated 10bps versus the April vintage
              <CitationChip id="C-003" />; the 10-year held near 4.18% into the print.
            </p>

            <div className="mt-5 rounded-(--radius-ctl) border-l-2 border-flag bg-page/60 px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-flag">
                Flagged — needs source
              </p>
              <p className="mt-1 leading-relaxed text-neutral-50">
                TSM June revenue guidance implies HPC mix above 60%
                <CitationChip id="C-004" flagged /> — no stored source span supports this claim. It
                will not export until validated or removed.
              </p>
            </div>
          </article>

          {/* Evidence ledger */}
          <section
            id="ledger"
            className="rounded-(--radius-card) border border-hairline bg-card"
          >
            <h2 className="th-label border-b border-hairline px-4 py-2.5">Evidence ledger</h2>
            <table className="w-full text-[13px]">
              <caption className="sr-only">
                Claims with sources, spans, and validator status
              </caption>
              <thead>
                <tr className="th-label">
                  <th scope="col" className="px-4 py-1.5 text-left font-semibold">ID</th>
                  <th scope="col" className="px-2 py-1.5 text-left font-semibold">Claim</th>
                  <th scope="col" className="px-2 py-1.5 text-left font-semibold">Source</th>
                  <th scope="col" className="px-2 py-1.5 text-left font-semibold">Span</th>
                  <th scope="col" className="px-4 py-1.5 text-right font-semibold">Validator</th>
                </tr>
              </thead>
              <tbody>
                {ledger.map((row) => (
                  <tr key={row.id} className="border-t border-hairline align-top">
                    <td className="px-4 py-2 font-mono text-[11px] text-neutral-90">{row.id}</td>
                    <td className="max-w-md px-2 py-2 text-neutral-50">{row.claim}</td>
                    <td className="px-2 py-2 font-mono text-[11px] text-neutral-70">
                      {row.source}
                    </td>
                    <td className="px-2 py-2 font-mono text-[11px] text-neutral-70">{row.span}</td>
                    <td className="px-4 py-2 text-right">
                      {row.status === "pass" ? (
                        <span className="font-medium text-up">✓ PASS</span>
                      ) : (
                        <span className="font-medium text-flag">⚑ FLAG</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <footer className="px-1 pb-6 text-[11px] leading-relaxed text-neutral-90">
            Internal research draft. Factual, cited, non-personalized. Not investment advice, not a
            recommendation, and not an offer to buy or sell any security. AI-assisted content —
            human review required before external use. Sources: SEC EDGAR, FRED (this product uses
            the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St.
            Louis).
          </footer>
        </section>
      </main>
    </div>
  );
}
