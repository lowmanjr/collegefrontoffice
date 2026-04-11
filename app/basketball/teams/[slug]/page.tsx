import Link from "next/link";
import Image from "next/image";
import { supabase } from "@/lib/supabase";
import { formatCurrency, formatCompactCurrency } from "@/lib/utils";
import { BASE_URL } from "@/lib/constants";
import { basketballPositionBadgeClass, roleTierBadgeClass } from "@/lib/ui-helpers";
import PlayerAvatar from "@/components/PlayerAvatar";

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
      "id, slug, name, position, role_tier, class_year, cfo_valuation, is_public, roster_status, headshot_url, usage_rate, ppg, rpg, apg"
    )
    .eq("team_id", team.id)
    .eq("roster_status", "active")
    .order("cfo_valuation", { ascending: false, nullsFirst: false });

  const roster = (playersRaw ?? []);

  const total_valuation = roster.reduce(
    (sum, p) => sum + (p.is_public && p.cfo_valuation != null ? p.cfo_valuation : 0),
    0
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

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="bg-slate-900 text-white px-4 pt-8 pb-20">
        <div className="mx-auto max-w-6xl">
          <div className="flex flex-col sm:flex-row sm:items-center gap-6">
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
            <div>
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
              <div className="mt-4">
                <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">
                  Est. Roster Value
                </p>
                <p
                  className="text-3xl sm:text-4xl font-bold text-emerald-400 leading-none"
                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                >
                  {formatCompactCurrency(total_valuation)}
                </p>
                <p className="mt-1.5 text-[10px] text-slate-500">
                  Includes only players participating in the NIL market
                </p>
              </div>
            </div>
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

        {roster.length === 0 ? (
          <div className="bg-white rounded-xl shadow-md border border-gray-100 p-12 text-center">
            <p className="text-sm font-semibold text-slate-400">
              No players currently tracked for this team.
            </p>
          </div>
        ) : (
          <>
            {/* Mobile cards */}
            <div className="md:hidden space-y-3">
              {roster.map((player) => {
                const isPrivate = !player.is_public;
                const hasStats = (player.usage_rate ?? 0) > 0;
                const tierLabel = hasStats ? player.role_tier : "incoming";
                return (
                  <Link
                    key={player.id}
                    href={`/basketball/players/${player.slug}`}
                    className="block bg-white rounded-xl border border-gray-200 p-4 hover:border-slate-300 transition-colors shadow-sm"
                  >
                    <div className="flex items-center gap-3">
                      <PlayerAvatar
                        headshot_url={player.headshot_url}
                        name={player.name}
                        position={player.position}
                        size={44}
                        className="shrink-0"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <h3
                            className="font-bold text-slate-900 uppercase tracking-tight truncate"
                            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                          >
                            {player.name}
                          </h3>
                          <div className="flex gap-1 shrink-0">
                            {player.position && (
                              <span
                                className={`inline-block rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${basketballPositionBadgeClass(player.position)}`}
                              >
                                {player.position}
                              </span>
                            )}
                            {tierLabel && (
                              <span
                                className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold capitalize ${roleTierBadgeClass(tierLabel)}`}
                              >
                                {tierLabel}
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center justify-end mt-1">
                          {isPrivate ? (
                            <span className="text-slate-400 text-xs italic">Private</span>
                          ) : player.cfo_valuation != null ? (
                            <span
                              className="font-bold text-emerald-600 tabular-nums"
                              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                            >
                              {formatCurrency(player.cfo_valuation)}
                            </span>
                          ) : (
                            <span className="text-slate-400 text-xs">—</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>

            {/* Desktop table */}
            <div className="hidden md:block bg-white rounded-xl shadow-md border border-gray-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 z-10 bg-slate-900 text-slate-300">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">
                        Player
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest w-16">
                        Pos
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest w-24">
                        Role
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest w-16">
                        PPG
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest">
                        NIL Value
                      </th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-gray-100">
                    {roster.map((player) => {
                      const isPrivate = !player.is_public;
                      const hasStats = (player.usage_rate ?? 0) > 0;
                      const tierLabel = hasStats ? player.role_tier : "incoming";
                      return (
                        <tr
                          key={player.id}
                          className="hover:bg-slate-50 transition-colors group"
                        >
                          <td className="px-4 py-3.5">
                            <div className="flex items-center gap-3">
                              <PlayerAvatar
                                headshot_url={player.headshot_url}
                                name={player.name}
                                position={player.position}
                                size={40}
                                className="shrink-0"
                              />
                              <Link
                                href={`/basketball/players/${player.slug}`}
                                className="font-semibold text-slate-900 hover:text-emerald-500 hover:underline transition-colors uppercase tracking-tight"
                                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                              >
                                {player.name}
                              </Link>
                            </div>
                          </td>

                          <td className="px-4 py-3.5">
                            {player.position ? (
                              <span
                                className={`inline-block rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${basketballPositionBadgeClass(player.position)}`}
                              >
                                {player.position}
                              </span>
                            ) : (
                              <span className="text-slate-400">—</span>
                            )}
                          </td>

                          <td className="px-4 py-3.5">
                            {tierLabel && (
                              <span
                                className={`inline-block rounded px-2 py-0.5 text-xs font-semibold capitalize ${roleTierBadgeClass(tierLabel)}`}
                              >
                                {tierLabel}
                              </span>
                            )}
                          </td>

                          <td className="px-4 py-3.5 text-right tabular-nums text-slate-600">
                            {player.ppg != null ? Number(player.ppg).toFixed(1) : "—"}
                          </td>

                          <td className="px-4 py-3.5 text-right">
                            {isPrivate ? (
                              <span className="text-slate-400 text-xs italic">Private</span>
                            ) : player.cfo_valuation != null ? (
                              <span
                                className="font-bold text-emerald-600 tabular-nums"
                                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                              >
                                {formatCurrency(player.cfo_valuation)}
                              </span>
                            ) : (
                              <span className="text-slate-400 text-xs">—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div className="border-t border-gray-100 bg-slate-50 px-4 py-3 flex items-center justify-between">
                <p className="text-xs text-slate-400">
                  <span className="font-semibold text-slate-600">{roster.length}</span>{" "}
                  players
                </p>
                <p className="text-xs text-slate-400">Basketball V1</p>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
