"use client";

import { useEffect, useState } from "react";

type TextSize = "normal" | "large" | "xl";

const OPTIONS: { size: TextSize; label: string }[] = [
  { size: "normal", label: "A" },
  { size: "large", label: "A+" },
  { size: "xl", label: "A++" },
];

export default function TextSizeToggle({
  label = "Text size",
  optionTitles = { normal: "Normal text", large: "Large text", xl: "Extra large text" },
}: {
  label?: string;
  optionTitles?: Record<TextSize, string>;
}) {
  const [size, setSize] = useState<TextSize>("normal");

  useEffect(() => {
    const saved = window.localStorage.getItem("cmb-text-size");
    const nextSize = saved === "large" || saved === "xl" ? saved : "normal";
    setSize(nextSize);
    document.documentElement.dataset.textSize = nextSize;
  }, []);

  function choose(nextSize: TextSize) {
    setSize(nextSize);
    window.localStorage.setItem("cmb-text-size", nextSize);
    document.documentElement.dataset.textSize = nextSize;
  }

  return (
    <div
      className="flex rounded-(--radius-ctl) border border-elevated p-0.5"
      role="group"
      aria-label={label}
    >
      {OPTIONS.map((option) => (
        <button
          key={option.size}
          type="button"
          onClick={() => choose(option.size)}
          title={optionTitles[option.size]}
          aria-pressed={size === option.size}
          className={`min-h-7 min-w-8 rounded-(--radius-ctl) px-1.5 font-mono text-[11px] transition-colors ${
            size === option.size
              ? "bg-action text-on-action"
              : "text-neutral-70 hover:bg-card hover:text-neutral-30"
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
