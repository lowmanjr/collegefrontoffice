import { Suspense } from "react";
import { supabase } from "@/lib/supabase";
import type { Metadata } from "next";
import { BASE_URL } from "@/lib/constants";
import PortalBoard from "@/components/PortalBoard";

export const revalidate = 900;

export const metadata: Metadata = {
  title: "Football Transfer Portal Valuations | College Front Office",
  description:
    "Transfer portal acquisitions ranked by estimated NIL value across all 68 Power 4 programs.",
  openGraph: {
    title: "Football Transfer Portal Valuations | College Front Office",
    description:
      "Transfer portal acquisitions ranked by estimated NIL value across all 68 Power 4 programs.",
  },
  alternates: { canonical: `${BASE_URL}/football/portal` },
};

export default async function PortalPage() {
  // Fetch all portal players with team data
  const { data: portalPlayers } = await supabase
    .from("players")
    .select("id, slug, name, position, cfo_valuation, headshot_url, team_id, teams(university_name, logo_url, slug, conference)")
    .eq("acquisition_type", "portal")
    .eq("roster_status", "active")
    .not("cfo_valuation", "is", null)
    .order("cfo_valuation", { ascending: false });

  // Fetch all teams for the team view
  const { data: allTeams } = await supabase
    .from("teams")
    .select("id, university_name, logo_url, slug, conference");

  const players = (portalPlayers ?? []).map((p: any) => ({
    id: p.id as string,
    slug: p.slug as string | null,
    name: p.name as string,
    position: p.position as string | null,
    cfo_valuation: p.cfo_valuation as number,
    headshot_url: p.headshot_url as string | null,
    team_name: (p.teams as any)?.university_name ?? "Unknown",
    team_slug: (p.teams as any)?.slug ?? null,
    team_logo: (p.teams as any)?.logo_url ?? null,
    conference: (p.teams as any)?.conference ?? null,
  }));

  // Build team summaries
  const teamMap = new Map<string, { count: number; value: number }>();
  for (const p of portalPlayers ?? []) {
    const tid = p.team_id as string;
    const existing = teamMap.get(tid) ?? { count: 0, value: 0 };
    existing.count += 1;
    existing.value += (p.cfo_valuation as number) ?? 0;
    teamMap.set(tid, existing);
  }

  const teamSummaries = (allTeams ?? [])
    .map((t: any) => {
      const stats = teamMap.get(t.id) ?? { count: 0, value: 0 };
      return {
        team_name: t.university_name as string,
        team_slug: t.slug as string | null,
        team_logo: t.logo_url as string | null,
        conference: t.conference as string | null,
        portal_count: stats.count,
        portal_value: stats.value,
      };
    })
    .sort((a, b) => b.portal_value - a.portal_value);

  const totalCount = players.length;
  const totalValue = players.reduce((s, p) => s + p.cfo_valuation, 0);

  return (
    <main className="min-h-screen bg-gray-100">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "ItemList",
            name: "Football Transfer Portal Valuations",
            description: "College football transfer portal acquisitions ranked by estimated NIL value.",
            url: `${BASE_URL}/football/portal`,
            numberOfItems: totalCount,
            itemListElement: players.slice(0, 50).map((p, i) => ({
              "@type": "ListItem",
              position: i + 1,
              url: `${BASE_URL}/football/players/${p.slug}`,
              name: p.name,
            })),
          }),
        }}
      />

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="bg-slate-900 text-white px-6 py-6">
        <div className="mx-auto max-w-7xl">
          <h1
            className="text-4xl sm:text-5xl font-bold uppercase tracking-tight leading-none"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Football Transfer Portal Valuations
          </h1>
        </div>
      </div>

      {/* ── Content ────────────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-7xl px-4 py-8">
        <Suspense fallback={<div className="text-center py-8 text-slate-400">Loading portal data...</div>}>
          <PortalBoard
            players={players}
            teamSummaries={teamSummaries}
            totalCount={totalCount}
            totalValue={totalValue}
          />
        </Suspense>
      </div>
    </main>
  );
}
