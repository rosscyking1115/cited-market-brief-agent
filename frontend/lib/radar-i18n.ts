// Radar localization layer. The /market-radar backend authors all narrative in
// Traditional Chinese (Taiwan-first pilot). For the Korean and English editions
// we keep the backend payload as the source of truth for TW and map localized
// narrative here, so no backend round-trip or loading flicker is needed. If the
// radar's content grows, the longer-term move is a backend `lang` parameter.

import type {
  GlossaryItem,
  MarketId,
  MarketStatus,
  NewsRankKind,
  OvernightRiskItem,
} from "@/lib/api";
import type { UserRegion } from "@/lib/regions";

export type RadarLang = "tw" | "ko" | "en";
// Narrative content exists in ko/en here; tw is read from the API payload.
type NarrativeLang = "ko" | "en";

type RiskGroup = OvernightRiskItem["group"];
export type RadarSection = "clock" | "risk" | "glossary" | "focus" | "dataTime" | "mostRead";

type LocalizedCopy = Record<RadarLang, string>;

export const RADAR_COPY = {
  productName: { tw: "早晨市場雷達", ko: "모닝 마켓 레이더", en: "Morning Market Radar" },
  productDescriptor: { tw: "每日市場雷達 · 有來源依據", ko: "데일리 마켓 레이더 · 출처 기반", en: "Daily market radar · Evidence-backed" },
  radarNav: { tw: "市場雷達", ko: "시장 레이더", en: "Market radar" },
  briefNav: { tw: "公司研究工作區", ko: "기업 리서치 워크스페이스", en: "Company research" },
  region: { tw: "地區", ko: "지역", en: "Region" },
  chooseRegion: { tw: "選擇地區版本", ko: "지역판 선택", en: "Choose region edition" },
  skipMain: { tw: "跳至主要內容", ko: "본문으로 건너뛰기", en: "Skip to main content" },
  workspaces: { tw: "工作區", ko: "작업 공간", en: "Workspaces" },
  lightTheme: { tw: "淺色", ko: "라이트", en: "Light" },
  darkTheme: { tw: "深色", ko: "다크", en: "Dark" },
  switchToLightTheme: { tw: "切換至淺色主題", ko: "라이트 테마로 전환", en: "Switch to light theme" },
  switchToDarkTheme: { tw: "切換至深色主題", ko: "다크 테마로 전환", en: "Switch to dark theme" },
  textSize: { tw: "文字大小", ko: "글자 크기", en: "Text size" },
  normalText: { tw: "一般文字", ko: "기본 글자", en: "Normal text" },
  largeText: { tw: "大文字", ko: "큰 글자", en: "Large text" },
  extraLargeText: { tw: "特大文字", ko: "매우 큰 글자", en: "Extra large text" },
  demoData: { tw: "示範資料", ko: "데모 데이터", en: "Demo data" },
  sourcedData: { tw: "來源資料", ko: "출처 데이터", en: "Sourced data" },
  originalLanguage: { tw: "來源語言原文", ko: "원문", en: "Original-language source" },
  rows: { tw: "則", ko: "건", en: "items" },
  scheduled: { tw: "預定交易時段", ko: "예정 정규장", en: "Scheduled regular session" },
  holidayCaveat: {
    tw: "狀態依一般平日交易時段計算；未納入交易所假日、臨時停市或即時市場狀態。",
    ko: "상태는 일반 평일 정규장 기준입니다. 거래소 휴일, 임시 휴장, 실시간 시장 상태는 반영하지 않습니다.",
    en: "Status follows normal weekday core sessions. It does not account for exchange holidays, exceptional closures or live market state.",
  },
  globalScope: {
    tw: "台灣版另提供台灣匯率與 ETF 歸因；其他版本使用同一組有來源的全球指標。",
    ko: "한국판은 출처가 확인된 글로벌 지표를 사용하며, 완전한 한국 로컬 시장 커버리지를 주장하지 않습니다.",
    en: "This edition localises sourced global indicators; it does not claim complete local-market coverage.",
  },
  notAdvice: {
    tw: "市場資訊與教育內容，不構成投資建議。",
    ko: "시장 정보와 교육 콘텐츠이며 투자 자문이 아닙니다.",
    en: "Market information and educational content, not investment advice.",
  },
} satisfies Record<string, LocalizedCopy>;

