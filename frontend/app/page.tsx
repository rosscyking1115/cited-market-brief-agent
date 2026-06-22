// Cited Market Brief Agent dashboard — RSC-first. Fetches the latest brief's evidence payload
// from the API; falls back to demo data when the backend isn't running so the
// design system always renders. The evidence ledger is the only client island.

import BriefCanvas from "@/app/components/BriefCanvas";
import ChangesPanel from "@/app/components/ChangesPanel";
import EvidenceRail from "@/app/components/EvidenceRail";
import EvidenceLedger from "@/app/components/EvidenceLedger";
import FundAttributionPanel from "@/app/components/FundAttributionPanel";
import MorningMarketDashboard from "@/app/components/MorningMarketDashboard";
import RepairClaimButton from "@/app/components/RepairClaimButton";
import { HideOnTaiwan } from "@/app/components/RegionGate";
import { RegionSwitcher } from "@/app/components/RegionProvider";
import TextSizeToggle from "@/app/components/TextSizeToggle";
import ThemeToggle from "@/app/components/ThemeToggle";
import {
  API_URL,
  getChanges,
  getFundAttributionPlan,
  getLatestEvidence,
  getLatestFundAttribution,
  getMorningRadar,
  type ChangesPayload,
  type EvidencePayload,
  type MorningRadarPayload,
} from "@/lib/api";

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

const DEMO_CHANGES: ChangesPayload = {
  watchlist_id: "demo",
  since: "2026-06-09T06:21:00+00:00",
  previous_brief_id: "demo-prev",
  new_documents: [
    {
      document_id: "demo-doc-1",
      doc_type: "10-Q",
      accession: "0001045810-26-000089",
      publisher: "SEC EDGAR (NVDA)",
      url: "https://www.sec.gov/Archives/edgar/data/1045810/…",
      publication_date: "2026-06-09",
    },
  ],
  filing_diffs: [
    {
      cik: "1045810",
      form: "10-Q",
      publisher: "SEC EDGAR (NVDA)",
      accession_new: "0001045810-26-000089",
      accession_old: "0001045810-26-000034",
      sections: [{ section: "Item 1A", added: 2, removed: 0, modified: 1 }],
      samples: [
        {
          kind: "added",
          section: "Item 1A",
          text: "We are subject to new export control licensing requirements for advanced accelerator products. These requirements could materially reduce revenue from affected regions.",
          similarity: 0,
        },
        {
          kind: "modified",
          section: "Item 1A",
          text: "Demand may fluctuate based on datacenter capital expenditure cycles and hyperscaler build plans.",
          similarity: 0.82,
        },
      ],
    },
  ],
  macro_deltas: [
    {
      series_id: "CPIAUCSL",
      latest_date: "2026-05",
      latest_value: 327.1,
      prev_date: "2026-04",
      prev_value: 326.6,
      change: 0.5,
      change_pct: 0.1531,
      revisions: [{ date: "2026-03", old_value: 325.9, new_value: 325.8 }],
      vintage: "2026-06-10T05:59:02+00:00",
    },
  ],
};

const DEMO_RADAR: MorningRadarPayload = {
  generated_at: "2026-06-14T07:30:00+08:00",
  timezone: "Asia/Taipei",
  headline: "今天先看全球市場，再看台股開盤",
  summary_points: [
    "美股與歐股收盤先決定隔夜基調。",
    "08:00 先看日本、韓國；09:00 接台股。",
    "油金、美元、利率用來判斷風險情緒，不作買賣建議。",
  ],
  current_focus: "台灣 · 未開盤",
  market_clock: [
    {
      market: "日本",
      label: "日經225 / TOPIX",
      window: "08:00-10:30, 11:30-14:30",
      status: "open",
      note: "亞洲第一棒，先看科技與匯率。",
    },
    {
      market: "韓國",
      label: "KOSPI / KOSDAQ",
      window: "08:00-14:30",
      status: "open",
      note: "記憶體、電池、出口股參考。",
    },
    {
      market: "台灣",
      label: "加權指數 / 台指期",
      window: "09:00-13:30",
      status: "not_open",
      note: "開盤前先看台幣、台指期與半導體。",
    },
    {
      market: "香港 / A股",
      label: "恆生 / 上證 / 滬深300",
      window: "09:30-12:00, 13:00-16:00",
      status: "not_open",
      note: "中國需求、政策與港股科技股。",
    },
    {
      market: "歐洲",
      label: "Stoxx 600 / DAX / FTSE 100",
      window: "夏令約 15:00 後",
      status: "not_open",
      note: "下午接力觀察歐股與歐元。",
    },
    {
      market: "美國",
      label: "道瓊 / 標普500 / 那斯達克",
      window: "夏令 21:30-04:00",
      status: "closed",
      note: "台灣早上主要看昨晚收盤與期貨。",
    },
  ],
  snapshots: [],
  popular_news: [],
  overnight_risk: [],
  stories: [
    {
      title: "先看隔夜美股、歐股，再看亞洲開盤順序。",
      why: "早上需要的是全球市場脈絡，不是只看單一公司或單一產業。",
      tag: "新版主軸",
    },
    {
      title: "油金、美元、利率放在同一排看。",
      why: "商品、匯率與利率常一起影響風險情緒，但不直接代表可以買賣。",
      tag: "市場背景",
    },
  ],
  glossary: [
    {
      term: "費半",
      english: "PHLX Semiconductor Index",
      meaning: "美國主要半導體股票指數，常被用來觀察 AI 與晶片族群氣氛。",
    },
    {
      term: "VIX",
      english: "Volatility Index",
      meaning: "市場恐慌與避險情緒指標，數字升高通常代表波動變大。",
    },
    {
      term: "殖利率",
      english: "Treasury yield",
      meaning: "債券市場利率。美債殖利率上升時，成長股與科技股常會承壓。",
    },
  ],
  disclaimer: "本頁提供市場資訊與教育內容，不構成個人化投資建議或買賣建議。",
};

