import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Cited Market Brief Agent",
    short_name: "Market Brief",
    description:
      "Cited, reviewable morning briefs from public market data with audit-ready evidence.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#161616",
    theme_color: "#242526",
    orientation: "portrait",
    categories: ["finance", "business", "productivity"],
    icons: [
      {
        src: "/icons/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/maskable-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
