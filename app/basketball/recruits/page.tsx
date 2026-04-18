import Link from "next/link";
import { Suspense } from "react";
import { supabase } from "@/lib/supabase";
import type { Metadata } from "next";
import { BASE_URL } from "@/lib/constants";
import { formatCurrency } from "@/lib/utils";
import {
  basketballPositionBadgeClass,
  formatDraftProjectionBadge,
} from "@/lib/ui-helpers";
import PlayerAvatar from "@/components/PlayerAvatar";
import BasketballSearchFilters from "@/components/basketball/BasketballSearchFilters";
import BasketballClassYearFilter from "@/components/basketball/BasketballClassYearFilter";

export const revalidate = 3600;

export const metadata: Metadata = {
  title: "Basketball Recruits — NIL Valuations | College Front Office",
  description:
    "NIL valuations for top college basketball recruits — Classes of 2026, 2027, and 2028.",
  openGraph: {
    title: "Basketball Recruit NIL Valuations | College Front Office",
    description:
      "NIL valuations for top college basketball recruits.",
  },
  alternates: { canonical: `${BASE_URL}/basketball/recruits` },
};

interface RecruitTeam {
  university_name: string;
  slug: string;
  logo_url: string | null;
}

interface Recruit {
  id: string;
  name: string;
  position: string | null;
  star_rating: number | null;
  hs_grad_year: number | null;
  nba_draft_projection: number | null;
  cfo_valuation: number | null;
  slug: string | null;
  headshot_url: string | null;
  basketball_teams: RecruitTeam | null;
}

interface PageProps {
  searchParams: Promise<{ q?: string; pos?: string; year?: string }>;
}

