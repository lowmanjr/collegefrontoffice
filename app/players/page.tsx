import Link from "next/link";
import Image from "next/image";
import { Suspense } from "react";
import { supabase } from "@/lib/supabase";
import type { Metadata } from "next";

export const revalidate = 900;

export const metadata: Metadata = {
  title: "Top Player Valuations — CFO NIL Valuations | College Front Office",
  description: "The most valuable active college football players ranked by C.F.O. algorithmic valuation. Proprietary estimates based on production, draft projection, and market data.",
  openGraph: {
    title: "Top Player Valuations | College Front Office",
    description: "The most valuable active college football players ranked by C.F.O. algorithmic valuation.",
  },
};
import SearchFilters from "@/components/SearchFilters";
import PlayerAvatar from "@/components/PlayerAvatar";
import { formatCurrency } from "@/lib/utils";
import { positionBadgeClass } from "@/lib/ui-helpers";
import type { PlayerWithTeam } from "@/lib/database.types";

// ─── page ────────────────────────────────────────────────────────────────────

interface PageProps {
  searchParams: Promise<{ q?: string; pos?: string }>;
}

export default async function BigBoardPage({ searchParams }: PageProps) {
  const { q, pos } = await searchParams;

  let query = supabase
    .from("players")
    .select("*, teams(university_name, logo_url)")
    .eq("player_tag", "College Athlete")
    .not("cfo_valuation", "is", null);

  if (q) query = query.ilike("name", `%${q}%`);
  if (pos && pos !== "All") query = query.eq("position", pos);

  const { data: players, error } = await query
    .order("cfo_valuation", { ascending: false })
    .limit(100);

  if (error) console.error("Supabase Error:", error);

  const rows = (players ?? []) as PlayerWithTeam[];
  const isFiltered = !!(q || (pos && pos !== "All"));

  return (
    <main className="min-h-screen bg-gray-100">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="bg-slate-900 text-white px-6 py-8">
        <div className="mx-auto max-w-7xl">
          <h1
            className="text-4xl sm:text-5xl font-bold uppercase tracking-tight leading-none"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Top Player Valuations
          </h1>
          <div className="mt-6">
            <Suspense>
              <SearchFilters />
            </Suspense>
          </div>
        </div>
      </div>

      {/* ── Table ──────────────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-7xl px-4 py-6">

        {rows.length === 0 ? (
          <div className="bg-white rounded-xl shadow-md p-16 text-center">
            <p className="text-slate-400 text-sm">
              {isFiltered
                ? "No players match your search. Try adjusting the filters."
                : "No players found. Check back soon."}
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-200">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                {/* Sticky header */}
                <thead className="sticky top-0 z-10 bg-slate-900 text-slate-300">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest w-12">
                      #
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">
                      Player
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">
                      Team
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
                  {rows.map((player, index) => {
                    const rank = index + 1;
                    const team = player.teams;
                    const isPrivate = !player.is_public;
                    const isFrozen =
                      !isPrivate &&
                      (player.status === "Medical Exemption" || player.status === "Inactive");

                    return (
                      <tr key={player.id} className="hover:bg-slate-50 transition-colors group">
                        {/* Rank */}
                        <td className="px-4 py-3 text-slate-400 font-mono text-xs tabular-nums">
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

                        {/* Team */}
                        <td className="px-4 py-3">
                          {team ? (
                            <div className="flex items-center gap-2">
                              {team.logo_url && (
                                <Image
                                  src={team.logo_url}
                                  alt={`${team.university_name} logo`}
                                  width={20}
                                  height={20}
                                  className="h-5 w-5 object-contain shrink-0"
                                />
                              )}
                              <span className="text-slate-700 text-xs font-medium leading-tight">
                                {team.university_name}
                              </span>
                            </div>
                          ) : (
                            <span className="text-slate-400 text-xs">—</span>
                          )}
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
                          ) : isFrozen ? (
                            <span className="text-slate-400 text-xs italic">Frozen</span>
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

            {/* Footer */}
            <div className="border-t border-gray-100 bg-slate-50 px-4 py-3 flex items-center justify-between">
              <p className="text-xs text-slate-400">
                Showing <span className="font-semibold text-slate-600">{rows.length}</span>{" "}
                {isFiltered ? "matching players" : "players"}
              </p>
              <p className="text-xs text-slate-400">
                Rankings updated algorithmically · C.F.O. Valuation Engine V3.5
              </p>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