export const HERO_COPY: Record<RadarLang, {
  today: string;
  relative: string;
  now: string;
  emptySummary: string;
  detailLink: string;
  setupPrompt: string;
  setupLink: string;
}> = {
  tw: { today: "今日重點 · AI 摘要", relative: "相對表現 · 今日", now: "目前焦點", emptySummary: "今日市場摘要會在新聞與行情回傳後自動生成。", detailLink: "查看歸因明細", setupPrompt: "設定你的基金後，這裡會顯示今日相對加權指數的表現。", setupLink: "前往設定" },
  ko: { today: "오늘의 핵심 · AI 요약", relative: "상대 성과 · 오늘", now: "현재 포커스", emptySummary: "오늘의 시장 요약은 뉴스와 시세가 들어오면 자동 생성됩니다.", detailLink: "기여도 상세 보기", setupPrompt: "펀드를 설정하면 오늘 벤치마크 대비 성과가 여기에 표시됩니다.", setupLink: "설정으로" },
  en: { today: "Today's brief · AI summary", relative: "Relative · today", now: "Now", emptySummary: "Today's market summary is generated once news and prices arrive.", detailLink: "See attribution detail", setupPrompt: "Set up your fund and today's performance versus the benchmark shows here.", setupLink: "Set up" },
};

export const NEWS_UI_COPY: Record<RadarLang, {
  title: string;
  meta: string;
  all: string;
  emptyTitle: string;
  emptyBody: string;
  periods: Record<"1d" | "1w" | "1m", string>;
  sparse: (period: string) => string;
}> = {
  tw: {
    title: "市場新聞",
    meta: "今日最值得閱讀的財經要聞",
    all: "全部",
    emptyTitle: "目前沒有可顯示的市場新聞",
    emptyBody: "等財經來源回傳新聞時，這裡才會出現可點擊標題。",
    periods: { "1d": "今日", "1w": "本週", "1m": "本月" },
    sparse: (period) => `本期單篇熱門文章較少；以上為 AI 整理的${period}重點，個別新聞可參考今日列表。`,
  },
  ko: {
    title: "시장 뉴스",
    meta: "오늘 가장 읽을 만한 시장 뉴스",
    all: "전체",
    emptyTitle: "아직 표시할 시장 뉴스가 없습니다",
    emptyBody: "실제 링크와 출처가 들어오면 이곳에 표시됩니다.",
    periods: { "1d": "오늘", "1w": "이번 주", "1m": "이번 달" },
    sparse: (period) => `이 기간의 개별 인기 기사는 적습니다. 위 ${period} 요약을 참고하고, 개별 기사는 오늘 탭을 확인하세요.`,
  },
  en: {
    title: "Market news",
    meta: "Today's most decision-relevant finance reads",
    all: "All",
    emptyTitle: "No market news to show yet",
    emptyBody: "Linked, source-backed headlines will appear here when the feeds return them.",
    periods: { "1d": "Today", "1w": "This week", "1m": "This month" },
    sparse: (period) => `Not many standalone articles for this window. The ${period} summary covers it, and individual reads are on the Today tab.`,
  },
};

const MARKET_ORDER: Record<UserRegion, MarketId[]> = {
  TW: ["twse", "jpx", "krx", "hkex", "lse", "xetra", "nyse"],
  KR: ["krx", "jpx", "twse", "hkex", "xetra", "lse", "nyse"],
  UK: ["lse", "xetra", "nyse", "jpx", "krx", "twse", "hkex"],
  EU: ["xetra", "lse", "nyse", "jpx", "krx", "twse", "hkex"],
};

const GLOBAL_RISK_SYMBOLS = new Set(["VIX", "USD-BROAD", "WTI", "XAU", "US10Y"]);

export function orderedMarketIds(region: UserRegion): MarketId[] {
  return MARKET_ORDER[region];
}

export function visibleRiskSymbols(region: UserRegion, symbols: string[]): string[] {
  return region === "TW" ? symbols : symbols.filter((symbol) => GLOBAL_RISK_SYMBOLS.has(symbol));
}

type NewsCopySource = {
  title: string;
  title_zh_hant: string;
  title_ko?: string | null;
  summary?: string | null;
  summary_zh?: string | null;
  summary_ko?: string | null;
};

