import type { NextConfig } from "next";

// The Python backend (FastAPI) owns audio analysis and console I/O.
// In dev and in docker compose, /api/* is proxied to it.
const backend = process.env.WM_BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
  // Phones on the LAN (mic needs HTTPS: npm run dev:https). Next matches hostnames
  // with "*" per dot segment, CIDR like "192.168.0.0/16" is NOT supported.
  allowedDevOrigins: ["127.0.0.1", "*.local", "192.168.*.*", "10.*.*.*", "172.*.*.*"],
};

export default nextConfig;
