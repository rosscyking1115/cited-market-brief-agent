import type { Metadata } from "next";
import BriefCanvas from "@/app/components/BriefCanvas";
import ChangesPanel from "@/app/components/ChangesPanel";
import EvidenceLedger from "@/app/components/EvidenceLedger";
import EvidenceRail from "@/app/components/EvidenceRail";
import RepairClaimButton from "@/app/components/RepairClaimButton";
import WorkspaceHeader from "@/app/components/WorkspaceHeader";
import { API_URL, getChanges, getLatestEvidence } from "@/lib/api";
import { DEMO_BRIEF, DEMO_CHANGES } from "@/lib/demo-data";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Evidence-backed company brief",
  description: "An English source-of-record research workspace with claim-level citation review.",
};

const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "1";

export default async function BriefPage() {
  const live = DEMO_MODE ? null : await getLatestEvidence();
  const data = live ?? DEMO_BRIEF;
  const isLive = live !== null;
  const liveChanges = isLive && data.watchlist_id ? await getChanges(data.watchlist_id) : null;
  const changes = liveChanges ?? DEMO_CHANGES;
  const timestamp = data.created_at.slice(0, 16).replace("T", " ");
  const supported = data.claims.filter((claim) => claim.support_status === "supported").length;
  const attentionClaims = data.claims.filter((claim) => claim.support_status !== "supported");

  return (
    <div className="min-h-screen">
      <WorkspaceHeader workspace="brief" />
      <main id="main-content" className="mx-auto max-w-7xl space-y-5 px-3 py-4 sm:px-6 sm:py-6">
        <section className="flex flex-col gap-2 border-b border-hairline pb-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="th-label">Research workspace · English source of record</p>
            <h1 className="mt-1 font-serif text-2xl font-semibold leading-tight text-neutral-30 sm:text-3xl">
              Evidence-backed company brief
            </h1>
            <p className="reader-body mt-2 max-w-3xl text-[14px] leading-relaxed text-neutral-70">
              SEC filing changes and macro deltas, checked claim by claim against stored source spans.
              Traditional Chinese and Korean are labelled reading aids; review and approval stay tied to the English original.
            </p>
          </div>
          <span className={`w-fit rounded-(--radius-ctl) border px-2 py-1 font-mono text-[10px] ${isLive ? "border-up/60 text-up" : "border-elevated text-neutral-90"}`}>
            {isLive ? "● LIVE WORKSPACE" : "○ DEMO DATA"}
          </span>
        </section>

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px] lg:items-start">
          <div className="min-w-0 space-y-5">
            <article className="overflow-hidden rounded-(--radius-card) border border-hairline bg-card px-4 py-4 shadow-[var(--shadow-soft)] sm:px-6 sm:py-5">
              <div className="border-b border-hairline pb-4">
                <p className="th-label mb-2 break-words">Morning brief · Watchlist: {data.watchlist}</p>
                <h2 className="font-serif text-xl font-semibold leading-tight text-neutral-30 sm:text-2xl">
                  What changed since yesterday?
                </h2>
                <p className="reader-meta mt-2 break-words font-mono text-[11px] leading-relaxed text-neutral-90">
                  generated {timestamp} UTC · {data.claims.length} claims · {supported} validated · {attentionClaims.length} flagged · status {data.status}
                </p>
              </div>

              {attentionClaims.length > 0 && (
                <section className="mt-5 rounded-(--radius-ctl) border border-flag/40 bg-page/70 px-3 py-3 sm:px-4" aria-labelledby="attention-title">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <p id="attention-title" className="th-label text-flag">Needs attention</p>
                    <span className="font-mono text-[10px] text-neutral-90">{attentionClaims.length} claim blocked from clean approval</span>
                  </div>
                  <ul className="mt-2 grid gap-2">
                    {attentionClaims.map((claim) => (
                      <li key={claim.claim_id} className="reader-body grid min-w-0 gap-2 text-[13px] leading-relaxed sm:flex sm:items-start">
                        <a href={`#claim-${String(claim.index).padStart(3, "0")}`} className="w-fit shrink-0 rounded-(--radius-ctl) border border-flag/60 px-1.5 py-0.5 font-mono text-[10px] text-flag hover:bg-flag hover:text-white">
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
                <section className="mt-5 rounded-(--radius-ctl) border border-action/40 bg-page/60 px-4 py-3">
                  <p className="th-label">Analyst open questions</p>
                  <ul className="reader-body mt-1 list-inside list-disc text-[13px] text-neutral-50">
                    {data.open_questions.map((question) => <li key={question}>{question}</li>)}
                  </ul>
                </section>
              )}
            </article>

            <div className="flex flex-wrap items-center gap-2 px-1" aria-label="Brief exports">
              <span className="th-label">Export</span>
              {["markdown", "pdf", "pptx", "xlsx"].map((format) => (
                <a
                  key={format}
                  href={isLive ? `${API_URL}/briefs/${data.brief_id}/${format === "markdown" ? "markdown" : `export/${format}`}` : undefined}
                  aria-disabled={!isLive}
                  className={`rounded-(--radius-ctl) border px-2.5 py-1 font-mono text-[11px] uppercase ${isLive ? "border-elevated text-neutral-50 hover:border-action" : "pointer-events-none border-hairline text-neutral-90 opacity-50"}`}
                >
                  ↓ {format === "markdown" ? "MD" : format}
                </a>
              ))}
            </div>

            <ChangesPanel changes={changes} />
          </div>
          <EvidenceRail claims={data.claims} changes={changes} />
        </div>

        <EvidenceLedger claims={data.claims} apiUrl={API_URL} live={isLive} />

        <footer className="reader-meta px-1 pb-6 text-[11px] leading-relaxed text-neutral-90">
          Internal research draft. Factual, cited and non-personalised. AI-assisted content requires human review before external use. Sources include SEC EDGAR and FRED.
        </footer>
      </main>
    </div>
  );
}
