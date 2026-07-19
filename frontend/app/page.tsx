import FundAttributionPanel from "@/app/components/FundAttributionPanel";
import MorningMarketDashboard from "@/app/components/MorningMarketDashboard";
import RadarDataStatus from "@/app/components/RadarDataStatus";
import RadarFooter from "@/app/components/RadarFooter";
import { ShowOnTaiwan } from "@/app/components/RegionGate";
import TodayHero from "@/app/components/TodayHero";
import WorkspaceHeader from "@/app/components/WorkspaceHeader";
import { getLatestFundAttribution, getMorningRadar } from "@/lib/api";
import { DEMO_ATTRIBUTION, DEMO_RADAR } from "@/lib/demo-data";

export const dynamic = "force-dynamic";

const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "1";

export default async function RadarPage() {
  const liveRadar = DEMO_MODE ? null : await getMorningRadar();
  const radar = liveRadar ?? DEMO_RADAR;
  const latestAttribution = DEMO_MODE ? null : await getLatestFundAttribution();
  const attribution = latestAttribution?.result ?? (DEMO_MODE ? DEMO_ATTRIBUTION : null);

  return (
    <div className="min-h-screen">
      <WorkspaceHeader workspace="radar" />
      <main id="main-content" className="mx-auto max-w-7xl space-y-4 px-3 py-4 sm:space-y-5 sm:px-6 sm:py-6">
        <RadarDataStatus isDemo={!liveRadar} />
        <TodayHero radar={radar} attribution={attribution} />
        <MorningMarketDashboard radar={radar} />

        <ShowOnTaiwan>
          <div id="fund" className="scroll-mt-20">
            <FundAttributionPanel latest={attribution} />
          </div>
        </ShowOnTaiwan>

        <RadarFooter />
      </main>
    </div>
  );
}
