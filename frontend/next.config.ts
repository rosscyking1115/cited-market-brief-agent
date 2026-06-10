import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next 16: Turbopack is the default build; middleware.ts is now proxy.ts.
  // Phase 2+: enable cacheComponents (PPR default) and tag brief routes by watchlist-run.
  reactStrictMode: true,
};

export default nextConfig;
