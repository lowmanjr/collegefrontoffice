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
      // Updated: /futures redirects now point directly to the new /football/recruits location
      {
        source: "/futures",
        destination: "/football/recruits",
        permanent: true,
      },
      {
        source: "/futures/:path*",
        destination: "/football/recruits/:path*",
        permanent: true,
      },
      // Football URL migration: root football routes → /football/*
      { source: "/players", destination: "/football/players", permanent: true },
      { source: "/players/:path*", destination: "/football/players/:path*", permanent: true },
      { source: "/teams", destination: "/football/teams", permanent: true },
      { source: "/teams/:path*", destination: "/football/teams/:path*", permanent: true },
      { source: "/portal", destination: "/football/portal", permanent: true },
      { source: "/recruits", destination: "/football/recruits", permanent: true },
      { source: "/methodology", destination: "/football/methodology", permanent: true },
    ];
  },
};

export default withBundleAnalyzer(nextConfig);
