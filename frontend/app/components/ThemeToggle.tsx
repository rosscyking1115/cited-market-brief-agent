"use client";

import { useEffect, useState } from "react";

type Theme = "dark" | "light";

export default function ThemeToggle({
  lightLabel = "Light",
  darkLabel = "Dark",
  switchToLightLabel = "Switch to light theme",
  switchToDarkLabel = "Switch to dark theme",
}: {
  lightLabel?: string;
  darkLabel?: string;
  switchToLightLabel?: string;
  switchToDarkLabel?: string;
}) {
  // Default light to match the pre-paint script in layout.tsx (avoids a flash).
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const saved = window.localStorage.getItem("cmb-theme");
    const nextTheme = saved === "dark" ? "dark" : "light";
    setTheme(nextTheme);
    document.documentElement.dataset.theme = nextTheme;
  }, []);

  function toggleTheme() {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    window.localStorage.setItem("cmb-theme", nextTheme);
    document.documentElement.dataset.theme = nextTheme;
  }

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="rounded-(--radius-ctl) border border-elevated px-2.5 py-1 font-mono text-[11px] text-neutral-70 transition-colors hover:border-action hover:text-neutral-30"
      title={theme === "dark" ? switchToLightLabel : switchToDarkLabel}
    >
      {theme === "dark" ? lightLabel : darkLabel}
    </button>
  );
}
