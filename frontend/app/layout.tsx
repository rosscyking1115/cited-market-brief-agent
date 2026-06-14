import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, Inter, Source_Serif_4 } from "next/font/google";
import OnboardingGuide from "@/app/components/OnboardingGuide";
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
  applicationName: "Cited Market Brief",
  title: {
    default: "Cited Market Brief Agent",
    template: "%s · Cited Market Brief Agent",
  },
  description:
    "Cited, reviewable morning briefs from public data. Every claim validated against a stored source span.",
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
    title: "Market Brief",
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
        {children}
        <OnboardingGuide />
        <ServiceWorkerRegister />
      </body>
    </html>
  );
}
