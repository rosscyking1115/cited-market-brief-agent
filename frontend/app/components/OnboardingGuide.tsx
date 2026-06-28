"use client";

import { useEffect, useState } from "react";
import { useRegion } from "@/app/components/RegionProvider";
import type { UserRegion } from "@/lib/regions";

const STORAGE_KEY = "cmb-onboarding-v1";

const STEPS: Record<UserRegion, { title: string; body: string }[]> = {
  TW: [
    {
      title: "先看市場新聞",
      body: "台灣版會先整理有來源、可點開閱讀的新聞，再接基金歸因與早盤資料。",
    },
    {
      title: "語言已自動選好",
      body: "選台灣後，文章會自動使用繁體中文閱讀輔助；原文仍保留，方便回到最準確的來源。",
    },
    {
      title: "基金歸因可以上傳檔案",
      body: "把 JPM 或基金公司下載的持股 Excel 放進來，就能看哪些持股讓基金贏或輸大盤。",
    },
    {
      title: "只放能真的用的資料",
      body: "未授權或還沒接好的指數行情會先藏起來，避免首頁看起來很多但實際不能判斷。",
    },
  ],
  KR: [
    {
      title: "시장 뉴스를 먼저 봅니다",
      body: "한국판은 링크와 출처가 있는 뉴스, 반도체·배터리, 아시아 개장 흐름을 우선 보여줍니다.",
    },
    {
      title: "언어는 자동으로 바뀝니다",
      body: "한국을 선택하면 브리프가 자동으로 한국어 읽기 모드로 열립니다. 감사용 원문은 그대로 보관됩니다.",
    },
    {
      title: "펀드 분석은 다음 단계입니다",
      body: "첫 파일 업로드 분석은 대만 ETF부터 지원하고, 한국 ETF/펀드 템플릿은 공식 자료원을 확인한 뒤 확장합니다.",
    },
  ],
  UK: [
    {
      title: "Start with the market tape",
      body: "The UK edition frames the page around the London morning: US close, sterling, gilts, Europe and macro context.",
    },
    {
      title: "No translation click needed",
      body: "English is the source language here, so the audited brief opens directly without a separate translation step.",
    },
    {
      title: "Fund attribution comes by region",
      body: "The Taiwan upload workflow is the pilot. UK fund/ETF attribution comes after we confirm official holdings and benchmark sources.",
    },
  ],
  EU: [
    {
      title: "Start with the European open",
      body: "The Europe edition frames the page around US close, euro, Bunds, STOXX sectors, energy and macro context.",
    },
    {
      title: "No translation click needed",
      body: "English is the source language here, so the audited brief opens directly without a separate translation step.",
    },
    {
      title: "Fund attribution comes by region",
      body: "The Taiwan upload workflow is the pilot. Europe fund/ETF attribution comes after we confirm official holdings and benchmark sources.",
    },
  ],
};

const GUIDE_UI: Record<UserRegion, { guide: string; skip: string; next: string; done: string }> = {
  TW: { guide: "快速導覽", skip: "略過", next: "下一步", done: "完成" },
  KR: { guide: "빠른 안내", skip: "건너뛰기", next: "다음", done: "완료" },
  UK: { guide: "Quick guide", skip: "Skip", next: "Next", done: "Done" },
  EU: { guide: "Quick guide", skip: "Skip", next: "Next", done: "Done" },
};

export default function OnboardingGuide() {
  const { needsChoice, profile, ready } = useRegion();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const steps = STEPS[profile.region];
  const ui = GUIDE_UI[profile.region];

  useEffect(() => {
    if (!ready || needsChoice) return;
    if (window.localStorage.getItem(STORAGE_KEY) !== "done") {
      setStep(0);
      setOpen(true);
    }
  }, [needsChoice, ready]);

  function close() {
    window.localStorage.setItem(STORAGE_KEY, "done");
    setOpen(false);
  }

  if (!open || !ready || needsChoice) return null;

  const current = steps[step];
  const last = step === steps.length - 1;

  return (
    <div className="fixed inset-0 z-50 flex items-end bg-black/55 px-3 py-4 sm:items-center sm:justify-center">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboarding-title"
        className="w-full max-w-md rounded-(--radius-modal) border border-elevated bg-card p-4 shadow-2xl sm:p-5"
      >
        <div className="flex items-center justify-between gap-3">
          <p className="th-label">
            {ui.guide} {step + 1}/{steps.length}
          </p>
          <button
            type="button"
            onClick={close}
            className="rounded-(--radius-ctl) border border-elevated px-2 py-1 text-[12px] text-neutral-70 transition-[border-color,box-shadow] hover:border-action hover:text-neutral-30 hover:shadow-sm"
          >
            {ui.skip}
          </button>
        </div>

        <h2 id="onboarding-title" className="mt-3 font-serif text-xl font-semibold leading-tight text-neutral-30">
          {current.title}
        </h2>
        <p className="reader-body mt-3 text-[14px] leading-relaxed text-neutral-50">
          {current.body}
        </p>

        <div className="mt-5 flex items-center justify-between gap-3">
          <div className="flex gap-1.5">
            {steps.map((item, index) => (
              <span
                key={item.title}
                className={`h-1.5 w-6 rounded-full ${index <= step ? "bg-action" : "bg-elevated"}`}
                aria-hidden
              />
            ))}
          </div>

          <button
            type="button"
            onClick={() => (last ? close() : setStep((currentStep) => currentStep + 1))}
            className="min-h-10 rounded-(--radius-ctl) bg-action px-4 py-2 text-[14px] font-semibold text-white transition-[background-color,box-shadow,transform] hover:bg-action-hover hover:shadow-md active:translate-y-px"
          >
            {last ? ui.done : ui.next}
          </button>
        </div>
      </section>
    </div>
  );
}
