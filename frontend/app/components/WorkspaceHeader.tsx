"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { RegionSwitcher, useRegion } from "@/app/components/RegionProvider";
import TextSizeToggle from "@/app/components/TextSizeToggle";
import ThemeToggle from "@/app/components/ThemeToggle";
import { RADAR_COPY, radarLang } from "@/lib/radar-i18n";

export default function WorkspaceHeader({ workspace }: { workspace: "radar" | "brief" }) {
  const pathname = usePathname();
  const { profile } = useRegion();
  const lang = workspace === "brief" ? "en" : radarLang(profile.region);
  const copy = (key: keyof typeof RADAR_COPY) => RADAR_COPY[key][lang];

  return (
    <header className="sticky top-0 z-20 border-b border-hairline bg-bar">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-4 gap-y-2 px-3 py-2 sm:px-6">
        <Link href="/" className="flex min-w-0 items-center gap-2 rounded-(--radius-ctl) focus-visible:outline-offset-4">
          <span className="block h-5 w-1.5 bg-navy-700" aria-hidden />
          <span className="truncate font-serif text-[16px] font-semibold tracking-tight text-neutral-30 sm:text-[17px]">
            {workspace === "brief" ? "Cited Market Brief Agent" : copy("productName")}
          </span>
        </Link>

        <nav aria-label={copy("workspaces")} className="order-3 flex basis-full gap-1 sm:order-none sm:basis-auto">
          <Link
            href={workspace === "radar" ? `/?region=${profile.region.toLowerCase()}` : "/"}
            aria-current={pathname === "/" ? "page" : undefined}
            className={`rounded-(--radius-ctl) px-2.5 py-1.5 text-[12px] font-medium ${pathname === "/" ? "bg-action-soft text-action" : "text-neutral-70 hover:text-neutral-30"}`}
          >
            {copy("radarNav")}
          </Link>
          <Link
            href="/brief"
            aria-current={pathname === "/brief" ? "page" : undefined}
            className={`rounded-(--radius-ctl) px-2.5 py-1.5 text-[12px] font-medium ${pathname === "/brief" ? "bg-action-soft text-action" : "text-neutral-70 hover:text-neutral-30"}`}
          >
            {copy("briefNav")}
          </Link>
        </nav>

        <div className="ml-auto flex min-w-0 items-center gap-2">
          {workspace === "radar" && <RegionSwitcher label={copy("region")} ariaLabel={copy("chooseRegion")} />}
          <ThemeToggle
            lightLabel={copy("lightTheme")}
            darkLabel={copy("darkTheme")}
            switchToLightLabel={copy("switchToLightTheme")}
            switchToDarkLabel={copy("switchToDarkTheme")}
          />
          <TextSizeToggle
            label={copy("textSize")}
            optionTitles={{
              normal: copy("normalText"),
              large: copy("largeText"),
              xl: copy("extraLargeText"),
            }}
          />
        </div>
      </div>
    </header>
  );
}
