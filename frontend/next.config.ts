import type { NextConfig } from "next";

// The Python backend (FastAPI) owns audio analysis and console I/O.
// In dev and in docker compose, /api/* is proxied to it.
const backend = process.env.WM_BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
  allowedDevOrigins: ["localhost", "127.0.0.1", "*.local", "192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"],
};

export default nextConfig;