export default async function Page() {
  const live = await getLatestEvidence();
  const data = live ?? DEMO;
  const isLive = live !== null;
  const liveChanges =
    isLive && data.watchlist_id ? await getChanges(data.watchlist_id) : null;
  const changesData = liveChanges ?? DEMO_CHANGES;
  const radarData = (await getMorningRadar()) ?? DEMO_RADAR;
  const attributionPlan = await getFundAttributionPlan();
  const latestAttribution = await getLatestFundAttribution();
  const ts = data.created_at.slice(0, 16).replace("T", " ");
  const supported = data.claims.filter((c) => c.support_status === "supported").length;
  const flagged = data.claims.length - supported;
  const attentionClaims = data.claims.filter((c) => c.support_status !== "supported");

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-hairline bg-bar">
        <div className="mx-auto flex min-h-12 max-w-7xl flex-wrap items-center justify-between gap-2 px-3 py-2 sm:px-6">
          <div className="flex min-w-0 basis-full items-center gap-2 sm:basis-auto sm:gap-3">
            <span className="block h-5 w-1.5 bg-navy-700" aria-hidden />
            <span className="truncate font-serif text-[16px] font-semibold tracking-tight text-neutral-30 sm:text-[17px]">
              Morning Market Radar
            </span>
            <span className="th-label mt-px hidden sm:inline">Taiwan morning · Evidence-backed</span>
          </div>
          <div className="flex min-w-0 basis-full items-center justify-between gap-2 sm:basis-auto sm:justify-start sm:gap-3">
            <RegionSwitcher />
            <ThemeToggle />
            <TextSizeToggle />
            <HideOnTaiwan>
              <span
                className={`rounded-(--radius-ctl) border px-2 py-0.5 font-mono text-[10px] ${
                  isLive ? "border-up/60 text-up" : "border-elevated text-neutral-90"
                }`}
              >
                {isLive ? "● LIVE" : "○ DEMO DATA"}
              </span>
              <span className="hidden rounded-(--radius-ctl) border border-flag/60 px-2 py-0.5 text-[11px] font-medium text-flag sm:inline">
                INTERNAL RESEARCH DRAFT
              </span>
            </HideOnTaiwan>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-4 px-3 py-4 sm:space-y-5 sm:px-6 sm:py-6">
        <MorningMarketDashboard radar={radarData} />

        <FundAttributionPanel plan={attributionPlan} latest={latestAttribution?.result ?? null} />

        <HideOnTaiwan>
        <div className="flex flex-col gap-1 border-t border-hairline pt-5 sm:flex-row sm:items-end sm:justify-between">
          <div className="min-w-0">
            <p className="th-label">Secondary module · Beta</p>
            <h2 className="font-serif text-xl font-semibold leading-tight text-neutral-30 sm:text-2xl">
              Evidence-backed company brief
            </h2>
          </div>
          <p className="reader-meta max-w-xl break-words text-neutral-90">
            A separate research module: SEC filing changes and macro deltas, validated claim-by-claim against
            stored source spans. Shown {isLive ? "live from your watchlist." : "with sample data — start the backend to go live."}
          </p>
        </div>

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px] lg:items-start">
          <div className="min-w-0 space-y-4 sm:space-y-5">
            <article className="overflow-hidden rounded-(--radius-card) border border-hairline bg-card px-4 py-4 sm:px-6 sm:py-5">
              <div className="border-b border-hairline pb-4">
                <p className="th-label mb-2 break-words">Morning brief · Watchlist: {data.watchlist}</p>
                <h1 className="font-serif text-xl font-semibold leading-tight text-neutral-30 sm:text-2xl">
                  What changed since yesterday?
                </h1>
                <p className="reader-meta mt-2 break-words font-mono text-[11px] leading-relaxed text-neutral-90">
                  generated {ts} UTC · {data.claims.length} claims · {supported} validated ·{" "}
                  {flagged} flagged · status {data.status}
                </p>
              </div>

              {attentionClaims.length > 0 && (
                <section className="mt-5 min-w-0 rounded-(--radius-ctl) border border-flag/40 bg-page/70 px-3 py-3 sm:px-4">
                  <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-2">
                    <p className="th-label text-flag">Needs attention</p>
                    <span className="min-w-0 break-words font-mono text-[10px] text-neutral-90">
                      {attentionClaims.length} claim{attentionClaims.length > 1 ? "s" : ""} blocked from clean approval
                    </span>
                  </div>
                  <ul className="mt-2 grid gap-2">
                    {attentionClaims.map((claim) => (
                      <li key={claim.claim_id} className="reader-body grid min-w-0 gap-2 text-[13px] leading-relaxed sm:flex sm:items-start">
                        <a
                          href={`#claim-${String(claim.index).padStart(3, "0")}`}
                          className="w-fit shrink-0 rounded-(--radius-ctl) border border-flag/60 px-1.5 py-0.5 font-mono text-[10px] text-flag hover:bg-flag hover:text-white"
                        >
                          C-{String(claim.index).padStart(3, "0")}
                        </a>
                        <span className="min-w-0 break-words text-neutral-50">{claim.text}</span>
                        <RepairClaimButton claimId={claim.claim_id} apiUrl={API_URL} live={isLive} />
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              <BriefCanvas
                briefId={data.brief_id}
                sections={data.sections}
                claims={data.claims}
                initialEdits={data.user_edits?.sections ?? {}}
                initialStatus={data.status}
                initialTranslations={data.translations ?? {}}
                apiUrl={API_URL}
                live={isLive}
              />

              {data.open_questions.length > 0 && (
                <section className="mt-5 rounded-(--radius-ctl) border-l-2 border-action bg-page/60 px-4 py-3">
                  <p className="th-label">Analyst open questions</p>
                  <ul className="reader-body mt-1 list-inside list-disc text-[13px] text-neutral-50">
                    {data.open_questions.map((q) => (
                      <li key={q}>{q}</li>
                    ))}
                  </ul>
                </section>
              )}
            </article>

            <div className="flex flex-wrap items-center gap-2 px-1">
              <span className="th-label">Export</span>
              {[
                { fmt: "markdown", href: `${API_URL}/briefs/${data.brief_id}/markdown`, label: "MD" },
                { fmt: "pdf", href: `${API_URL}/briefs/${data.brief_id}/export/pdf`, label: "PDF" },
                { fmt: "pptx", href: `${API_URL}/briefs/${data.brief_id}/export/pptx`, label: "PPTX" },
                { fmt: "xlsx", href: `${API_URL}/briefs/${data.brief_id}/export/xlsx`, label: "XLSX" },
              ].map(({ fmt, href, label }) => (
                <a
                  key={fmt}
                  href={isLive ? href : undefined}
                  aria-disabled={!isLive}
                  className={`rounded-(--radius-ctl) border px-2.5 py-1 font-mono text-[11px] ${
                    isLive
                      ? "border-elevated text-neutral-50 hover:border-action hover:text-neutral-30"
                      : "pointer-events-none border-hairline text-neutral-90 opacity-50"
                  }`}
                >
                  ↓ {label}
                </a>
              ))}
              <span className="font-mono text-[10px] text-neutral-90">
                every export carries the watermark, evidence ledger, and AI marking
              </span>
            </div>

            <ChangesPanel changes={changesData} />
          </div>

          <EvidenceRail claims={data.claims} changes={changesData} />
        </div>

        <EvidenceLedger claims={data.claims} apiUrl={API_URL} live={isLive} />
        </HideOnTaiwan>

        <footer className="reader-meta px-1 pb-6 text-[11px] leading-relaxed text-neutral-90">
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
