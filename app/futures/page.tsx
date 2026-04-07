import Link from "next/link";
import Image from "next/image";
import { Suspense } from "react";
import { supabase } from "@/lib/supabase";
import type { Metadata } from "next";

export const revalidate = 1800;

export const metadata: Metadata = {
  title: "CFO Futures Market — HS Recruit NIL Valuations | College Front Office",
  description: "Projected NIL valuations for elite high school football recruits based on 247Sports Composite rankings and the C.F.O. algorithm.",
  openGraph: {
    title: "CFO Futures Market | College Front Office",
    description: "Projected NIL valuations for elite high school football recruits.",
  },
};
import SearchFilters from "@/components/SearchFilters";
import ClassYearFilter from "@/components/ClassYearFilter";
import { formatCurrency } from "@/lib/utils";
import { positionBadgeClass } from "@/lib/ui-helpers";
import type { PlayerWithTeam } from "@/lib/database.types";

// ─── helpers ────────────────────────────────────────────────────────────────

function formatComposite(score: number | null): string {
  if (score == null) return "—";
  return score.toFixed(4);
}

// ─── page ────────────────────────────────────────────────────────────────────

interface PageProps {
  searchParams: Promise<{ q?: string; pos?: string; year?: string }>;
}

export default async function FuturesMarketPage({ searchParams }: PageProps) {
  const { q, pos, year } = await searchParams;

  let query = supabase
    .from("players")
    .select("*, teams(university_name, logo_url)")
    .eq("player_tag", "High School Recruit");

  if (q) query = query.ilike("name", `%${q}%`);
  if (pos && pos !== "All") query = query.eq("position", pos);
  if (year && year !== "All") query = query.eq("hs_grad_year", parseInt(year));

  const { data: recruits, error } = await query
    .order("cfo_valuation", { ascending: false })
    .limit(100);

  if (error) console.error("Supabase Error:", error);

  const rows = (recruits ?? []) as PlayerWithTeam[];
  const isFiltered = !!(q || (pos && pos !== "All") || (year && year !== "All"));

  return (
    <main className="min-h-screen bg-gray-100">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="bg-slate-900 text-white px-6 py-10">
        <div className="mx-auto max-w-7xl">
          <Link
            href="/"
            className="inline-block mb-6 text-slate-400 hover:text-white text-sm transition-colors"
          >
            ← Back to Dashboard
          </Link>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs uppercase tracking-widest text-slate-400 mb-1">
                C.F.O. Recruiting
              </p>
              <h1
                className="text-4xl sm:text-5xl font-bold uppercase tracking-tight leading-none"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                CFO Futures Market
              </h1>
              <p className="mt-3 text-slate-400 text-sm max-w-xl leading-relaxed">
                Projected NIL valuations for elite High School Recruits based on 247Sports Composite
                rankings.
              </p>
            </div>
            <div className="mt-4 sm:mt-0 shrink-0 text-right">
              <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">
                Total Prospects
              </p>
              <p
                className="text-4xl font-bold text-white leading-none"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                {rows.length}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Table ──────────────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-7xl px-4 py-8">
        {/* Class year pills + search & filter bar */}
        <Suspense>
          <ClassYearFilter />
        </Suspense>
        <Suspense>
          <SearchFilters />
        </Suspense>

        {rows.length === 0 ? (
          <div className="bg-white rounded-xl shadow-md p-16 text-center">
            <p className="text-slate-400 text-sm">
              {isFiltered
                ? "No recruits match your search. Try adjusting the filters."
                : "No recruits found. Check back soon."}
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
                      Commitment
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest w-16">
                      Pos
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest hidden sm:table-cell w-20">
                      Class
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest hidden md:table-cell w-28">
                      Composite
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest">
                      Projected Value
                    </th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-gray-100">
                  {rows.map((recruit, index) => {
                    const rank = index + 1;
                    const team = recruit.teams;
                    const isPrivate = !recruit.is_public;

                    return (
                      <tr key={recruit.id} className="hover:bg-slate-50 transition-colors group">
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
                          <Link
                            href={`/players/${recruit.id}`}
                            className="font-semibold text-slate-900 hover:text-green-500 hover:underline transition-colors uppercase tracking-tight"
                            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                          >
                            {recruit.name}
                          </Link>
                          {recruit.national_rank != null && (
                            <p className="text-xs text-slate-400 mt-0.5 font-mono">
                              #{recruit.national_rank} national
                            </p>
                          )}
                        </td>

                        {/* Commitment */}
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
                            <span className="text-slate-400 text-xs italic">Uncommitted</span>
                          )}
                        </td>

                        {/* Position */}
                        <td className="px-4 py-3">
                          {recruit.position ? (
                            <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${positionBadgeClass(recruit.position)}`}>
                              {recruit.position}
                            </span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </td>

                        {/* Class year */}
                        <td className="px-4 py-3 hidden sm:table-cell">
                          {recruit.class_year ? (
                            <span
                              className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                                recruit.class_year === "2026"
                                  ? "bg-blue-100 text-blue-700"
                                  : "bg-purple-100 text-purple-700"
                              }`}
                            >
                              {recruit.class_year}
                            </span>
                          ) : (
                            <span className="text-slate-400 text-xs">—</span>
                          )}
                        </td>

                        {/* Composite score */}
                        <td className="px-4 py-3 text-right hidden md:table-cell">
                          <span className="font-mono text-xs text-slate-600 tabular-nums">
                            {formatComposite(recruit.composite_score)}
                          </span>
                        </td>

                        {/* Projected value */}
                        <td className="px-4 py-3 text-right">
                          {isPrivate ? (
                            <span className="text-slate-400 text-xs italic">Private</span>
                          ) : recruit.cfo_valuation != null ? (
                            <span
                              className="font-bold text-emerald-600 tabular-nums"
                              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                            >
                              {formatCurrency(recruit.cfo_valuation)}
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
                {isFiltered ? "matching prospects" : "prospects"}
              </p>
              <p className="text-xs text-slate-400">
                Futures valuations based on 247Sports Composite · C.F.O. Valuation Engine V3.5
              </p>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