export function localizedNewsCopy(lang: RadarLang, item: NewsCopySource) {
  const title = lang === "tw" ? item.title_zh_hant : lang === "ko" ? item.title_ko : item.title;
  const summary = lang === "tw" ? item.summary_zh : lang === "ko" ? item.summary_ko : item.summary;
  const localizedTitle = title?.trim();
  const localizedSummary = summary?.trim();
  const sourceTitle = item.title.trim();
  const sourceSummary = item.summary?.trim() || null;
  const titleIsOriginalLanguage =
    lang !== "en" && (!localizedTitle || localizedTitle === sourceTitle);
  const summaryIsOriginalLanguage =
    lang !== "en" &&
    Boolean(localizedSummary || sourceSummary) &&
    (!localizedSummary || localizedSummary === sourceSummary);
  return {
    title: localizedTitle || item.title,
    summary: localizedSummary || item.summary || null,
    isOriginalLanguage: titleIsOriginalLanguage || summaryIsOriginalLanguage,
    titleIsOriginalLanguage,
    summaryIsOriginalLanguage,
  };
}

export function radarLang(region: UserRegion): RadarLang {
  if (region === "TW") return "tw";
  if (region === "KR") return "ko";
  return "en";
}

// --- Structural labels (all three languages) ------------------------------

export const MARKET_LABELS: Record<string, Record<RadarLang, string>> = {
  日本: { tw: "日本", ko: "일본", en: "Japan" },
  韓國: { tw: "韓國", ko: "한국", en: "Korea" },
  台灣: { tw: "台灣", ko: "대만", en: "Taiwan" },
  // Backwards-compatible source key; the scheduled market is HKEX only.
  "香港 / A股": { tw: "香港", ko: "홍콩", en: "Hong Kong" },
  歐洲: { tw: "歐洲", ko: "유럽", en: "Europe" },
  美國: { tw: "美國", ko: "미국", en: "United States" },
};

export const MARKET_ID_LABELS: Record<MarketId, Record<RadarLang, string>> = {
  jpx: { tw: "日本", ko: "일본", en: "Japan" },
  krx: { tw: "韓國", ko: "한국", en: "Korea" },
  twse: { tw: "台灣", ko: "대만", en: "Taiwan" },
  hkex: { tw: "香港", ko: "홍콩", en: "Hong Kong" },
  lse: { tw: "倫敦", ko: "런던", en: "London" },
  xetra: { tw: "Xetra", ko: "프랑크푸르트", en: "Xetra" },
  nyse: { tw: "紐約", ko: "뉴욕", en: "New York" },
};

export const CATEGORY_LABELS: Record<string, Record<RadarLang, string>> = {
  市場: { tw: "市場", ko: "시장", en: "Markets" },
  半導體: { tw: "半導體", ko: "반도체", en: "Semiconductors" },
  能源: { tw: "能源", ko: "에너지", en: "Energy" },
  商品: { tw: "商品", ko: "원자재", en: "Commodities" },
  匯率: { tw: "匯率", ko: "환율", en: "FX" },
  利率: { tw: "利率", ko: "금리", en: "Rates" },
  宏觀: { tw: "宏觀", ko: "거시경제", en: "Macro" },
  公司: { tw: "公司", ko: "기업", en: "Companies" },
};

export const STATUS_LABELS: Record<MarketStatus, Record<RadarLang, string>> = {
  open: { tw: "盤中", ko: "개장", en: "Open" },
  lunch: { tw: "午休", ko: "점심 휴장", en: "Lunch" },
  closed: { tw: "已收盤", ko: "마감", en: "Closed" },
  weekend: { tw: "週末", ko: "주말", en: "Weekend" },
  not_open: { tw: "未開盤", ko: "개장 전", en: "Pre-open" },
};

export const GROUP_LABELS: Record<RiskGroup, Record<RadarLang, string>> = {
  futures: { tw: "期貨", ko: "선물", en: "Futures" },
  volatility: { tw: "波動率", ko: "변동성", en: "Volatility" },
  fx: { tw: "匯率", ko: "환율", en: "FX" },
  commodities: { tw: "商品", ko: "원자재", en: "Commodities" },
  rates: { tw: "利率", ko: "금리", en: "Rates" },
};

export const SECTION_LABELS: Record<RadarSection, Record<RadarLang, string>> = {
  clock: { tw: "市場時鐘 · 亞洲到美國", ko: "마켓 클락 · 아시아→미국", en: "Market clock · Asia to US" },
  risk: { tw: "隔夜風險儀表", ko: "오버나이트 리스크", en: "Overnight risk rail" },
  glossary: { tw: "名詞解釋", ko: "용어 설명", en: "Glossary" },
  focus: { tw: "目前焦點", ko: "현재 포커스", en: "Now" },
  dataTime: { tw: "資料時間", ko: "데이터 시간", en: "Data time" },
  mostRead: { tw: "最多瀏覽", ko: "많이 본 기사", en: "Most read" },
};

