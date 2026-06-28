import type { ChangesPayload, ClaimRow } from "@/lib/api";

function StatusDot({ status }: { status: string }) {
  const cls =
    status === "supported"
      ? "bg-up"
      : status === "unsupported"
        ? "bg-down"
        : "bg-flag";
  return <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${cls}`} aria-hidden />;
}

export default function EvidenceRail({
  claims,
  changes,
}: {
  claims: ClaimRow[];
  changes: ChangesPayload;
}) {
  const supported = claims.filter((claim) => claim.support_status === "supported").length;
  const flagged = claims.filter((claim) => claim.support_status !== "supported");
  const citationCount = claims.reduce((count, claim) => count + claim.citations.length, 0);
  const latestSources = [
    ...changes.new_documents.map((doc) => ({
      key: doc.document_id,
      label: doc.publisher,
      meta: [doc.doc_type, doc.accession ?? doc.publication_date?.slice(0, 10)].filter(Boolean).join(" · "),
    })),
    ...claims.flatMap((claim) =>
      claim.citations.slice(0, 1).map((citation) => ({
        key: `${claim.claim_id}-${citation.span_id}`,
        label: citation.publisher ?? "Evidence source",
        meta: [citation.doc_type, citation.section, citation.accession].filter(Boolean).join(" · "),
      })),
    ),
  ].slice(0, 6);

  return (
    <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
      <section className="rounded-(--radius-card) border border-hairline bg-card shadow-[var(--shadow-soft)]">
        <div className="border-b border-hairline px-4 py-3">
          <p className="th-label">Audit status</p>
          <h2 className="reader-heading mt-1 text-[15px] font-semibold text-neutral-30">
            {supported}/{claims.length} claims validated
          </h2>
        </div>
        <div className="grid grid-cols-3 divide-x divide-hairline">
          <div className="px-3 py-3">
            <p className="th-label">Claims</p>
            <p className="mt-1 font-mono text-lg font-semibold text-neutral-30">{claims.length}</p>
          </div>
          <div className="px-3 py-3">
            <p className="th-label">Cites</p>
            <p className="mt-1 font-mono text-lg font-semibold text-neutral-30">{citationCount}</p>
          </div>
          <div className="px-3 py-3">
            <p className="th-label">Flags</p>
            <p className={`mt-1 font-mono text-lg font-semibold ${flagged.length ? "text-flag" : "text-up"}`}>
              {flagged.length}
            </p>
          </div>
        </div>
      </section>

      {flagged.length > 0 && (
        <section className="rounded-(--radius-card) border border-flag/40 bg-card shadow-[var(--shadow-soft)]">
          <div className="border-b border-flag/30 px-4 py-3">
            <p className="th-label text-flag">Needs review</p>
          </div>
          <ul className="divide-y divide-hairline">
            {flagged.map((claim) => (
              <li key={claim.claim_id}>
                <a
                  href={`#claim-${String(claim.index).padStart(3, "0")}`}
                  className="flex gap-2 px-4 py-3 hover:bg-page/50"
                >
                  <StatusDot status={claim.support_status} />
                  <span className="min-w-0">
                    <span className="block font-mono text-[10px] text-flag">C-{String(claim.index).padStart(3, "0")}</span>
                    <span className="reader-body block text-[12px] text-neutral-50">{claim.text}</span>
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="rounded-(--radius-card) border border-hairline bg-card shadow-[var(--shadow-soft)]">
        <div className="border-b border-hairline px-4 py-3">
          <p className="th-label">Source tape</p>
        </div>
        <ul className="divide-y divide-hairline">
          {latestSources.length === 0 && (
            <li className="reader-body px-4 py-3 text-[12px] text-neutral-90">No source changes detected.</li>
          )}
          {latestSources.map((source) => (
            <li key={source.key} className="px-4 py-3">
              <p className="reader-body text-[12px] font-medium text-neutral-50">{source.label}</p>
              <p className="reader-meta mt-0.5 break-words font-mono text-[10px] text-neutral-90">{source.meta}</p>
            </li>
          ))}
        </ul>
      </section>
    </aside>
  );
}
