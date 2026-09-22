import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  typescript: { ignoreBuildErrors: true },
  images: {
    remotePatterns: [
      { protocol: "https" as const, hostname: "cdn.shopify.com" },
      { protocol: "https" as const, hostname: "**.myshopify.com" },
    ],
  },
};

export default nextConfig;