export const RANK_KIND_LABELS: Record<RadarLang, Record<NewsRankKind, string>> = {
  tw: { most_read: "閱讀最多", most_viewed: "觀看最多", most_covered: "最多報導", trending: "趨勢", latest: "最新" },
  ko: { most_read: "많이 읽음", most_viewed: "많이 봄", most_covered: "최다 보도", trending: "트렌드", latest: "최신" },
  en: { most_read: "Most read", most_viewed: "Most viewed", most_covered: "Most covered", trending: "Trending", latest: "Latest" },
};

// --- Narrative (ko/en; tw uses the API payload) ---------------------------

export const RADAR_HEADLINE: Record<NarrativeLang, string> = {
  ko: "글로벌 시장을 먼저 보고, 아시아 개장을 확인하세요",
  en: "Start with the overnight tape, then the next scheduled session",
};

export const RADAR_SUMMARY: Record<NarrativeLang, [string, string, string]> = {
  ko: [
    "미국·유럽 증시 마감이 오버나이트 분위기를 먼저 결정합니다.",
    "각 시장의 정규장 상태는 해당 거래소의 현지 시간대로 계산합니다.",
    "유가·금·달러·금리는 리스크 심리를 읽는 용도이며, 매매 권유가 아닙니다.",
  ],
  en: [
    "The US and European closes set the overnight tone first.",
    "Each scheduled session is calculated in the exchange's own time zone.",
    "Oil, gold, the dollar and rates gauge risk sentiment. They are not a buy/sell signal.",
  ],
};

export const RADAR_DISCLAIMER: Record<NarrativeLang, string> = {
  ko: "이 페이지는 시장 정보와 교육 콘텐츠를 제공하며, 개인화된 투자 자문이나 매매 권유가 아닙니다.",
  en: "This page provides market information and educational content. It is not personalized investment advice or a buy/sell recommendation.",
};

export const CLOCK_NOTES: Record<MarketId, Record<NarrativeLang, string>> = {
  jpx: {
    ko: "아시아 첫 타자 — 기술주와 환율을 먼저 봅니다.",
    en: "Asia's first session. Watch tech and FX first.",
  },
  krx: {
    ko: "메모리·배터리·수출주 참고.",
    en: "A read on memory, batteries and exporters.",
  },
  twse: {
    ko: "개장 전 대만달러·대만지수 선물·반도체를 확인.",
    en: "Pre-open: check TWD, TAIEX futures and semis.",
  },
  hkex: {
    ko: "홍콩 수요·시장 정책과 홍콩 기술주.",
    en: "Hong Kong demand, market policy and HK tech.",
  },
  xetra: {
    ko: "오후에 유럽 증시와 유로를 이어서 관찰.",
    en: "The afternoon handoff: European equities and the euro.",
  },
  lse: {
    ko: "런던 정규장과 파운드 흐름을 확인합니다.",
    en: "London's core session and the sterling handoff.",
  },
  nyse: {
    ko: "대만 아침에는 전날 마감과 선물을 주로 봅니다.",
    en: "In the Taiwan morning, watch last night's close and futures.",
  },
};

// keyed by overnight-risk symbol
export const RISK_WHY: Record<string, Record<NarrativeLang, string>> = {
  VIX: {
    ko: "헤지·시장 변동성 압력 참고.",
    en: "A gauge of hedging and volatility pressure.",
  },
  "USD/TWD": {
    ko: "대만 전자·수출주 심리에 영향.",
    en: "Drives sentiment in Taiwan tech and exporters.",
  },
  "USD/JPY": {
    ko: "일본 증시·수출주·아시아 환율 참고.",
    en: "A read on Japanese equities, exporters and Asian FX.",
  },
  "USD/CNY": {
    ko: "중국·홍콩 시장 리스크 심리 참고. FRED는 CNY를 제공하며 역외 CNH가 아닙니다.",
    en: "Risk sentiment for China/HK markets. FRED provides CNY, not offshore CNH.",
  },
  "USD-BROAD": {
    ko: "달러 강약은 원자재·아시아 환율·자금 흐름에 영향. FRED 광의 달러지수이며 ICE DXY가 아닙니다.",
    en: "Dollar strength moves commodities, Asian FX and flows. FRED broad dollar index, not ICE DXY.",
  },
  WTI: {
    ko: "유가는 인플레이션·에너지주·리스크 심리에 영향.",
    en: "Oil feeds inflation, energy equities and risk sentiment.",
  },
  XAU: {
    ko: "안전자산·실질금리 심리 참고.",
    en: "A read on safe-haven demand and real rates.",
  },
  US10Y: {
    ko: "금리 변화는 기술주 밸류에이션·달러에 영향.",
    en: "Rate moves drive tech valuations and the dollar.",
  },
};

