import type { NextConfig } from "next";

// CSP note (docs/SECURITY.md): 'unsafe-inline' for script-src is required by the
// Next.js runtime without nonce plumbing; the Phase 5 follow-up moves to
// nonce-based CSP via proxy.ts (Next 16's middleware) before external launch.
const isDev = process.env.NODE_ENV !== "production";
const apiConnectSource = process.env.NEXT_PUBLIC_API_URL ? ` ${process.env.NEXT_PUBLIC_API_URL}` : "";

const securityHeaders = [
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'",
      `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data:",
      "font-src 'self'",
      "manifest-src 'self'",
      "worker-src 'self'",
      `connect-src 'self'${apiConnectSource}${isDev ? " http://localhost:8000" : ""}`,
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join("; "),
  },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  // Next 16: Turbopack is the default build; middleware.ts is now proxy.ts.
  // Phase 2+: enable cacheComponents (PPR default) and tag brief routes by watchlist-run.
  reactStrictMode: true,
  async headers() {
    return [{ source: "/(.*)", headers: securityHeaders }];
  },
};

export default nextConfig;
