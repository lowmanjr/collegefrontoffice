import { createClient } from "@supabase/supabase-js";
import type { MetadataRoute } from "next";

export const revalidate = 86400; // 1 day

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = "https://collegefrontoffice.com";

  // Static pages
  const staticPages: MetadataRoute.Sitemap = [
    { url: base, changeFrequency: "daily", priority: 1.0 },
    { url: `${base}/players`, changeFrequency: "daily", priority: 0.9 },
    { url: `${base}/teams`, changeFrequency: "daily", priority: 0.9 },
    { url: `${base}/recruits`, changeFrequency: "daily", priority: 0.8 },
    { url: `${base}/methodology`, changeFrequency: "monthly", priority: 0.5 },
  ];

  // Dynamic: teams
  const { data: teams } = await supabase.from("teams").select("slug");
  const teamPages: MetadataRoute.Sitemap = (teams ?? []).map((t) => ({
    url: `${base}/teams/${t.slug}`,
    changeFrequency: "daily" as const,
    priority: 0.8,
  }));

  // Dynamic: players (only public, with valuations)
  const { data: players } = await supabase
    .from("players")
    .select("slug")
    .eq("is_public", true)
    .not("cfo_valuation", "is", null)
    .limit(500);
  const playerPages: MetadataRoute.Sitemap = (players ?? []).map((p) => ({
    url: `${base}/players/${p.slug}`,
    changeFrequency: "weekly" as const,
    priority: 0.6,
  }));

  return [...staticPages, ...teamPages, ...playerPages];
}
