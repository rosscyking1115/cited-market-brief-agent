"use client";

import type { ClaimRow, SectionEdit } from "@/lib/api";

function CheckRow({
  ok,
  label,
  detail,
}: {
  ok: boolean;
  label: string;
  detail: string;
}) {
  return (
    <li className="reader-body flex items-start gap-2 py-1.5 text-[13px]">
      <span
        className={`mt-0.5 font-mono text-[11px] ${ok ? "text-up" : "text-flag"}`}
        aria-hidden
      >
        {ok ? "✓" : "⚑"}
      </span>
      <span>
        <span className="font-medium text-neutral-30">{label}</span>
        <span className="block text-neutral-70 sm:ml-2 sm:inline">{detail}</span>
      </span>
    </li>
  );
}

export default function ApprovalChecklist({
  sectionsCount,
  edits,
  claims,
}: {
  sectionsCount: number;
  edits: Record<string, SectionEdit>;
  claims: ClaimRow[];
}) {
  const resolvedSections = Array.from({ length: sectionsCount }, (_, i) => edits[String(i)]).filter(
    (entry) => entry && entry.action !== "needs_source",
  ).length;
  const sectionsOk = resolvedSections === sectionsCount;
  const supported = claims.filter((claim) => claim.support_status === "supported").length;
  const cited = claims.filter((claim) => claim.citations.length > 0).length;
  const claimsOk = supported === claims.length;
  const citationsOk = cited === claims.length;
  const ready = sectionsOk && claimsOk && citationsOk;

  return (
    <section
      className={`mt-5 rounded-(--radius-ctl) border px-4 py-3 ${
        ready ? "border-up/50 bg-page/70" : "border-flag/40 bg-page/70"
      }`}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className={`th-label ${ready ? "text-up" : "text-flag"}`}>
          {ready ? "Approval ready" : "Approval checklist"}
        </p>
        <span className="font-mono text-[10px] text-neutral-90">
          {ready ? "all gates clear" : "approval blocked"}
        </span>
      </div>
      <ul className="mt-2">
        <CheckRow
          ok={sectionsOk}
          label="Sections resolved"
          detail={`${resolvedSections}/${sectionsCount} accepted, edited, or rejected`}
        />
        <CheckRow
          ok={claimsOk}
          label="Claims validated"
          detail={`${supported}/${claims.length} supported`}
        />
        <CheckRow
          ok={citationsOk}
          label="Evidence attached"
          detail={`${cited}/${claims.length} claims have citations`}
        />
        <CheckRow
          ok={ready}
          label="Exports approvable"
          detail={ready ? "approved watermark can be applied" : "draft watermark remains required"}
        />
      </ul>
    </section>
  );
}
