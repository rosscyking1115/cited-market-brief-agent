// Server-side API client with graceful degradation: every helper returns null on
// failure so the dashboard falls back to demo data instead of erroring.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const SERVER_API_URL = process.env.API_URL ?? API_URL;

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

export type BriefLocale = "original" | "zh-Hant" | "ko";

export type BriefTranslation = {
  locale: Exclude<BriefLocale, "original">;
  label: string;
  disclaimer: string;
  sections: BriefSectionData[];
  open_questions: string[];
};

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
  translations?: Partial<Record<Exclude<BriefLocale, "original">, BriefTranslation>>;
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

export type MarketStatus = "not_open" | "open" | "lunch" | "closed" | "weekend";
export type SnapshotTone = "up" | "down" | "flat" | "pending";
export type NewsRankKind = "most_read" | "most_viewed" | "most_covered" | "trending" | "latest";
export type NewsSourceStatus = "official_api" | "rss" | "licensed" | "planned" | "manual_reference";

export type MarketClockItem = {
  market: string;
  label: string;
  window: string;
  status: MarketStatus;
  note: string;
};

export type MarketSnapshotItem = {
  label: string;
  local_name: string;
  value: string;
  change: string;
  tone: SnapshotTone;
  source: string;
  source_status: "live" | "delayed" | "eod" | "planned";
};

export type MarketStoryItem = {
  title: string;
  why: string;
  tag: string;
};

export type PopularNewsItem = {
  rank: number;
  title: string;
  title_zh_hant: string;
  source: string;
  url: string | null;
  published_at: string | null;
  window: "1h" | "24h";
  rank_kind: NewsRankKind;
  source_status: NewsSourceStatus;
  category: string;
  why: string;
  rights_note: string;
};

export type OvernightRiskItem = {
  rank: number;
  symbol: string;
  name: string;
  local_name: string;
  group: "futures" | "volatility" | "fx" | "commodities" | "rates";
  value: string;
  change: string;
  tone: SnapshotTone;
  source: string;
  source_status: "live" | "delayed" | "eod" | "planned";
  why: string;
  rights_note: string;
};

export type GlossaryItem = {
  term: string;
  english: string;
  meaning: string;
};

export type MorningRadarPayload = {
  generated_at: string;
  timezone: string;
  headline: string;
  summary_points: [string, string, string];
  current_focus: string;
  market_clock: MarketClockItem[];
  snapshots: MarketSnapshotItem[];
  popular_news: PopularNewsItem[];
  overnight_risk: OvernightRiskItem[];
  stories: MarketStoryItem[];
  glossary: GlossaryItem[];
  disclaimer: string;
};

export type AutomationPolicyItem = {
  label: string;
  status: "allowed" | "manual_first" | "needs_review" | "blocked";
  note: string;
};

export type FundAttributionPlanPayload = {
  title: string;
  target_use_case: string;
  first_region: string;
  daily_trigger: string;
  required_inputs: string[];
  first_supported_workflow: string[];
  automation_policy: AutomationPolicyItem[];
  disclaimer: string;
};

export type HoldingInput = {
  symbol: string;
  name: string;
  weight_pct: number;
  return_pct: number | null;
};

export type AttributionRow = {
  symbol: string;
  name: string;
  weight_pct: number;
  return_pct: number | null;
  contribution_pct: number | null;
  direction: "positive" | "negative" | "flat" | "missing";
};

export type HoldingsParsePayload = {
  source_name: string;
  parsed_count: number;
  skipped_rows: number;
  detected_columns: string[];
  holdings: HoldingInput[];
  warnings: string[];
  source_notes: string[];
};

export type HoldingReturnFillPayload = {
  as_of: string;
  filled_count: number;
  missing_symbols: string[];
  holdings: HoldingInput[];
  warnings: string[];
  source_notes: string[];
};

export type FundAttributionPayload = {
  fund_name: string;
  benchmark_name: string;
  as_of: string;
  fund_return_pct: number;
  benchmark_return_pct: number;
  active_return_pct: number;
  explained_return_pct: number;
  residual_pct: number;
  holdings_count: number;
  contributors: AttributionRow[];
  drags: AttributionRow[];
  missing_returns: AttributionRow[];
  source_notes: string[];
  automation_policy: AutomationPolicyItem[];
  summary_zh_hant: string;
  disclaimer: string;
};

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${SERVER_API_URL}${path}`, {
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

/** Taiwan-morning market radar payload, or null when the API/DB isn't reachable. */
export async function getMorningRadar(): Promise<MorningRadarPayload | null> {
  return fetchJson<MorningRadarPayload>("/market-radar");
}

/** Fund attribution workflow plan, or null when the API isn't reachable. */
export async function getFundAttributionPlan(): Promise<FundAttributionPlanPayload | null> {
  return fetchJson<FundAttributionPlanPayload>("/fund-attribution/plan");
}
