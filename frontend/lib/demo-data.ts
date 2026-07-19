import type {
  ChangesPayload,
  EvidencePayload,
  FundAttributionPayload,
  MorningRadarPayload,
} from "@/lib/api";

export const DEMO_BRIEF: EvidencePayload = {
  brief_id: "demo",
  watchlist: "US Semiconductors + Macro (sample)",
  status: "draft",
  created_at: "2026-06-10T06:21:00+00:00",
  sections: [
    {
      title: "Filing changes",
      content_markdown:
        "NVIDIA's 10-Q introduces a new export-control risk factor not present in the prior quarter [#0]. AMD disclosed a datacentre leadership change via 8-K [#1].",
    },
    {
      title: "Macro context",
      content_markdown:
        "May CPI decelerated 10bps versus the April vintage [#2]; the 10-year US Treasury yield held near 4.18% into the print.",
    },
  ],
  open_questions: ["What drove the sequential gross-margin change?"],
  claims: [
    {
      claim_id: "demo-0",
      index: 0,
      text: "NVDA 10-Q adds a new export-control risk factor versus the prior quarter",
      type: "filing_change",
      confidence: "high",
      support_status: "supported",
      needs_review: false,
      citations: [
        {
          span_id: "demo-span-0",
          validator: "pass",
          validated_at: "2026-06-10T06:21:05+00:00",
          evidence_quote: "new export control licensing requirements for advanced accelerator products",
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
      text: "AMD 8-K discloses a datacentre leadership change",
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
      text: "May CPI print decelerated 10bps versus the April vintage",
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
            "Consumer Price Index for All Urban Consumers. Data vintage: 2026-06-10. Observations: 2026-03: 325.8; 2026-04: 326.6; 2026-05: 327.1.",
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

export const DEMO_CHANGES: ChangesPayload = {
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
          text: "We are subject to new export control licensing requirements for advanced accelerator products.",
          similarity: 0,
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

export const DEMO_RADAR: MorningRadarPayload = {
  generated_at: "2026-07-15T10:00:00+00:00",
  timezone: "Asia/Taipei",
  headline: "今天先看全球市場，再看台股開盤",
  today_overview: "今日重點：聯準會維持利率，AI 晶片需求支撐科技股；油價因供給疑慮緩解而回落。（示範資料）",
  week_overview: "本週：全球資金轉進亞洲股市，半導體與科技類股相對強勢。（示範資料）",
  month_overview: "本月：半導體帶動台股月線收紅，市場聚焦 AI 需求與利率路徑。（示範資料）",
  summary_points: [
    "美股與歐股收盤先決定隔夜基調。",
    "各市場狀態依所在地的一般平日交易時段計算。",
    "油金、美元、利率用來判斷風險情緒，不作買賣建議。",
  ],
  current_focus: "台灣 · 已收盤",
  market_clock: [
    { market_id: "twse", time_zone: "Asia/Taipei", sessions: [{ opens_at: "2026-07-15T09:00:00+08:00", closes_at: "2026-07-15T13:30:00+08:00" }], market: "台灣", label: "TAIEX / Taiwan index futures", window: "09:00-13:30", status: "closed", note: "開盤前先看台幣、台指期與半導體。" },
    { market_id: "jpx", time_zone: "Asia/Tokyo", sessions: [{ opens_at: "2026-07-15T09:00:00+09:00", closes_at: "2026-07-15T11:30:00+09:00" }, { opens_at: "2026-07-15T12:30:00+09:00", closes_at: "2026-07-15T15:30:00+09:00" }], market: "日本", label: "Nikkei 225 / TOPIX", window: "09:00-11:30, 12:30-15:30", status: "closed", note: "亞洲第一棒，先看科技與匯率。" },
    { market_id: "krx", time_zone: "Asia/Seoul", sessions: [{ opens_at: "2026-07-15T09:00:00+09:00", closes_at: "2026-07-15T15:30:00+09:00" }], market: "韓國", label: "KOSPI / KOSDAQ", window: "09:00-15:30", status: "closed", note: "記憶體、電池、出口股參考。" },
    { market_id: "hkex", time_zone: "Asia/Hong_Kong", sessions: [{ opens_at: "2026-07-15T09:30:00+08:00", closes_at: "2026-07-15T12:00:00+08:00" }, { opens_at: "2026-07-15T13:00:00+08:00", closes_at: "2026-07-15T16:00:00+08:00" }], market: "香港", label: "Hang Seng / HKEX", window: "09:30-12:00, 13:00-16:00", status: "closed", note: "香港需求、政策與港股科技股。" },
    { market_id: "lse", time_zone: "Europe/London", sessions: [{ opens_at: "2026-07-15T08:00:00+01:00", closes_at: "2026-07-15T16:30:00+01:00" }], market: "英國", label: "FTSE 100 / LSE", window: "08:00-16:30", status: "open", note: "倫敦核心交易時段。" },
    { market_id: "xetra", time_zone: "Europe/Berlin", sessions: [{ opens_at: "2026-07-15T09:00:00+02:00", closes_at: "2026-07-15T17:30:00+02:00" }], market: "歐洲", label: "DAX / Xetra", window: "09:00-17:30", status: "open", note: "Xetra 核心交易時段。" },
    { market_id: "nyse", time_zone: "America/New_York", sessions: [{ opens_at: "2026-07-15T09:30:00-04:00", closes_at: "2026-07-15T16:00:00-04:00" }], market: "美國", label: "S&P 500 / Nasdaq / NYSE", window: "09:30-16:00", status: "not_open", note: "台灣早上主要看昨晚收盤與期貨。" },
  ],
  snapshots: [],
  popular_news: [
    { rank: 1, window: "1d", rank_kind: "most_viewed", source_status: "official_api", source: "Reuters", url: "https://www.reuters.com/", published_at: "2026-07-15T08:10:00+00:00", category: "市場", title: "Fed holds rates steady as inflation cools toward target", title_zh_hant: "聯準會按兵不動，通膨降溫接近目標", title_ko: "연준, 인플레이션 둔화 속 금리 동결", summary: "The central bank held its benchmark rate and signalled patience on cuts.", summary_zh: "聯準會維持基準利率不變，對降息保持耐心。", summary_ko: null, why: "利率路徑影響成長股評價。", rights_note: "示範資料。" },
    { rank: 2, window: "1d", rank_kind: "latest", source_status: "rss", source: "CNBC", url: "https://www.cnbc.com/", published_at: "2026-07-15T07:05:00+00:00", category: "半導體", title: "Nvidia leads chip rally on strong AI demand outlook", title_zh_hant: "AI 需求強勁，輝達領軍晶片股走高", title_ko: "강한 AI 수요 전망에 엔비디아가 반도체주 상승 주도", summary: "AI accelerator demand lifted chip shares in the US and Asia.", summary_zh: "AI 加速器需求續強，帶動美國與亞洲半導體股。", summary_ko: "AI 가속기 수요가 미국과 아시아 반도체주를 끌어올렸습니다.", why: "晶片族群牽動科技股風險情緒。", rights_note: "示範資料。" },
    { rank: 3, window: "1d", rank_kind: "latest", source_status: "rss", source: "MarketWatch", url: "https://www.marketwatch.com/", published_at: "2026-07-15T06:20:00+00:00", category: "能源", title: "Oil slips as supply concerns ease", title_zh_hant: "供給疑慮緩解，油價回落", title_ko: "공급 우려 완화에 유가 하락", summary: "Crude fell as traders reduced supply-disruption fears.", summary_zh: "供給中斷疑慮降低，原油走跌。", summary_ko: "공급 차질 우려가 줄면서 원유 가격이 하락했습니다.", why: "油價影響通膨與能源股。", rights_note: "示範資料。" },
    { rank: 4, window: "1w", rank_kind: "most_viewed", source_status: "official_api", source: "NYT", url: "https://www.nytimes.com/", published_at: "2026-07-12T09:00:00+00:00", category: "市場", title: "Global funds rotate into Asian equities", title_zh_hant: "全球資金轉進亞洲股市", title_ko: "글로벌 자금, 아시아 주식으로 이동", summary: "Investors added Asian exposure on valuation and earnings momentum.", summary_zh: "資金因評價與獲利動能轉進亞股。", summary_ko: "밸류에이션과 이익 모멘텀에 힘입어 아시아 비중이 늘었습니다.", why: "跨市場資金流向提供全球背景。", rights_note: "示範資料。" },
    { rank: 5, window: "1w", rank_kind: "latest", source_status: "rss", source: "BBC", url: "https://www.bbc.com/news/business", published_at: "2026-07-11T13:30:00+00:00", category: "匯率", title: "Dollar softens as rate-cut bets build", title_zh_hant: "降息預期升溫，美元走弱", title_ko: "금리 인하 기대에 달러 약세", summary: "The dollar eased as markets priced earlier rate cuts.", summary_zh: "市場提前反映降息，美元走弱。", summary_ko: "시장은 조기 금리 인하를 반영하며 달러가 약세를 보였습니다.", why: "美元強弱影響商品與全球資金流。", rights_note: "示範資料。" },
    { rank: 6, window: "1m", rank_kind: "most_viewed", source_status: "official_api", source: "NYT", url: "https://www.nytimes.com/section/business", published_at: "2026-06-30T08:00:00+00:00", category: "半導體", title: "Semiconductors lead a broad technology advance", title_zh_hant: "半導體帶動科技股走高", title_ko: "반도체주가 기술주 상승 주도", summary: "Chip strength carried the technology sector higher.", summary_zh: "半導體撐盤，帶動科技類股走高。", summary_ko: "반도체 강세가 기술주 상승을 이끌었습니다.", why: "月度回顧有助掌握中期族群輪動。", rights_note: "示範資料。" },
  ],
  overnight_risk: [
    { rank: 1, symbol: "VIX", name: "CBOE Volatility Index", local_name: "VIX 波動率指數", group: "volatility", value: "14.2", change: "-0.6", tone: "down", source: "FRED", source_status: "eod", why: "避險與市場波動壓力參考。", rights_note: "示範資料。" },
    { rank: 2, symbol: "USD/TWD", name: "US dollar / Taiwan dollar", local_name: "美元兌台幣", group: "fx", value: "31.85", change: "+0.12", tone: "up", source: "Alpha Vantage", source_status: "delayed", why: "影響台股電子與出口股情緒。", rights_note: "示範資料。" },
    { rank: 3, symbol: "USD-BROAD", name: "Broad US dollar index", local_name: "廣義美元指數", group: "fx", value: "119.4", change: "-0.2", tone: "down", source: "FRED", source_status: "eod", why: "美元強弱影響商品與資金流。", rights_note: "示範資料。" },
    { rank: 4, symbol: "WTI", name: "WTI crude oil", local_name: "西德州原油", group: "commodities", value: "68.4", change: "-1.1", tone: "down", source: "FRED", source_status: "eod", why: "油價牽動通膨與能源股。", rights_note: "示範資料。" },
    { rank: 5, symbol: "US10Y", name: "US 10-year Treasury yield", local_name: "美債 10 年期殖利率", group: "rates", value: "4.18%", change: "-0.03", tone: "down", source: "FRED", source_status: "eod", why: "利率變化影響科技股評價與美元。", rights_note: "示範資料。" },
  ],
  stories: [],
  glossary: [
    { term: "費半", english: "PHLX Semiconductor Index", meaning: "美國主要半導體股票指數，常用來觀察 AI 與晶片族群氣氛。" },
    { term: "VIX", english: "Volatility Index", meaning: "市場恐慌與避險情緒指標，數字升高通常代表波動變大。" },
    { term: "殖利率", english: "Treasury yield", meaning: "債券市場利率。美債殖利率上升時，成長股常承壓。" },
  ],
  disclaimer: "本頁提供市場資訊與教育內容，不構成個人化投資建議或買賣建議。",
};

export const DEMO_ATTRIBUTION: FundAttributionPayload = {
  fund_name: "示範 ETF（範例資料）",
  benchmark_name: "台灣加權指數",
  as_of: "2026-06-28",
  fund_return_pct: -1.15,
  benchmark_return_pct: -3.64,
  active_return_pct: 2.49,
  explained_return_pct: -1.15,
  residual_pct: 0,
  holdings_count: 4,
  contributors: [{ symbol: "2412", name: "中華電", weight_pct: 6, return_pct: 0.82, contribution_pct: 0.05, direction: "positive" }],
  drags: [
    { symbol: "2454", name: "聯發科", weight_pct: 5.25, return_pct: -9.98, contribution_pct: -0.52, direction: "negative" },
    { symbol: "2330", name: "台積電", weight_pct: 20.5, return_pct: -2.09, contribution_pct: -0.43, direction: "negative" },
  ],
  missing_returns: [],
  all_rows: [],
  source_notes: ["示範資料，僅供展示介面。"],
  automation_policy: [],
  summary_zh_hant: "示範資料：基金當日 −1.15%，加權指數 −3.64%，相對表現 +2.49 個百分點。",
  disclaimer: "本頁提供績效歸因與教育資訊，不構成投資建議。",
};
