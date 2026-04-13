import Link from "next/link";
import Image from "next/image";
import { Suspense } from "react";
import { supabase } from "@/lib/supabase";
import { formatCurrency, formatCompactCurrency } from "@/lib/utils";
import { BASE_URL } from "@/lib/constants";
import { positionBadgeClass } from "@/lib/ui-helpers";
import PlayerAvatar from "@/components/PlayerAvatar";
import TeamRoster from "@/components/TeamRoster";
import RosterDonut from "@/components/RosterDonut";
import type { PlayerRow } from "@/lib/database.types";

export const revalidate = 900;

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const { data } = await supabase
    .from("teams")
    .select("university_name, conference")
    .eq("slug", slug)
    .single();
  return {
    title: data
      ? `${data.university_name} — ${data.conference} | CFO`
      : "Team Profile | College Front Office",
    description: data
      ? `NIL roster valuation for ${data.university_name} (${data.conference})`
      : "Team NIL roster valuation",
    alternates: {
      canonical: `${BASE_URL}/teams/${slug}`,
    },
  };
}

// ─── types ───────────────────────────────────────────────────────────────────

type Player = Pick<
  PlayerRow,
  "id" | "slug" | "name" | "position" | "class_year" | "star_rating" | "cfo_valuation" | "is_public" | "roster_status" | "headshot_url" | "acquisition_type"
>;

// ─── page ────────────────────────────────────────────────────────────────────

interface PageProps {
  params: Promise<{ slug: string }>;
}

export default async function TeamDashboardPage({ params }: PageProps) {
  const { slug } = await params;

  const { data: team, error } = await supabase
    .from("teams")
    .select("id, university_name, conference, logo_url")
    .eq("slug", slug)
    .single();

  const teamId = team?.id;

  const [playersResp, recruitsResp] = teamId
    ? await Promise.all([
        supabase
          .from("players")
          .select("id, slug, name, position, class_year, star_rating, cfo_valuation, is_public, roster_status, headshot_url, acquisition_type")
          .eq("team_id", teamId)
          .eq("player_tag", "College Athlete")
          .order("cfo_valuation", { ascending: false, nullsFirst: false }),
        supabase
          .from("players")
          .select("id, slug, name, position, class_year, star_rating, cfo_valuation, is_public, roster_status, headshot_url, acquisition_type")
          .eq("team_id", teamId)
          .eq("player_tag", "High School Recruit")
          .eq("hs_grad_year", 2026)
          .not("cfo_valuation", "is", null)
          .order("cfo_valuation", { ascending: false, nullsFirst: false }),
      ])
    : [{ data: [] }, { data: [] }];

  const activeRoster = ((playersResp.data ?? []) as Player[]).filter(
    (p) => !p.roster_status || p.roster_status === "active"
  );
  const recruits = (recruitsResp.data ?? []) as Player[];

  if (error || !team) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
        <div className="text-center">
          <p className="text-6xl font-bold text-slate-700 mb-4">404</p>
          <p className="text-slate-400 mb-6">Team not found.</p>
          <Link href="/players" className="text-blue-400 hover:underline text-sm">
            ← Back to Big Board
          </Link>
        </div>
      </main>
    );
  }

  // Combine active roster + 2026 incoming recruits into one list
  const allRoster = [...activeRoster, ...recruits].sort((a, b) => {
    const aVal = a.cfo_valuation ?? 0;
    const bVal = b.cfo_valuation ?? 0;
    return bVal - aVal;
  });

  const total_valuation = allRoster.reduce(
    (sum, p) => sum + (p.is_public && p.cfo_valuation != null ? p.cfo_valuation : 0),
    0
  );

  // Three-way value split by acquisition type
  const retainedValue = allRoster.reduce(
    (s, p) => s + (p.acquisition_type === "retained" && p.cfo_valuation ? p.cfo_valuation : 0), 0
  );
  const portalValue = allRoster.reduce(
    (s, p) => s + (p.acquisition_type === "portal" && p.cfo_valuation ? p.cfo_valuation : 0), 0
  );
  const recruitValue = allRoster.reduce(
    (s, p) => s + (p.acquisition_type === "recruit" && p.cfo_valuation ? p.cfo_valuation : 0), 0
  );

  return (
    <div className="min-h-screen bg-gray-100">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "SportsTeam",
            name: team.university_name,
            sport: "American Football",
            ...(team.conference ? { memberOf: { "@type": "SportsOrganization", name: team.conference } } : {}),
            url: `https://collegefrontoffice.com/teams/${slug}`,
          }),
        }}
      />

      {/* ── Hero + Donut (unified) ────────────────────────────────────── */}
      <section className="bg-slate-900 text-white px-4 pt-8 pb-20">
        <div className="mx-auto max-w-6xl">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-8">
            {/* Left: Identity */}
            <div className="flex flex-col items-center md:items-start gap-4">
              <div className="flex flex-col sm:flex-row items-center sm:items-center gap-5">
                {team.logo_url && (
                  <Image
                    src={team.logo_url}
                    alt={`${team.university_name} logo`}
                    width={80}
                    height={80}
                    className="h-20 w-20 object-contain shrink-0"
                    priority
                  />
                )}
                <div className="text-center sm:text-left">
                  <h1
                    className="text-4xl sm:text-5xl font-bold uppercase tracking-tight leading-none"
                    style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                  >
                    {team.university_name}
                  </h1>
                  {team.conference && (
                    <span className="mt-2 inline-block rounded px-2.5 py-0.5 text-xs font-semibold uppercase tracking-widest bg-slate-700 text-slate-300">
                      {team.conference}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Right: Donut + Legend */}
            {total_valuation > 0 && (
              <RosterDonut
                retainedValue={retainedValue}
                portalValue={portalValue}
                recruitValue={recruitValue}
                totalValuation={total_valuation}
                variant="dark"
              />
            )}
          </div>
        </div>
      </section>

      {/* ── Roster ───────────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-6xl px-4 -mt-10 relative z-10 pb-16">
        <h2
          className="text-2xl font-bold text-slate-900 uppercase tracking-wide mb-4"
          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
        >
          Active Roster
        </h2>

        <Suspense fallback={<div className="text-center py-8 text-slate-400">Loading roster...</div>}>
        <TeamRoster
          players={allRoster.map((p) => ({
            id: p.id,
            slug: p.slug,
            name: p.name,
            position: p.position,
            cfo_valuation: p.cfo_valuation,
            is_public: p.is_public,
            headshot_url: p.headshot_url,
            acquisition_type: p.acquisition_type ?? "retained",
          }))}
          retainedValue={retainedValue}
          portalValue={portalValue}
          recruitValue={recruitValue}
          totalValuation={total_valuation}
        />
        </Suspense>
      </div>
    </div>
  );
}
