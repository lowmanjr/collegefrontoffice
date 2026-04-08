import Link from "next/link";
import Image from "next/image";
import { Suspense } from "react";
import { supabase } from "@/lib/supabase";
import type { Metadata } from "next";
import { BASE_URL } from "@/lib/constants";

export const revalidate = 900;

export const metadata: Metadata = {
  title: "Top College Football NIL Valuations — Player Rankings | College Front Office",
  description: "See the most valuable college football players ranked by NIL valuation. Proprietary estimates based on production data, draft projections, and market modeling.",
  openGraph: {
    title: "Top College Football NIL Valuations | College Front Office",
    description: "See the most valuable college football players ranked by NIL valuation.",
  },
  alternates: { canonical: `${BASE_URL}/players` },
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
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "ItemList",
            name: "Top Player Valuations",
            description: "The most valuable college football players ranked by CFO algorithmic valuation.",
            url: `${BASE_URL}/players`,
            numberOfItems: rows.length,
            itemListElement: rows.slice(0, 50).map((player, i) => ({
              "@type": "ListItem",
              position: i + 1,
              url: `${BASE_URL}/players/${player.slug}`,
              name: player.name,
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
            Top Player Valuations
          </h1>
        </div>
      </div>

      {/* ── Table ──────────────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="mb-4">
          <Suspense>
            <SearchFilters />
          </Suspense>
        </div>

        {rows.length === 0 ? (
          <div className="bg-white rounded-xl shadow-md p-16 text-center">
            <p className="text-slate-400 text-sm">
              {isFiltered
                ? "No players match your search. Try adjusting the filters."
                : "No players found. Check back soon."}
            </p>
          </div>
        ) : (
          <>
          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {rows.map((player) => {
              const team = player.teams;
              const isPrivate = !player.is_public;
              const isFrozen =
                !isPrivate &&
                (player.status === "Medical Exemption" || player.status === "Inactive");

              return (
                <Link
                  key={player.id}
                  href={`/players/${player.slug}`}
                  className="block bg-white rounded-xl border border-gray-200 p-4 hover:border-slate-300 transition-colors shadow-sm"
                >
                  <div className="flex items-center gap-3">
                    <PlayerAvatar
                      headshot_url={player.headshot_url}
                      name={player.name}
                      position={player.position}
                      size={48}
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
                        {player.position && (
                          <span className={`shrink-0 inline-block rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${positionBadgeClass(player.position)}`}>
                            {player.position}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center justify-between mt-1">
                        <div className="flex items-center gap-2">
                          {team && (
                            <div className="flex items-center gap-1.5">
                              {team.logo_url && (
                                <Image
                                  src={team.logo_url}
                                  alt={team.university_name}
                                  width={16}
                                  height={16}
                                  className="h-4 w-4 object-contain shrink-0"
                                />
                              )}
                              <span className="text-xs text-slate-500">{team.university_name}</span>
                            </div>
                          )}
                        </div>
                        <span
                          className="font-bold text-emerald-600 tabular-nums"
                          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                        >
                          {isPrivate ? (
                            <span className="text-slate-400 text-xs font-normal italic">Private</span>
                          ) : isFrozen ? (
                            <span className="text-slate-400 text-xs font-normal italic">Frozen</span>
                          ) : player.cfo_valuation != null ? (
                            formatCurrency(player.cfo_valuation)
                          ) : "—"}
                        </span>
                      </div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
          <div className="md:hidden mt-3 px-1 flex items-center justify-between">
            <p className="text-xs text-slate-400">
              Showing <span className="font-semibold text-slate-600">{rows.length}</span>{" "}
              {isFiltered ? "matching players" : "players"}
            </p>
            <p className="text-xs text-slate-400">V3.5</p>
          </div>

          {/* Desktop table */}
          <div className="hidden md:block bg-white rounded-xl shadow-md overflow-hidden border border-gray-200">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                {/* Sticky header */}
                <thead className="sticky top-0 z-10 bg-slate-900 text-slate-300">
                  <tr>
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
                  {rows.map((player) => {
                    const team = player.teams;
                    const isPrivate = !player.is_public;
                    const isFrozen =
                      !isPrivate &&
                      (player.status === "Medical Exemption" || player.status === "Inactive");

                    return (
                      <tr key={player.id} className="hover:bg-slate-50 transition-colors group">
                        {/* Player name */}
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
                              href={`/players/${player.slug}`}
                              className="font-semibold text-slate-900 hover:text-emerald-500 hover:underline transition-colors uppercase tracking-tight"
                              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                            >
                              {player.name}
                            </Link>
                          </div>
                        </td>

                        {/* Team */}
                        <td className="px-4 py-3.5">
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
                        <td className="px-4 py-3.5">
                          {player.position ? (
                            <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${positionBadgeClass(player.position)}`}>
                              {player.position}
                            </span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </td>

                        {/* Valuation */}
                        <td className="px-4 py-3.5 text-right">
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
          </>
        )}
      </div>
    </main>
  );
}
