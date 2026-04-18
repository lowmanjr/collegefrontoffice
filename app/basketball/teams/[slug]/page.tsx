import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { BASE_URL } from "@/lib/constants";
import RosterDonut from "@/components/RosterDonut";
import BasketballTeamRoster from "@/components/BasketballTeamRoster";

export const revalidate = 900;

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const { data } = await supabase
    .from("basketball_teams")
    .select("university_name, conference")
    .eq("slug", slug)
    .single();
  return {
    title: data
      ? `${data.university_name} Basketball — ${data.conference} | CFO`
      : "Team Profile | College Front Office",
    description: data
      ? `Basketball NIL roster valuation for ${data.university_name} (${data.conference})`
      : "Team basketball NIL roster valuation",
    alternates: { canonical: `${BASE_URL}/basketball/teams/${slug}` },
  };
}

interface PageProps {
  params: Promise<{ slug: string }>;
}

export default async function BasketballTeamPage({ params }: PageProps) {
  const { slug } = await params;

  const { data: team, error } = await supabase
    .from("basketball_teams")
    .select("id, university_name, conference, logo_url")
    .eq("slug", slug)
    .single();

  if (error || !team) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
        <div className="text-center">
          <p className="text-6xl font-bold text-slate-700 mb-4">404</p>
          <p className="text-slate-400 mb-6">Team not found.</p>
          <Link href="/basketball/teams" className="text-blue-400 hover:underline text-sm">
            ← Back to Teams
          </Link>
        </div>
      </main>
    );
  }

  const { data: playersRaw } = await supabase
    .from("basketball_players")
    .select(
      "id, slug, name, position, class_year, cfo_valuation, is_public, roster_status, headshot_url, acquisition_type, ppg, role_tier"
    )
    .eq("team_id", team.id)
    .eq("roster_status", "active")
    .order("cfo_valuation", { ascending: false, nullsFirst: false });

  const roster = (playersRaw ?? []);

  const total_valuation = roster.reduce(
    (sum, p) => sum + (p.is_public && p.cfo_valuation != null ? p.cfo_valuation : 0),
    0
  );

  const retainedValue = roster.reduce(
    (s, p) => s + ((p.acquisition_type ?? "retained") === "retained" && p.cfo_valuation ? p.cfo_valuation : 0), 0
  );
  const portalValue = roster.reduce(
    (s, p) => s + (p.acquisition_type === "portal" && p.cfo_valuation ? p.cfo_valuation : 0), 0
  );
  const recruitValue = roster.reduce(
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
            sport: "Basketball",
            ...(team.conference
              ? { memberOf: { "@type": "SportsOrganization", name: team.conference } }
              : {}),
            url: `${BASE_URL}/basketball/teams/${slug}`,
          }),
        }}
      />

      {/* ── Hero + Donut ────────────────────────────────────────────────── */}
      <section className="bg-slate-900 text-white px-4 pt-8 pb-20">
        <div className="mx-auto max-w-6xl">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-8">
            <div className="flex flex-col items-center md:items-start gap-4">
              <div className="flex flex-col sm:flex-row items-center sm:items-center gap-5">
                {team.logo_url && (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={team.logo_url}
                    alt={`${team.university_name} logo`}
                    width={80}
                    height={80}
                    className="h-20 w-20 object-contain shrink-0"
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

            {total_valuation > 0 && (
              <RosterDonut
                retainedValue={retainedValue ?? 0}
                portalValue={portalValue ?? 0}
                recruitValue={recruitValue ?? 0}
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

        <BasketballTeamRoster
          players={roster.map((p) => ({
            id: p.id,
            slug: p.slug,
            name: p.name,
            position: p.position,
            cfo_valuation: p.cfo_valuation,
            is_public: p.is_public,
            headshot_url: p.headshot_url,
            acquisition_type: p.acquisition_type ?? "retained",
            ppg: p.ppg,
            role_tier: p.role_tier,
          }))}
        />
      </div>
    </div>
  );
}
