import Link from "next/link";
import Image from "next/image";
import { supabase } from "@/lib/supabase";
import { formatCurrency } from "@/lib/utils";
import { positionBadgeClass } from "@/lib/ui-helpers";
import PositionValueChart from "@/components/PositionValueChart";
import PlayerAvatar from "@/components/PlayerAvatar";
import type { PlayerRow } from "@/lib/database.types";

export const revalidate = 900;

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { data } = await supabase
    .from("teams")
    .select("university_name, conference")
    .eq("id", id)
    .single();
  return {
    title: data
      ? `${data.university_name} — ${data.conference} | CFO`
      : "Team Profile | College Front Office",
    description: data
      ? `NIL roster valuation for ${data.university_name} (${data.conference})`
      : "Team NIL roster valuation",
  };
}

// ─── types ───────────────────────────────────────────────────────────────────

type Player = Pick<
  PlayerRow,
  "id" | "name" | "position" | "class_year" | "star_rating" | "cfo_valuation" | "is_public" | "roster_status" | "headshot_url"
>;

// ─── page ────────────────────────────────────────────────────────────────────

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function TeamDashboardPage({ params }: PageProps) {
  const { id } = await params;

  const [teamResp, playersResp, recruitsResp] = await Promise.all([
    supabase
      .from("teams")
      .select("id, university_name, conference, logo_url")
      .eq("id", id)
      .single(),
    supabase
      .from("players")
      .select("id, name, position, class_year, star_rating, cfo_valuation, is_public, roster_status, headshot_url")
      .eq("team_id", id)
      .eq("player_tag", "College Athlete")
      .order("cfo_valuation", { ascending: false, nullsFirst: false }),
    supabase
      .from("players")
      .select("id, name, position, class_year, star_rating, cfo_valuation, is_public, roster_status, headshot_url")
      .eq("team_id", id)
      .eq("player_tag", "High School Recruit")
      .eq("hs_grad_year", 2026)
      .not("cfo_valuation", "is", null)
      .order("cfo_valuation", { ascending: false, nullsFirst: false }),
  ]);

  const { data: team, error } = teamResp;
  const allRoster = (playersResp.data ?? []) as Player[];
  const roster = allRoster.filter((p) => !p.roster_status || p.roster_status === "active");
  const departed = allRoster.filter((p) => p.roster_status && p.roster_status !== "active");
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

  const total_valuation = roster.reduce(
    (sum, p) => sum + (p.is_public && p.cfo_valuation != null ? p.cfo_valuation : 0),
    0
  );
  const recruit_valuation = recruits.reduce(
    (sum, p) => sum + (p.cfo_valuation ?? 0),
    0
  );

  // Position group aggregation for chart
  function toPositionGroup(pos: string | null): string {
    if (!pos) return "SPEC";
    const p = pos.toUpperCase();
    if (p === "QB") return "QB";
    if (p === "WR") return "WR";
    if (p === "RB") return "RB";
    if (p === "TE") return "TE";
    if (["OT", "OG", "C", "OL", "IOL"].includes(p)) return "OL";
    if (["DT", "DL"].includes(p)) return "DL";
    if (["EDGE", "DE"].includes(p)) return "EDGE";
    if (p === "LB") return "LB";
    if (["CB", "S"].includes(p)) return "DB";
    return "SPEC";
  }

  const GROUP_ORDER = ["QB", "WR", "RB", "TE", "OL", "EDGE", "DL", "LB", "DB", "SPEC"];

  const positionGroups = GROUP_ORDER
    .map((group) => {
      const players = roster.filter((p) => toPositionGroup(p.position) === group);
      const value = players.reduce((sum, p) => sum + (p.is_public && p.cfo_valuation != null ? p.cfo_valuation : 0), 0);
      return { group, value, count: players.length };
    })
    .filter((g) => g.count > 0);

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
            url: `https://collegefrontoffice.com/teams/${id}`,
          }),
        }}
      />
      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="bg-slate-900 text-white px-4 pt-10 pb-24">
        <div className="mx-auto max-w-6xl">
          <Link
            href="/players"
            className="inline-block mb-8 text-slate-400 hover:text-white text-sm transition-colors"
          >
            ← Back to Big Board
          </Link>

          {/* Team identity row */}
          <div className="flex flex-col sm:flex-row sm:items-center gap-6 mb-10">
            {team.logo_url && (
              <Image
                src={team.logo_url}
                alt={`${team.university_name} logo`}
                width={96}
                height={96}
                className="h-24 w-24 object-contain shrink-0"
                priority
              />
            )}
            <div>
              <p className="text-xs uppercase tracking-widest text-slate-400 mb-1">
                Team Dashboard
              </p>
              <h1
                className="text-5xl sm:text-6xl font-bold uppercase tracking-tight leading-none"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                {team.university_name}
              </h1>
              {team.conference && (
                <span className="mt-3 inline-block rounded px-2.5 py-0.5 text-xs font-semibold uppercase tracking-widest bg-slate-700 text-slate-300">
                  {team.conference}
                </span>
              )}
            </div>
          </div>

          {/* Market cap block */}
          <div className="border-t border-slate-700 pt-8 grid grid-cols-1 gap-6 sm:grid-cols-[1fr_auto]">
            <div>
              <p className="text-xs uppercase tracking-widest text-slate-400 mb-2">
                Total Roster Market Cap
              </p>
              <p
                className="text-5xl sm:text-6xl font-bold text-emerald-400 leading-none"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                {formatCurrency(total_valuation)}
              </p>
              <p className="mt-2 text-xs text-slate-500">
                {roster.length} College Athlete{roster.length !== 1 ? "s" : ""} on active roster
              </p>
              {recruits.length > 0 && (
                <p className="mt-1 text-xs text-slate-500">
                  + {recruits.length} incoming recruit{recruits.length !== 1 ? "s" : ""} ({formatCurrency(recruit_valuation)})
                </p>
              )}
            </div>

            {/* Disclaimer */}
            <div className="sm:max-w-sm bg-slate-800 border border-slate-700 rounded-xl px-4 py-4 flex gap-3 items-start">
              {/* Info icon */}
              <svg
                className="mt-0.5 h-4 w-4 shrink-0 text-slate-400"
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  clipRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
                />
              </svg>
              <p className="text-xs text-slate-400 leading-relaxed">
                <span className="font-semibold text-slate-300">Note on Valuations: </span>
                Total Market Cap is an analytical projection. Valuations are dynamically generated
                based on 247Sports composite ratings, active depth-chart status, and positional
                market premiums. They are designed to illustrate relative roster equity and pipeline
                strength, not exact NIL compensation.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Roster Table ─────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-6xl px-4 -mt-10 relative z-10 pb-16">
        {/* Position value chart */}
        {positionGroups.length > 0 && (
          <div className="bg-white rounded-xl shadow-md border border-gray-200 p-6 mb-8">
            <h2
              className="text-xs uppercase tracking-widest text-slate-400 mb-1"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              Roster Value by Position
            </h2>
            <p className="text-xs text-slate-400 mb-4">Aggregate CFO valuations across position groups</p>
            <PositionValueChart data={positionGroups} />
          </div>
        )}

        <div className="mb-4 flex items-baseline justify-between">
          <h2
            className="text-2xl font-bold text-slate-900 uppercase tracking-wide"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Active Roster
          </h2>
          {roster.length > 0 && (
            <span className="text-sm text-gray-400">{roster.length} players</span>
          )}
        </div>

        {roster.length === 0 ? (
          <div className="bg-white rounded-xl shadow-md border border-gray-100 p-12 text-center">
            <p className="text-sm font-semibold text-slate-400">
              No College Athletes currently tracked for this team.
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-md border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 z-10 bg-slate-900 text-slate-300">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest w-12">
                      #
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">
                      Player
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest w-16">
                      Pos
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest">
                      CFO Valuation
                    </th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-gray-100">
                  {roster.map((player, index) => {
                    const rank = index + 1;
                    const isPrivate = !player.is_public;

                    return (
                      <tr key={player.id} className="hover:bg-slate-50 transition-colors group">
                        {/* Rank */}
                        <td className="px-4 py-3 text-xs tabular-nums">
                          {rank <= 3 ? (
                            <span
                              className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                                rank === 1
                                  ? "bg-yellow-400 text-yellow-900"
                                  : rank === 2
                                    ? "bg-slate-300 text-slate-700"
                                    : "bg-amber-600 text-white"
                              }`}
                            >
                              {rank}
                            </span>
                          ) : (
                            <span className="text-slate-400 font-semibold">{rank}</span>
                          )}
                        </td>

                        {/* Player name */}
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            <PlayerAvatar
                              headshot_url={player.headshot_url}
                              name={player.name}
                              position={player.position}
                              size={32}
                              className="shrink-0"
                            />
                            <Link
                              href={`/players/${player.id}`}
                              className="font-semibold text-slate-900 hover:text-green-500 hover:underline transition-colors uppercase tracking-tight"
                              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                            >
                              {player.name}
                            </Link>
                          </div>
                        </td>

                        {/* Position */}
                        <td className="px-4 py-3">
                          {player.position ? (
                            <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${positionBadgeClass(player.position)}`}>
                              {player.position}
                            </span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </td>

                        {/* Valuation */}
                        <td className="px-4 py-3 text-right">
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

            {/* Table footer */}
            <div className="border-t border-gray-100 bg-slate-50 px-4 py-3 flex items-center justify-between">
              <p className="text-xs text-slate-400">
                <span className="font-semibold text-slate-600">{roster.length}</span> players on
                roster
              </p>
              <p className="text-xs text-slate-400">
                Active payroll:{" "}
                <span className="font-semibold text-emerald-600">
                  {formatCurrency(total_valuation)}
                </span>
              </p>
            </div>
          </div>
        )}

        {/* ── Incoming Recruits ─────────────────────────────────────────── */}
        {recruits.length > 0 && (
          <div className="mt-8 bg-white rounded-xl shadow-md overflow-hidden">
            <div className="px-4 py-3 flex items-center justify-between border-b border-gray-100">
              <h3
                className="text-lg font-bold text-slate-900 uppercase tracking-wide"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                Incoming Recruits
              </h3>
              <span className="text-sm text-purple-600 font-semibold">
                {recruits.length} committed &middot; {formatCurrency(recruit_valuation)}
              </span>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-xs uppercase tracking-wider text-slate-400">
                  <th className="text-left py-2 px-4 font-medium">Player</th>
                  <th className="text-left py-2 px-4 font-medium">Pos</th>
                  <th className="text-left py-2 px-4 font-medium">Stars</th>
                  <th className="text-right py-2 px-4 font-medium">CFO Value</th>
                </tr>
              </thead>
              <tbody>
                {recruits.map((player) => (
                  <tr
                    key={player.id}
                    className="border-b border-gray-50 hover:bg-purple-50/50 transition-colors"
                  >
                    <td className="py-2.5 px-4">
                      <div className="flex items-center gap-2">
                        <PlayerAvatar
                          headshot_url={player.headshot_url}
                          name={player.name}
                          position={player.position}
                          size={28}
                          className="shrink-0"
                        />
                        <Link
                          href={`/players/${player.id}`}
                          className="font-semibold text-slate-800 hover:text-purple-600 transition-colors"
                        >
                          {player.name}
                        </Link>
                      </div>
                    </td>
                    <td className="py-2.5 px-4">
                      <span className="rounded bg-purple-100 text-purple-700 px-2 py-0.5 text-xs font-semibold">
                        {player.position ?? "—"}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 text-yellow-500">
                      {"★".repeat(Math.min(player.star_rating ?? 0, 5))}
                    </td>
                    <td
                      className="py-2.5 px-4 text-right font-bold text-purple-700 tabular-nums"
                      style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                    >
                      {player.cfo_valuation != null
                        ? formatCurrency(player.cfo_valuation)
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── Departed Players ─────────────────────────────────────────── */}
        {departed.length > 0 && (
          <details className="mt-8 group">
            <summary className="cursor-pointer list-none flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-slate-700 transition-colors select-none">
              <svg className="h-4 w-4 text-slate-400 transition-transform group-open:rotate-90" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
              </svg>
              Departed Players ({departed.length})
            </summary>
            <div className="mt-3 bg-white rounded-xl shadow-md border border-gray-200 overflow-hidden opacity-75">
              <table className="w-full text-sm">
                <thead className="bg-slate-200 text-slate-500">
                  <tr>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-widest">Player</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-widest w-16">Pos</th>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-widest hidden sm:table-cell">Status</th>
                    <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-widest">Last Valuation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {departed.map((player) => {
                    const statusLabel = player.roster_status
                      ? player.roster_status.replace("departed_", "").replace(/^\w/, (c: string) => c.toUpperCase())
                      : "Departed";
                    return (
                      <tr key={player.id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-2.5">
                          <Link
                            href={`/players/${player.id}`}
                            className="font-semibold text-slate-500 hover:text-slate-700 transition-colors uppercase tracking-tight text-sm"
                            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                          >
                            {player.name}
                          </Link>
                        </td>
                        <td className="px-4 py-2.5">
                          {player.position ? (
                            <span className="inline-block rounded bg-slate-200 text-slate-500 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide">
                              {player.position}
                            </span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 hidden sm:table-cell">
                          <span className="text-xs text-slate-400 font-medium">{statusLabel}</span>
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          {player.cfo_valuation != null ? (
                            <span
                              className="text-slate-400 tabular-nums line-through text-sm"
                              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                            >
                              {formatCurrency(player.cfo_valuation)}
                            </span>
                          ) : (
                            <span className="text-slate-300 text-xs">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </details>
        )}
      </div>
    </div>
  );
}