export default async function BasketballRecruitsPage({ searchParams }: PageProps) {
  const { q, pos, year } = await searchParams;
  const activeYear = year || "2026";

  let query = supabase
    .from("basketball_players")
    .select(
      `id, name, position, star_rating, hs_grad_year, nba_draft_projection,
       cfo_valuation, slug, headshot_url,
       basketball_teams (university_name, slug, logo_url)`
    )
    .eq("player_tag", "High School Recruit")
    .gte("star_rating", 4)
    .not("cfo_valuation", "is", null);

  if (q) query = query.ilike("name", `%${q}%`);
  if (pos && pos !== "All") {
    query = query.eq("position", pos);
  }
  if (activeYear && activeYear !== "All") {
    query = query.eq("hs_grad_year", parseInt(activeYear));
  }

  const { data: recruits, error } = await query
    .order("composite_score", { ascending: false, nullsFirst: false })
    .limit(100);

  if (error) console.error("Recruits query error:", error);

  const rows = recruits ?? [];
  const isFiltered = !!(q || (pos && pos !== "All"));

  return (
    <main className="min-h-screen bg-gray-100">
      {/* Hero */}
      <div className="bg-slate-900 text-white px-6 py-6">
        <div className="mx-auto max-w-7xl">
          <h1
            className="text-4xl sm:text-5xl font-bold uppercase tracking-tight leading-none"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Basketball Recruit Valuations
          </h1>
        </div>
      </div>

      {/* Filters */}
      <div className="mx-auto max-w-7xl px-4 py-4">
        <Suspense>
          <BasketballSearchFilters />
        </Suspense>
        <Suspense>
          <BasketballClassYearFilter />
        </Suspense>
      </div>

      {/* Table */}
      <div className="mx-auto max-w-7xl px-4 pb-8">
        {rows.length === 0 ? (
          <div className="bg-white rounded-xl shadow-md p-16 text-center">
            <p className="text-slate-400 text-sm">
              {isFiltered
                ? "No recruits match your filters."
                : "No recruits found for this class year. Populate basketball_recruits CSVs to add recruits."}
            </p>
          </div>
        ) : (
          <>
            {/* Mobile cards */}
            <div className="md:hidden space-y-3">
              {(rows as unknown as Recruit[]).map((recruit) => {
                const team = recruit.basketball_teams;
                return (
                  <div
                    key={recruit.id}
                    className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm"
                  >
                    <div className="flex items-center gap-3">
                      <PlayerAvatar
                        headshot_url={recruit.headshot_url}
                        name={recruit.name}
                        position={recruit.position}
                        size={40}
                        className="shrink-0"
                      />
                      <div className="flex-1 min-w-0">
                        {recruit.slug ? (
                          <Link
                            href={`/basketball/players/${recruit.slug}`}
                            className="font-bold text-slate-900 uppercase tracking-tight truncate hover:text-emerald-600 hover:underline transition-colors block"
                            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                          >
                            {recruit.name}
                          </Link>
                        ) : (
                          <h3
                            className="font-bold text-slate-900 uppercase tracking-tight truncate"
                            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                          >
                            {recruit.name}
                          </h3>
                        )}
                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                          {recruit.position && (
                            <span
                              className={`inline-block rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${basketballPositionBadgeClass(recruit.position)}`}
                            >
                              {recruit.position}
                            </span>
                          )}
                          {recruit.star_rating != null && recruit.star_rating > 0 && (
                            <span className="text-yellow-400 text-sm tracking-tight">
                              {"★".repeat(Math.min(recruit.star_rating, 5))}
                            </span>
                          )}
                          {team ? (
                            <Link
                              href={`/basketball/teams/${team.slug}`}
                              className="flex items-center gap-1 text-xs text-slate-600 hover:text-emerald-600 transition-colors"
                            >
                              {team.logo_url && (
                                /* eslint-disable-next-line @next/next/no-img-element */
                                <img
                                  src={team.logo_url}
                                  alt={team.university_name}
                                  width={16}
                                  height={16}
                                  className="h-4 w-4 object-contain shrink-0"
                                />
                              )}
                              <span>{team.university_name}</span>
                            </Link>
                          ) : (
                            <span className="text-xs text-slate-400 italic">Uncommitted</span>
                          )}
                        </div>
                      </div>
                      <div className="shrink-0 self-start">
                        <span
                          className="font-bold text-emerald-600 tabular-nums"
                          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                        >
                          {recruit.cfo_valuation != null
                            ? formatCurrency(recruit.cfo_valuation)
                            : "—"}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Desktop table */}
            <div className="hidden md:block bg-white rounded-xl shadow-md overflow-hidden border border-gray-200">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 z-10 bg-slate-900 text-slate-300">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">Player</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-widest w-14">Pos</th>
                      <th className="px-3 py-3 text-center text-xs font-semibold uppercase tracking-widest w-16">Stars</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">Team</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest">Proj. NIL Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {(rows as unknown as Recruit[]).map((recruit) => {
                      const team = recruit.basketball_teams;
                      const draftLabel = formatDraftProjectionBadge(recruit.nba_draft_projection);
                      return (
                        <tr key={recruit.id} className="hover:bg-slate-50 transition-colors">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-3">
                              {recruit.headshot_url ? (
                                /* eslint-disable-next-line @next/next/no-img-element */
                                <img
                                  src={recruit.headshot_url}
                                  alt={recruit.name}
                                  width={32}
                                  height={32}
                                  className="rounded-full object-cover w-8 h-8 shrink-0 bg-slate-200"
                                />
                              ) : (
                                <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center shrink-0">
                                  <span className="text-slate-500 text-xs font-bold">
                                    {recruit.name.split(" ").map((n: string) => n[0]).slice(0, 2).join("")}
                                  </span>
                                </div>
                              )}
                              {recruit.slug ? (
                                <Link
                                  href={`/basketball/players/${recruit.slug}`}
                                  className="font-semibold text-slate-900 hover:text-emerald-600 hover:underline transition-colors uppercase tracking-tight"
                                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                                >
                                  {recruit.name}
                                </Link>
                              ) : (
                                <span
                                  className="font-semibold text-slate-900 uppercase tracking-tight"
                                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                                >
                                  {recruit.name}
                                </span>
                              )}
                              {draftLabel && (
                                <span className="inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold bg-purple-500 text-white ml-1.5">
                                  {draftLabel}
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-3 py-3">
                            {recruit.position ? (
                              <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${basketballPositionBadgeClass(recruit.position)}`}>
                                {recruit.position}
                              </span>
                            ) : (
                              <span className="text-slate-400">—</span>
                            )}
                          </td>
                          <td className="px-3 py-3 text-center">
                            <span className="text-yellow-400 text-sm tracking-tight">
                              {"★".repeat(Math.min(recruit.star_rating ?? 0, 5))}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            {team ? (
                              <Link
                                href={`/basketball/teams/${team.slug}`}
                                className="flex items-center gap-2 hover:text-emerald-600 transition-colors"
                              >
                                {team.logo_url && (
                                  /* eslint-disable-next-line @next/next/no-img-element */
                                  <img
                                    src={team.logo_url}
                                    alt={team.university_name}
                                    width={16}
                                    height={16}
                                    className="h-4 w-4 object-contain shrink-0"
                                  />
                                )}
                                <span className="text-xs font-medium text-slate-700">{team.university_name}</span>
                              </Link>
                            ) : (
                              <span className="text-xs text-slate-400 italic">Uncommitted</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span
                              className="font-bold text-emerald-600 tabular-nums"
                              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                            >
                              {recruit.cfo_valuation != null
                                ? formatCurrency(recruit.cfo_valuation)
                                : "—"}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="border-t border-gray-100 bg-slate-50 px-4 py-3 flex items-center justify-between">
                <p className="text-xs text-slate-400">
                  <span className="font-semibold text-slate-600">{rows.length}</span> recruits shown (4★ and above)
                </p>
                <p className="text-xs text-slate-400">
                  <Link href="/basketball/methodology" className="text-slate-500 hover:text-slate-700 underline transition-colors">
                    How are these calculated?
                  </Link>
                </p>
              </div>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
