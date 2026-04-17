import Link from "next/link";
import { Suspense } from "react";
import { supabase } from "@/lib/supabase";
import type { Metadata } from "next";
import { BASE_URL } from "@/lib/constants";
import { formatCurrency } from "@/lib/utils";
import { basketballPositionBadgeClass } from "@/lib/ui-helpers";
import BasketballRecruitsFilters from "./BasketballRecruitsFilters";

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

const CLASS_YEARS = ["2026", "2027", "2028"];

interface PageProps {
  searchParams: Promise<{ q?: string; pos?: string; year?: string }>;
}

export default async function BasketballRecruitsPage({ searchParams }: PageProps) {
  const { q, pos, year } = await searchParams;
  const activeYear = year || "2026";

  let query = supabase
    .from("basketball_players")
    .select(
      `id, name, position, star_rating, composite_score, hs_grad_year,
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
          <BasketballRecruitsFilters />
        </Suspense>
        <div className="flex gap-1.5 flex-wrap">
          {CLASS_YEARS.map((y) => {
            const active = activeYear === y;
            const href = `/basketball/recruits?year=${y}${q ? `&q=${q}` : ""}${pos ? `&pos=${pos}` : ""}`;
            return (
              <Link
                key={y}
                href={href}
                className={`px-3 py-2 rounded-lg text-xs font-semibold transition-colors ${
                  active
                    ? "bg-emerald-500 text-white"
                    : "bg-white text-slate-600 border border-gray-200 hover:border-slate-300"
                }`}
              >
                Class of {y}
              </Link>
            );
          })}
        </div>
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
          <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-200">
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
                  {rows.map((recruit: any, i: number) => {
                    const team = recruit.basketball_teams;
                    return (
                      <tr key={recruit.id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            {recruit.headshot_url ? (
                              // eslint-disable-next-line @next/next/no-img-element
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
                          <span className="text-amber-500 text-xs tracking-tight">
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
                                // eslint-disable-next-line @next/next/no-img-element
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
                            {formatCurrency(recruit.cfo_valuation)}
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
        )}
      </div>
    </main>
  );
}
