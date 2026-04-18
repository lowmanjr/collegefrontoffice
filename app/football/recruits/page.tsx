import Link from "next/link";
import Image from "next/image";
import { Suspense } from "react";
import { supabase } from "@/lib/supabase";
import type { Metadata } from "next";
import { BASE_URL } from "@/lib/constants";

export const revalidate = 1800;

export const metadata: Metadata = {
  title: "Top Football Recruit NIL Valuations — HS Recruit Rankings | College Front Office",
  description: "Projected NIL valuations for elite high school football recruits. Ranked by recruiting profile with position and program premiums.",
  openGraph: {
    title: "Top Football Recruit NIL Valuations | College Front Office",
    description: "Projected NIL valuations for elite high school football recruits.",
  },
  alternates: { canonical: `${BASE_URL}/football/recruits` },
};
import SearchFilters from "@/components/SearchFilters";
import ClassYearFilter from "@/components/ClassYearFilter";
import PlayerAvatar from "@/components/PlayerAvatar";
import { formatCurrency } from "@/lib/utils";
import { positionBadgeClass } from "@/lib/ui-helpers";
import type { PlayerWithTeam } from "@/lib/database.types";

// ─── page ────────────────────────────────────────────────────────────────────

interface PageProps {
  searchParams: Promise<{ q?: string; pos?: string; year?: string }>;
}

export default async function FuturesMarketPage({ searchParams }: PageProps) {
  const { q, pos, year } = await searchParams;
  const activeYear = year || "2026";

  let query = supabase
    .from("players")
    .select("*, teams(university_name, logo_url)")
    .eq("player_tag", "High School Recruit")
    .gte("star_rating", 4);

  if (q) query = query.ilike("name", `%${q}%`);
  if (pos && pos !== "All") {
    const POS_ALIASES: Record<string, string[]> = {
      K: ["K", "PK"],
      DL: ["DL", "DT"],
      S: ["S", "DB"],
    };
    const posValues = POS_ALIASES[pos] ?? [pos];
    query = posValues.length === 1
      ? query.eq("position", posValues[0])
      : query.in("position", posValues);
  }
  if (activeYear && activeYear !== "All") {
    query = query.eq("hs_grad_year", parseInt(activeYear));
  }

  const { data: recruits, error } = await query
    .order("composite_score", { ascending: false, nullsFirst: false })
    .limit(100);

  if (error) console.error("Supabase Error:", error);

  const rows = (recruits ?? []) as PlayerWithTeam[];
  const isFiltered = !!(q || (pos && pos !== "All"));

  return (
    <main className="min-h-screen bg-gray-100">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "ItemList",
            name: "Football Recruit Valuations",
            description: "Elite high school football recruit valuations.",
            url: `${BASE_URL}/football/recruits`,
            numberOfItems: rows.length,
            itemListElement: rows.slice(0, 50).map((recruit, i) => ({
              "@type": "ListItem",
              position: i + 1,
              url: `${BASE_URL}/football/players/${recruit.slug}`,
              name: recruit.name,
            })),
          }),
        }}
      />
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="bg-slate-900 text-white px-6 py-8">
        <div className="mx-auto max-w-7xl">
          <h1
            className="text-4xl sm:text-5xl font-bold uppercase tracking-tight leading-none"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Football Recruit Valuations
          </h1>
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
          <>
          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {rows.map((recruit) => {
              const team = recruit.teams;
              const isPrivate = !recruit.is_public;

              return (
                <Link
                  key={recruit.id}
                  href={`/football/players/${recruit.slug}`}
                  className="block bg-white rounded-xl border border-gray-200 p-4 hover:border-slate-300 transition-colors shadow-sm"
                >
                  <div className="flex items-center gap-3">
                    <PlayerAvatar
                      headshot_url={recruit.headshot_url}
                      name={recruit.name}
                      position={recruit.position}
                      size={48}
                      className="shrink-0"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <div className="min-w-0">
                          <h3
                            className="font-bold text-slate-900 uppercase tracking-tight truncate"
                            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                          >
                            {recruit.name}
                          </h3>
                        </div>
                        {recruit.position && (
                          <span className={`shrink-0 inline-block rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${positionBadgeClass(recruit.position)}`}>
                            {recruit.position}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center justify-between mt-2">
                        <div className="flex items-center gap-2">
                          {team ? (
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
                          ) : (
                            <span className="text-xs text-slate-400 italic">Uncommitted</span>
                          )}
                          {recruit.star_rating && recruit.star_rating > 0 && (
                            <span className="text-xs text-yellow-400">{"★".repeat(Math.min(recruit.star_rating, 5))}</span>
                          )}
                        </div>
                        <span className="font-bold text-emerald-600 tabular-nums" style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
                          {isPrivate ? (
                            <span className="text-slate-400 text-xs font-normal italic">Private</span>
                          ) : recruit.cfo_valuation != null ? (
                            formatCurrency(recruit.cfo_valuation)
                          ) : "—"}
                        </span>
                      </div>
                    </div>
                  </div>
                </Link>
              );
            })}
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
                      Commitment
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest w-16">
                      Pos
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest w-28">
                      Rating
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest">
                      Proj. NIL Value
                    </th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-gray-100">
                  {rows.map((recruit) => {
                    const team = recruit.teams;
                    const isPrivate = !recruit.is_public;

                    return (
                      <tr key={recruit.id} className="hover:bg-slate-50 transition-colors group">
                        {/* Player name */}
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-3">
                            <PlayerAvatar
                              headshot_url={recruit.headshot_url}
                              name={recruit.name}
                              position={recruit.position}
                              size={40}
                              className="shrink-0"
                            />
                            <div>
                              <Link
                                href={`/football/players/${recruit.slug}`}
                                className="font-semibold text-slate-900 hover:text-emerald-500 hover:underline transition-colors uppercase tracking-tight"
                                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                              >
                                {recruit.name}
                              </Link>
                            </div>
                          </div>
                        </td>

                        {/* Commitment */}
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
                            <span className="text-slate-400 text-xs italic">Uncommitted</span>
                          )}
                        </td>

                        {/* Position */}
                        <td className="px-4 py-3.5">
                          {recruit.position ? (
                            <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${positionBadgeClass(recruit.position)}`}>
                              {recruit.position}
                            </span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </td>

                        {/* Rating (stars) */}
                        <td className="px-4 py-3.5 text-right">
                          {recruit.star_rating && recruit.star_rating > 0 ? (
                            <span className="text-sm leading-none tracking-tight">
                              <span className="text-yellow-400">{"★".repeat(Math.min(recruit.star_rating, 5))}</span>
                            </span>
                          ) : (
                            <span className="text-slate-400 text-xs">—</span>
                          )}
                        </td>

                        {/* Projected value */}
                        <td className="px-4 py-3.5 text-right">
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

          </div>
          </>
        )}
      </div>
    </main>
  );
}
