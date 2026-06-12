// "Since last brief" panel (Phase 3) — server-renderable, no client JS.
// New filings, risk-factor diffs (+/− blocks), and vintage-aware macro deltas.

import type { ChangesPayload } from "@/lib/api";

function DiffSample({
  kind,
  section,
  text,
}: {
  kind: string;
  section: string;
  text: string;
}) {
  const mark =
    kind === "added" ? (
      <span className="text-up">+</span>
    ) : kind === "removed" ? (
      <span className="text-down">−</span>
    ) : (
      <span className="text-flag">~</span>
    );
  return (
    <li className="reader-body grid grid-cols-[16px_56px_1fr] gap-2 py-1 text-[12px] leading-relaxed">
      <span className="w-3 shrink-0 text-center font-mono">{mark}</span>
      <span className="font-mono text-[10px] text-neutral-90 shrink-0 mt-0.5 w-14">{section}</span>
      <span
        className={
          kind === "removed" ? "text-neutral-90 line-through decoration-down/50" : "text-neutral-50"
        }
      >
        {text}
        {text.length >= 280 && "…"}
      </span>
    </li>
  );
}

export default function ChangesPanel({ changes }: { changes: ChangesPayload }) {
  const since = changes.since ? changes.since.slice(0, 16).replace("T", " ") + " UTC" : "first run";
  const empty =
    changes.new_documents.length === 0 &&
    changes.filing_diffs.length === 0 &&
    changes.macro_deltas.length === 0;

  return (
    <section className="rounded-(--radius-card) border border-hairline bg-card">
      <h2 className="th-label flex flex-wrap items-center justify-between gap-1 border-b border-hairline px-4 py-2.5">
        <span>Since last brief</span>
        <span className="font-mono">{since}</span>
      </h2>

      {empty && (
        <p className="reader-body px-4 py-3 text-[13px] text-neutral-90">
          No new filings, diffs, or macro changes detected.
        </p>
      )}

      {changes.filing_diffs.map((diff) => (
        <div key={`${diff.cik}-${diff.form}`} className="border-t border-hairline px-4 py-3 first:border-t-0">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="reader-heading text-[13px] font-semibold text-neutral-30">
              {diff.publisher} {diff.form} — filing diff
            </span>
            <span className="break-all font-mono text-[10px] text-neutral-90">
              {diff.accession_old} → {diff.accession_new}
            </span>
            {diff.sections.map((s) => (
              <span key={s.section} className="font-mono text-[10px] text-neutral-70">
                {s.section}: <span className="text-up">+{s.added}</span>{" "}
                <span className="text-down">−{s.removed}</span>{" "}
                <span className="text-flag">~{s.modified}</span>
              </span>
            ))}
          </div>
          <ul className="mt-1.5">
            {diff.samples.map((s, i) => (
              <DiffSample key={i} kind={s.kind} section={s.section} text={s.text} />
            ))}
          </ul>
        </div>
      ))}

      {changes.macro_deltas.length > 0 && (
        <div className="border-t border-hairline px-4 py-3">
          <p className="reader-heading text-[13px] font-semibold text-neutral-30">Macro deltas</p>
          <div className="mt-1.5 overflow-x-auto">
            <table className="w-full min-w-[520px] text-[12px]">
              <thead>
                <tr className="th-label">
                  <th scope="col" className="py-1 text-left font-semibold">Series</th>
                  <th scope="col" className="py-1 text-right font-semibold">Latest</th>
                  <th scope="col" className="py-1 text-right font-semibold">Δ period</th>
                  <th scope="col" className="py-1 text-right font-semibold">Revisions</th>
                </tr>
              </thead>
              <tbody>
                {changes.macro_deltas.map((d) => (
                  <tr key={d.series_id} className="h-7 border-t border-hairline">
                    <td className="font-mono text-neutral-30">{d.series_id}</td>
                    <td className="num text-neutral-50">
                      {d.latest_value ?? "—"}{" "}
                      <span className="font-mono text-[10px] text-neutral-90">{d.latest_date}</span>
                    </td>
                    <td className="num">
                      {d.change == null ? (
                        <span className="text-neutral-90">—</span>
                      ) : (
                        <span className={d.change >= 0 ? "text-up" : "text-down"}>
                          {d.change >= 0 ? "▲" : "▼"} {d.change >= 0 ? "+" : "−"}
                          {Math.abs(d.change)}
                          {d.change_pct != null && ` (${Math.abs(d.change_pct).toFixed(2)}%)`}
                        </span>
                      )}
                    </td>
                    <td className="num">
                      {d.revisions.length === 0 ? (
                        <span className="text-neutral-90">none</span>
                      ) : (
                        <span className="text-flag" title={d.revisions.map((r) => `${r.date}: ${r.old_value} → ${r.new_value}`).join("\n")}>
                          ⚑ {d.revisions.length} vintage revision{d.revisions.length > 1 ? "s" : ""}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {changes.new_documents.length > 0 && (
        <div className="border-t border-hairline px-4 py-3">
          <p className="reader-heading text-[13px] font-semibold text-neutral-30">
            New sources ingested ({changes.new_documents.length})
          </p>
          <ul className="mt-1">
            {changes.new_documents.slice(0, 8).map((doc) => (
              <li key={doc.document_id} className="flex flex-wrap items-baseline gap-2 py-0.5 text-[12px]">
                <span className="rounded-(--radius-ctl) bg-navy-900 px-1.5 py-0.5 font-mono text-[10px] text-neutral-50">
                  {doc.doc_type}
                </span>
                <span className="text-neutral-50">{doc.publisher}</span>
                <span className="font-mono text-[10px] text-neutral-90">
                  {doc.accession ?? doc.publication_date?.slice(0, 10) ?? ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
