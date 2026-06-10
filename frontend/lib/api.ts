// Server-side API client with graceful degradation: every helper returns null on
// failure so the dashboard falls back to demo data instead of erroring.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type CitationDetail = {
  span_id: string;
  validator: string; // pass | fail | pending
  validated_at: string | null;
  evidence_quote: string;
  span: [number | null, number | null];
  section: string | null;
  chunk_text: string | null;
  doc_type: string | null;
  accession: string | null;
  source_url: string | null;
  publisher: string | null;
  retrieved_at: string | null;
  checksum_sha256: string | null;
};

export type ClaimRow = {
  claim_id: string;
  index: number;
  text: string;
  type: string;
  confidence: string;
  support_status: string; // supported | unsupported | flagged
  needs_review: boolean;
  citations: CitationDetail[];
};

export type BriefSectionData = { title: string; content_markdown: string };

export type SectionEdit = {
  action: "accept" | "reject" | "edit" | "needs_source";
  content: string | null;
  at: string;
  by: string;
};

export type EvidencePayload = {
  brief_id: string;
  watchlist: string;
  watchlist_id?: string;
  status: string;
  created_at: string;
  sections: BriefSectionData[];
  open_questions: string[];
  claims: ClaimRow[];
  user_edits?: { sections?: Record<string, SectionEdit> };
};

export type ChangesPayload = {
  watchlist_id: string;
  since: string | null;
  previous_brief_id: string | null;
  new_documents: {
    document_id: string;
    doc_type: string;
    accession: string | null;
    publisher: string;
    url: string;
    publication_date: string | null;
  }[];
  filing_diffs: {
    cik: string;
    form: string;
    publisher: string;
    accession_new: string | null;
    accession_old: string | null;
    sections: { section: string; added: number; removed: number; modified: number }[];
    samples: { kind: string; section: string; text: string; similarity: number }[];
  }[];
  macro_deltas: {
    series_id: string;
    latest_date: string | null;
    latest_value: number | null;
    prev_date: string | null;
    prev_value: number | null;
    change: number | null;
    change_pct: number | null;
    revisions: { date: string; old_value: number; new_value: number }[];
    vintage?: string | null;
  }[];
};

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_URL}${path}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(1500),
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

/** Change detection for a watchlist, or null when unreachable. */
export async function getChanges(watchlistId: string): Promise<ChangesPayload | null> {
  return fetchJson<ChangesPayload>(`/watchlists/${watchlistId}/changes`);
}

/** Latest brief's evidence payload, or null when the API/DB isn't reachable. */
export async function getLatestEvidence(): Promise<EvidencePayload | null> {
  const watchlists = await fetchJson<{ id: string; name: string }[]>("/watchlists");
  if (!watchlists?.length) return null;

  for (const wl of watchlists) {
    const briefs = await fetchJson<{ brief_id: string }[]>(`/watchlists/${wl.id}/briefs`);
    if (briefs?.length) {
      return fetchJson<EvidencePayload>(`/briefs/${briefs[0].brief_id}/evidence`);
    }
  }
  return null;
}
