"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "cmb-onboarding-v1";

const STEPS = [
  {
    title: "Start with the morning context",
    body: "The top strip shows the latest macro or filing signal. Use it as the quick scan before reading the full brief.",
  },
  {
    title: "Read in your preferred language",
    body: "Original English stays as the audited source. Traditional Chinese and Korean are reading aids, and the A controls make the brief larger.",
  },
  {
    title: "Check the proof",
    body: "Tap any claim code, such as C-000, to jump to the evidence ledger and inspect the source behind the sentence.",
  },
  {
    title: "Use highlights when needed",
    body: "Show highlights marks important phrases only when you want help scanning. It stays off by default for a clean read.",
  },
  {
    title: "Review before exporting",
    body: "Accept, edit, reject, or request a source for each section. Exports stay blocked until the brief is review-ready.",
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