export const NEWS_WHY: Record<NarrativeLang, { latest: string; coverage: string; readership: string }> = {
  ko: {
    latest: "해당 시간대에 게시된 금융 RSS 최신 뉴스이며, 조회수 순위가 아닙니다.",
    coverage: "해당 시간대 GDELT에서 찾은 시장 관련 뉴스로, 보도량 신호이며 조회수가 아닙니다.",
    readership: "NYT Most Popular API 기준 최다 조회 기사이며, 실제 열독량 데이터입니다.",
  },
  en: {
    latest: "The latest headlines from the finance RSS feeds in this window. Not a readership ranking.",
    coverage: "Market-relevant news GDELT found in this window. A coverage signal, not readership.",
    readership: "Most-viewed on the NYT Most Popular API. Real readership data, not coverage.",
  },
};

// English/Korean concepts (not transliterated Chinese terms)
export const RADAR_GLOSSARY: Record<NarrativeLang, GlossaryItem[]> = {
  ko: [
    { term: "필라델피아 반도체지수", english: "PHLX Semiconductor Index", meaning: "미국 대표 반도체 지수로, AI·칩 업종 분위기를 가늠하는 지표." },
    { term: "VIX", english: "Volatility Index", meaning: "공포·헤지 심리 지표. 수치가 오르면 변동성이 커지는 경향." },
    { term: "국채 수익률", english: "US 10-year yield", meaning: "채권시장 금리. 미 국채 수익률이 오르면 성장·기술주가 압박받는 경향." },
    { term: "선물", english: "Index futures", meaning: "현물 개장 전 참고 가격이며, 공식 개장 결과와 같지 않습니다." },
    { term: "ADR", english: "American Depositary Receipt", meaning: "해외 기업의 미국 상장 증서 — TSMC 등의 오버나이트 참고로 활용." },
  ],
  en: [
    { term: "SOX", english: "PHLX Semiconductor Index", meaning: "The main US semiconductor index, watched as a proxy for AI and chip sentiment." },
    { term: "VIX", english: "Volatility Index", meaning: "A fear/hedging gauge; higher readings usually mean larger expected swings." },
    { term: "Treasury yield", english: "US 10-year yield", meaning: "The bond-market interest rate. Rising yields tend to pressure growth and tech stocks." },
    { term: "Futures", english: "Index futures", meaning: "A pre-open reference price; not the same as the official cash open." },
    { term: "ADR", english: "American Depositary Receipt", meaning: "A foreign company's US-traded receipt, used as an overnight reference for names like TSMC." },
  ],
};

// --- Localizers (tw falls back to the backend-authored payload value) ------

export function localizedHeadline(lang: RadarLang, twValue: string): string {
  return lang === "tw" ? twValue : RADAR_HEADLINE[lang];
}

export function localizedSummary(lang: RadarLang, twValue: string[]): string[] {
  return lang === "tw" ? twValue : RADAR_SUMMARY[lang];
}

export function localizedDisclaimer(lang: RadarLang, twValue: string): string {
  return lang === "tw" ? twValue : RADAR_DISCLAIMER[lang];
}

export function localizedClockNote(lang: RadarLang, marketId: MarketId, twValue: string): string {
  return lang === "tw" ? twValue : CLOCK_NOTES[marketId][lang];
}

export function localizedRiskWhy(lang: RadarLang, symbol: string, twValue: string): string {
  return lang === "tw" ? twValue : RISK_WHY[symbol]?.[lang] ?? "";
}

export function localizedGlossary(lang: RadarLang, twValue: GlossaryItem[]): GlossaryItem[] {
  return lang === "tw" ? twValue : RADAR_GLOSSARY[lang];
}

export function localizedNewsWhy(
  lang: RadarLang,
  rankKind: NewsRankKind,
  twValue: string,
): string | null {
  if (lang === "tw") return twValue || null;
  if (rankKind === "most_read" || rankKind === "most_viewed") return NEWS_WHY[lang].readership;
  if (rankKind === "trending" || rankKind === "most_covered") return NEWS_WHY[lang].coverage;
  if (rankKind === "latest") return NEWS_WHY[lang].latest;
  return null;
}
