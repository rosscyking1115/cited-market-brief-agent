"use client";

// Evidence ledger — the "click a claim, see the proof" surface (plan §14).
// Client island: row expansion + feedback posts. Everything else stays RSC.

import { useState } from "react";
import type { ClaimRow } from "@/lib/api";

const FEEDBACK_KINDS = [
  { kind: "useful", label: "Useful" },
  { kind: "not_useful", label: "Not useful" },
  { kind: "wrong", label: "Wrong" },
  { kind: "needs_source", label: "Needs source" },
] as const;

function StatusBadge({ status }: { status: string }) {
  if (status === "supported") return <span className="font-medium text-up">✓ PASS</span>;
  if (status === "unsupported") return <span className="font-medium text-down">▼ UNSUPPORTED</span>;
  return <span className="font-medium text-flag">⚑ FLAG</span>;
}

function FeedbackBar({
  claimId,
  apiUrl,
  live,
}: {
  claimId: string;
  apiUrl: string;
  live: boolean;
}) {
  const [sent, setSent] = useState<string | null>(null);
  const [error, setError] = useState(false);

  async function send(kind: string) {
    if (!live || sent) return;
    try {
      const res = await fetch(`${apiUrl}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim_id: claimId, kind }),
      });
      if (!res.ok) throw new Error();
      setSent(kind);
    } catch {
      setError(true);
    }
  }

  return (
    <div className="mt-3 flex items-center gap-2">
      <span className="th-label">Feedback</span>
      {FEEDBACK_KINDS.map(({ kind, label }) => (
        <button
          key={kind}
          type="button"
          onClick={() => send(kind)}
          disabled={!live || sent !== null}
          className={`rounded-(--radius-ctl) border px-2 py-1 text-[11px] transition-colors ${
            sent === kind
              ? "border-up text-up"
              : "border-elevated text-neutral-70 hover:border-action hover:text-neutral-30 disabled:opacity-40"
          }`}
          title={live ? undefined : "Connect the API to send feedback"}
        >
          {sent === kind ? `✓ ${label}` : label}
        </button>
      ))}
      {error && <span className="text-[11px] text-down">▼ failed — retry later</span>}
    </div>
  );
}

export default function EvidenceLedger({
  claims,
  apiUrl,
  live,
}: {
  claims: ClaimRow[];
  apiUrl: string;
  live: boolean;
}) {
  const [openId, setOpenId] = useState<string | null>(null);

  return (
    <section id="ledger" className="rounded-(--radius-card) border border-hairline bg-card">
      <h2 className="th-label flex items-center justify-between border-b border-hairline px-4 py-2.5">
        <span>Evidence ledger — click a claim for the proof</span>
        <span>{claims.filter((c) => c.support_status === "supported").length}/{claims.length} validated</span>
      </h2>
      <ul>
        {claims.map((claim) => {
          const open = openId === claim.claim_id;
          return (
            <li key={claim.claim_id} className="border-t border-hairline first:border-t-0">
              <button
                type="button"
                aria-expanded={open}
                onClick={() => setOpenId(open ? null : claim.claim_id)}
                className="grid w-full grid-cols-[64px_1fr_120px_90px] items-start gap-2 px-4 py-2 text-left text-[13px] hover:bg-page/40"
              >
                <span className="font-mono text-[11px] text-neutral-90">
                  C-{String(claim.index).padStart(3, "0")}
                </span>
                <span className="text-neutral-50">{claim.text}</span>
                <span className="font-mono text-[11px] text-neutral-70">{claim.type}</span>
                <span className="text-right">
                  <StatusBadge status={claim.support_status} />
                </span>
              </button>

              {open && (
                <div className="border-t border-hairline bg-page/60 px-6 py-4">
                  {claim.citations.length === 0 && (
                    <p className="text-[12px] text-flag">
                      ⚑ No citations — this claim cannot export and needs analyst review.
                    </p>
                  )}
                  {claim.citations.map((cit) => (
                    <div key={cit.span_id} className="mb-4 last:mb-0">
                      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                        <StatusBadge status={cit.validator === "pass" ? "supported" : "flagged"} />
                        <span className="font-mono text-[11px] text-neutral-30">
                          {cit.publisher} {cit.doc_type} {cit.accession ?? ""}
                        </span>
                        {cit.section && (
                          <span className="font-mono text-[11px] text-neutral-90">{cit.section}</span>
                        )}
                        {cit.span?.[0] != null && (
                          <span className="font-mono text-[11px] text-neutral-90">
                            chars {cit.span[0]}–{cit.span[1]}
                          </span>
                        )}
                      </div>
                      {cit.evidence_quote && (
                        <blockquote className="mt-2 border-l-2 border-action pl-3 text-[12px] italic text-neutral-50">
                          “{cit.evidence_quote}”
                        </blockquote>
                      )}
                      {cit.chunk_text && (
                        <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded-(--radius-ctl) border border-hairline bg-card p-3 font-mono text-[11px] leading-relaxed text-neutral-70">
                          {cit.chunk_text}
                        </pre>
                      )}
                      <p className="mt-1.5 font-mono text-[10px] text-neutral-90">
                        {cit.source_url && (
                          <a
                            href={cit.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-action hover:underline"
                          >
                            {cit.source_url}
                          </a>
                        )}
                        {cit.retrieved_at && <> · retrieved {cit.retrieved_at.slice(0, 19)}Z</>}
                        {cit.checksum_sha256 && <> · sha256 {cit.checksum_sha256.slice(0, 12)}…</>}
                      </p>
                    </div>
                  ))}
                  <FeedbackBar claimId={claim.claim_id} apiUrl={apiUrl} live={live} />
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
