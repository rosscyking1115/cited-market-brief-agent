// Radar localization layer. The /market-radar backend authors all narrative in
// Traditional Chinese (Taiwan-first pilot). For the Korean and English editions
// we keep the backend payload as the source of truth for TW and map localized
// narrative here, so no backend round-trip or loading flicker is needed. If the
// radar's content grows, the longer-term move is a backend `lang` parameter.

import type {
  GlossaryItem,
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
  "香港 / A股": { tw: "香港 / A股", ko: "홍콩 / 중국 A", en: "Hong Kong / China A" },
  歐洲: { tw: "歐洲", ko: "유럽", en: "Europe" },
  美國: { tw: "美國", ko: "미국", en: "United States" },
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
  en: "Read the global tape first, then the Asia open",
};

export const RADAR_SUMMARY: Record<NarrativeLang, [string, string, string]> = {
  ko: [
    "미국·유럽 증시 마감이 오버나이트 분위기를 먼저 결정합니다.",
    "08:00 일본·한국을 먼저 보고, 09:00 대만으로 이어집니다(타이베이 기준).",
    "유가·금·달러·금리는 리스크 심리를 읽는 용도이며, 매매 권유가 아닙니다.",
  ],
  en: [
    "The US and European closes set the overnight tone first.",
    "Watch Japan and Korea from 08:00, then Taiwan at 09:00 (Taipei time).",
    "Oil, gold, the dollar and rates gauge risk sentiment — not a buy/sell signal.",
  ],
};

export const RADAR_DISCLAIMER: Record<NarrativeLang, string> = {
  ko: "이 페이지는 시장 정보와 교육 콘텐츠를 제공하며, 개인화된 투자 자문이나 매매 권유가 아닙니다.",
  en: "This page provides market information and educational content. It is not personalized investment advice or a buy/sell recommendation.",
};

// keyed by the canonical (Chinese) market string from the payload
export const CLOCK_NOTES: Record<string, Record<NarrativeLang, string>> = {
  日本: {
    ko: "아시아 첫 타자 — 기술주와 환율을 먼저 봅니다.",
    en: "Asia's first session — watch tech and FX first.",
  },
  韓國: {
    ko: "메모리·배터리·수출주 참고.",
    en: "A read on memory, batteries and exporters.",
  },
  台灣: {
    ko: "개장 전 대만달러·대만지수 선물·반도체를 확인.",
    en: "Pre-open: check TWD, TAIEX futures and semis.",
  },
  "香港 / A股": {
    ko: "중국 수요·정책과 홍콩 기술주.",
    en: "China demand and policy, plus HK tech.",
  },
  歐洲: {
    ko: "오후에 유럽 증시와 유로를 이어서 관찰.",
    en: "The afternoon handoff — European equities and the euro.",
  },
  美國: {
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
    latest: "해당 시간대에 게시된 BBC RSS 최신 뉴스이며, 조회수 순위가 아닙니다.",
    coverage: "해당 시간대 GDELT에서 찾은 시장 관련 뉴스로, 트렌드/보도량 신호이며 조회수가 아닙니다.",
    readership: "NYT Most Popular API 기준 최근 1일 최다 조회 기사 — 실제 열독량 데이터입니다.",
  },
  en: {
    latest: "Latest BBC RSS headlines published in this window — not a readership ranking.",
    coverage: "Market-relevant news GDELT found in this window — a trend/coverage signal, not readership.",
    readership: "Genuinely most-viewed over the last day via the NYT Most Popular API — real readership data.",
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
    { term: "SOX", english: "PHLX Semiconductor Index", meaning: "A leading US semiconductor index, watched as a proxy for AI/chip sentiment." },
    { term: "VIX", english: "Volatility Index", meaning: "A fear/hedging gauge; higher readings usually mean larger expected swings." },
    { term: "Treasury yield", english: "US 10-year yield", meaning: "The bond-market interest rate. Rising yields tend to pressure growth and tech stocks." },
    { term: "Futures", english: "Index futures", meaning: "A pre-open reference price; not the same as the official cash open." },
    { term: "ADR", english: "American Depositary Receipt", meaning: "A foreign company's US-traded receipt — an overnight reference for names like TSMC." },
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

export function localizedClockNote(lang: RadarLang, market: string, twValue: string): string {
  return lang === "tw" ? twValue : CLOCK_NOTES[market]?.[lang] ?? twValue;
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
