import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, Inter, Source_Serif_4 } from "next/font/google";
import OnboardingGuide from "@/app/components/OnboardingGuide";
import { RegionProvider } from "@/app/components/RegionProvider";
import ServiceWorkerRegister from "@/app/components/ServiceWorkerRegister";
import "./globals.css";

// Self-hosted via next/font (perf budget: fonts ≤100KB woff2, display swap)
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-source-serif",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  applicationName: "Morning Market Radar",
  title: {
    default: "Morning Market Radar",
    template: "%s · Morning Market Radar",
  },
  description:
    "A morning market radar from public data: what moved overnight, what opens next in Asia, and the headlines that matter — plus an evidence-backed company brief where every claim is validated against a stored source span.",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" }],
  },
  appleWebApp: {
    capable: true,
    title: "Market Radar",
    statusBarStyle: "black-translucent",
  },
  formatDetection: {
    telephone: false,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#242526",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${sourceSerif.variable} ${plexMono.variable}`}
    >
      <body>
        {/* Apply saved theme / text-size / region before first paint to avoid a
            dark→light (and region/text-size) flash on load. */}
        <script
          dangerouslySetInnerHTML={{
            __html:
              "(function(){try{var d=document.documentElement;" +
              "var t=localStorage.getItem('cmb-theme');d.dataset.theme=t==='dark'?'dark':'light';" +
              "var s=localStorage.getItem('cmb-text-size');if(s==='large'||s==='xl')d.dataset.textSize=s;" +
              "var r=localStorage.getItem('cmb-region-v1');if(r)d.dataset.region=String(r).toLowerCase();" +
              "}catch(e){}})();",
          }}
        />
        <RegionProvider>
          {children}
          <OnboardingGuide />
        </RegionProvider>
        <ServiceWorkerRegister />
      </body>
    </html>
  );
}
