"use client";

import FundHoldingsParser from "@/app/components/FundHoldingsParser";
import SectorAttributionPanel from "@/app/components/SectorAttributionPanel";
import { useRegion } from "@/app/components/RegionProvider";
import type { FundAttributionPayload, FundAttributionPlanPayload } from "@/lib/api";
import type { UserRegion } from "@/lib/regions";

const DEMO_PLAN: FundAttributionPlanPayload = {
  title: "ETF / Fund vs Benchmark Attribution",
  target_use_case: "每天收盤後回答：基金和大盤表現差在哪裡，哪些持股造成差異。",
  first_region: "Taiwan",
  daily_trigger: "台股收盤後，等 TWSE/JPM 資料更新再跑。",
  required_inputs: [
    "ETF 持股、權重與持股日期",
    "ETF 當日報酬率或淨值/收盤價",
    "台灣加權指數當日報酬率",
    "每個持股的當日報酬率",
  ],
  first_supported_workflow: [
    "先讓使用者上傳 JPM 官網下載的持股檔",
    "系統抓 TWSE 收盤價並計算每檔持股報酬",
    "用權重 x 報酬計算貢獻",
    "輸出贏/輸大盤原因、最大貢獻、最大拖累、無法解釋殘差",
  ],
  automation_policy: [
    {
      label: "JPM ETF holdings file",
      status: "manual_first",
      note: "先支援上傳；自動下載前需確認條款。",
    },
    {
      label: "TWSE after-close prices",
      status: "allowed",
      note: "每日收盤後使用官方公開資料。",
    },
  ],
  disclaimer: "本頁提供績效歸因與教育資訊，不構成個人化投資建議或買賣建議。",
};

const COPY: Record<
  UserRegion,
  {
    eyebrow: string;
    title: string;
    pilotTitle: string;
    pilotBody: string;
    firstMarket: string;
    inputs: string;
    workflow: string;
    policy: string;
  }
> = {
  TW: {
    eyebrow: "核心功能 · ETF 歸因分析",
    title: "每天收盤後：基金為什麼贏/輸台灣加權指數？",
    pilotTitle: "",
    pilotBody: "",
    firstMarket: "第一版市場",
    inputs: "需要的資料",
    workflow: "第一版流程",
    policy: "自動化政策",
  },
  KR: {
    eyebrow: "다음 단계 · 펀드 기여도 분석",
    title: "장 마감 후: 펀드가 벤치마크를 이기거나 진 이유",
    pilotTitle: "한국 ETF/펀드 버전은 다음 단계입니다",
    pilotBody:
      "현재 자동 계산은 대만 ETF 업로드를 먼저 검증 중입니다. 한국판은 공식 보유 종목, 가격, 벤치마크 자료원을 확인한 뒤 같은 구조로 확장합니다.",
    firstMarket: "첫 지원 시장",
    inputs: "필요한 데이터",
    workflow: "지원 예정 흐름",
    policy: "자동화 정책",
  },
  UK: {
    eyebrow: "Next core feature · Fund attribution",
    title: "After the close: why did a fund beat or lag its benchmark?",
    pilotTitle: "UK fund attribution is queued after the Taiwan pilot",
    pilotBody:
      "The upload workflow is proven first with the JPM Taiwan ETF. UK OEIC/ETF support comes after we confirm official holdings files, benchmark data, and redistribution rules.",
    firstMarket: "First supported market",
    inputs: "Required data",
    workflow: "Planned workflow",
    policy: "Automation policy",
  },
  EU: {
    eyebrow: "Next core feature · Fund attribution",
    title: "After the close: why did a fund beat or lag its benchmark?",
    pilotTitle: "Europe fund attribution is queued after the Taiwan pilot",
    pilotBody:
      "The upload workflow is proven first with the JPM Taiwan ETF. EU ETF/fund support comes after we confirm official holdings files, benchmark data, and redistribution rules.",
    firstMarket: "First supported market",
    inputs: "Required data",
    workflow: "Planned workflow",
    policy: "Automation policy",
  },
};

export default function FundAttributionPanel({
  plan,
  latest,
}: {
  plan: FundAttributionPlanPayload | null;
  latest: FundAttributionPayload | null;
}) {
  const { profile } = useRegion();
  const copy = COPY[profile.region];
  const isTaiwan = profile.region === "TW";

  // Taiwan: the fund + sector tools are self-contained sections (no wrapper card).
  if (isTaiwan) {
    return (
      <>
        <FundHoldingsParser initialResult={latest} />
        <SectorAttributionPanel />
      </>
    );
  }

  // Other editions: the pilot card (fund attribution queued after Taiwan).
  return (
    <section className="overflow-hidden rounded-(--radius-card) border border-hairline bg-card">
      <div className="border-b border-hairline px-4 py-4 sm:px-5">
        <p className="th-label">{copy.eyebrow}</p>
        <div className="mt-2 grid gap-3 lg:grid-cols-[minmax(0,1fr)_320px] lg:items-start">
          <div>
            <h2 className="font-serif text-xl font-semibold leading-tight text-neutral-30 sm:text-2xl">
              {copy.title}
            </h2>
            <p className="reader-body mt-2 max-w-3xl text-neutral-70">{copy.pilotBody}</p>
          </div>
          <div className="rounded-(--radius-ctl) border border-elevated bg-page/60 px-3 py-2">
            <p className="th-label">{copy.firstMarket}</p>
            <p className="reader-body mt-1 font-semibold text-neutral-40">{profile.label}</p>
            <p className="reader-meta mt-1 text-neutral-90">{copy.pilotTitle}</p>
          </div>
        </div>
      </div>

      <div className="border-t border-hairline px-4 py-4 sm:px-5">
        <div className="rounded-(--radius-ctl) border border-hairline bg-page/50 px-4 py-4">
          <p className="reader-body font-semibold text-neutral-40">{copy.pilotTitle}</p>
          <p className="reader-meta mt-2 max-w-3xl text-neutral-90">{copy.pilotBody}</p>
        </div>
      </div>
    </section>
  );
}
