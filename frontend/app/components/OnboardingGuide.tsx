"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "cmb-onboarding-v1";

const STEPS = [
  {
    title: "先看 3 句話早盤",
    body: "最上方會用台北時間整理昨晚全球市場、今早亞洲開盤、以及今天先觀察什麼。",
  },
  {
    title: "跟著全球市場時鐘",
    body: "日本、韓國先開，再到台灣、香港/A股、歐洲、美國。狀態會顯示未開盤、盤中、午休或已收盤。",
  },
  {
    title: "指數先看中文名稱",
    body: "標普500、費半、日經225、KOSPI、加權指數都會保留英文代碼，但先用中文說明它代表什麼。",
  },
  {
    title: "看不懂就打開小字典",
    body: "殖利率、VIX、期貨、ADR 這類詞會用一兩句話解釋，目標是不用另外查。",
  },
  {
    title: "需要時再看證據",
    body: "下方仍保留原文與來源證據。任何重要句子都應該能回到資料來源，不只是一段 AI 摘要。",
  },
] as const;

export default function OnboardingGuide() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (window.localStorage.getItem(STORAGE_KEY) !== "done") {
      setOpen(true);
    }
  }, []);

  function close() {
    window.localStorage.setItem(STORAGE_KEY, "done");
    setOpen(false);
  }

  if (!open) return null;

  const current = STEPS[step];
  const last = step === STEPS.length - 1;

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
            Quick guide {step + 1}/{STEPS.length}
          </p>
          <button
            type="button"
            onClick={close}
            className="rounded-(--radius-ctl) border border-elevated px-2 py-1 text-[12px] text-neutral-70 hover:border-action hover:text-neutral-30"
          >
            Skip
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
            {STEPS.map((item, index) => (
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
            className="min-h-10 rounded-(--radius-ctl) bg-action px-4 py-2 text-[14px] font-semibold text-white hover:bg-action-hover"
          >
            {last ? "Done" : "Next"}
          </button>
        </div>
      </section>
    </div>
  );
}
