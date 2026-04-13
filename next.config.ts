import bundleAnalyzer from "@next/bundle-analyzer";
import type { NextConfig } from "next";

const withBundleAnalyzer = bundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

const nextConfig: NextConfig = {
  images: {
    unoptimized: true,
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**",
      },
    ],
  },
  async redirects() {
    return [
      {
        source: "/futures",
        destination: "/recruits",
        permanent: true,
      },
      {
        source: "/futures/:path*",
        destination: "/recruits/:path*",
        permanent: true,
      },
    ];
  },
};

export default withBundleAnalyzer(nextConfig);
