import { createClient } from "@supabase/supabase-js";
import type { MetadataRoute } from "next";
import { BASE_URL } from "@/lib/constants";

export const revalidate = 86400; // 1 day

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = BASE_URL;

  // Static pages
  const staticPages: MetadataRoute.Sitemap = [
    { url: base, changeFrequency: "daily", priority: 1.0, lastModified: new Date() },
    { url: `${base}/players`, changeFrequency: "daily", priority: 0.9, lastModified: new Date() },
    { url: `${base}/teams`, changeFrequency: "daily", priority: 0.9, lastModified: new Date() },
    { url: `${base}/recruits`, changeFrequency: "daily", priority: 0.8, lastModified: new Date() },
    { url: `${base}/methodology`, changeFrequency: "monthly", priority: 0.5 },
  ];

  // Dynamic: teams
  const { data: teams } = await supabase.from("teams").select("slug");
  const teamPages: MetadataRoute.Sitemap = (teams ?? []).map((t) => ({
    url: `${base}/teams/${t.slug}`,
    changeFrequency: "daily" as const,
    priority: 0.8,
    lastModified: new Date(),
  }));

  // Dynamic: ALL public players with slugs (paginated)
  const allPlayers: { slug: string }[] = [];
  const pageSize = 1000;
  let offset = 0;
  while (true) {
    const { data } = await supabase
      .from("players")
      .select("slug")
      .eq("is_public", true)
      .not("slug", "is", null)
      .range(offset, offset + pageSize - 1);
    const batch = data ?? [];
    allPlayers.push(...batch);
    if (batch.length < pageSize) break;
    offset += pageSize;
  }

  const playerPages: MetadataRoute.Sitemap = allPlayers.map((p) => ({
    url: `${base}/players/${p.slug}`,
    changeFrequency: "weekly" as const,
    priority: 0.6,
    lastModified: new Date(),
  }));

  return [...staticPages, ...teamPages, ...playerPages];
}
