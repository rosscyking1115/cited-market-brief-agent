"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
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
      body: "有快取翻譯時會顯示繁體中文閱讀輔助；否則清楚標示來源語言原文，並保留原始連結。",
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
      body: "캐시된 번역이 있으면 한국어로 표시하고, 없으면 원문임을 명확히 표시합니다. 기업 브리프는 별도 영어 감사 워크스페이스입니다.",
    },
    {
      title: "펀드 분석은 다음 단계입니다",
      body: "첫 파일 업로드 분석은 대만 ETF부터 지원하고, 한국 ETF/펀드 템플릿은 공식 자료원을 확인한 뒤 확장합니다.",
    },
  ],
  UK: [
    {
      title: "Start with the market tape",
      body: "The UK edition puts London's scheduled core session first and localises the sourced global indicators already available.",
    },
    {
      title: "No translation click needed",
      body: "This radar does not claim complete UK price, sterling or gilt coverage. The audited company brief lives in its own workspace.",
    },
    {
      title: "Fund attribution comes by region",
      body: "The Taiwan upload workflow is the pilot. UK fund/ETF attribution comes after we confirm official holdings and benchmark sources.",
    },
  ],
  EU: [
    {
      title: "Start with the European open",
      body: "The Europe edition puts Xetra's scheduled core session first and localises the sourced global indicators already available.",
    },
    {
      title: "No translation click needed",
      body: "This radar does not claim complete euro-area price, euro or Bund coverage. The audited company brief lives in its own workspace.",
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
  const pathname = usePathname();
  const { needsChoice, profile, ready } = useRegion();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const dialogRef = useRef<HTMLDialogElement>(null);
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

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const shouldOpen = pathname === "/" && open && ready && !needsChoice;
    if (shouldOpen && !dialog.open) dialog.showModal();
    if (!shouldOpen && dialog.open) dialog.close();
  }, [needsChoice, open, pathname, ready]);

  const current = steps[step];
  const last = step === steps.length - 1;

  return (
    <dialog
        ref={dialogRef}
        onCancel={close}
        aria-labelledby="onboarding-title"
        className="m-auto w-[calc(100%-1.5rem)] max-w-md rounded-(--radius-modal) border border-elevated bg-card p-4 text-neutral-30 shadow-2xl backdrop:bg-black/55 sm:p-5"
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
            className="min-h-10 rounded-(--radius-ctl) bg-action px-4 py-2 text-[14px] font-semibold text-on-action transition-[background-color,box-shadow,transform] hover:bg-action-hover hover:shadow-md active:translate-y-px"
          >
            {last ? ui.done : ui.next}
          </button>
        </div>
    </dialog>
  );
}
