import Link from "next/link";
import { Suspense } from "react";
import { supabase } from "@/lib/supabase";
import { formatCurrency, formatCompactCurrency } from "@/lib/utils";
import type { TeamRosterSummary } from "@/lib/database.types";
import type { Metadata } from "next";
import { BASE_URL } from "@/lib/constants";
import ConferenceFilter from "@/components/ConferenceFilter";

const CONF_SLUG_TO_DB: Record<string, string> = {
  sec: "SEC",
  "big-ten": "Big Ten",
  "big-12": "Big 12",
  acc: "ACC",
};

export const revalidate = 3600;

export const metadata: Metadata = {
  title: "College Football Team NIL Valuations — Program Rankings | College Front Office",
  description: "College football programs ranked by estimated roster value. See which teams have the most valuable rosters in the NIL era.",
  openGraph: {
    title: "College Football Team NIL Valuations | College Front Office",
    description: "College football programs ranked by estimated roster value.",
  },
  alternates: { canonical: `${BASE_URL}/teams` },
};

// ─── skeletons ───────────────────────────────────────────────────────────────

function TeamsTableSkeleton() {
  return (
    <div className="animate-pulse bg-white rounded-xl shadow-sm p-4 space-y-2">
      <div className="h-10 rounded-md bg-slate-800 mb-4" />
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="h-12 rounded-md bg-gray-100" />
      ))}
    </div>
  );
}

// ─── async data component ─────────────────────────────────────────────────────

async function TeamsGrid({ confSlug }: { confSlug: string | null }) {
  const confDb = confSlug ? CONF_SLUG_TO_DB[confSlug] ?? null : null;

  // Always fetch all teams for conference counts
  const allQuery = supabase
    .from("team_roster_summary")
    .select("id, conference");

  // Filtered query for display
  const filteredQuery = supabase
    .from("team_roster_summary")
    .select("*")
    .order("total_program_value", { ascending: false });
  if (confDb) filteredQuery.eq("conference", confDb);

  const [allResp, filteredResp, slugsResp] = await Promise.all([
    allQuery,
    filteredQuery,
    supabase.from("teams").select("id, slug"),
  ]);

  const { data, error } = filteredResp;

  if (error) {
    return <p className="text-sm text-red-500">Failed to load teams: {error.message}</p>;
  }

  // Build conference counts from the unfiltered set
  const confCounts: Record<string, number> = {};
  for (const t of allResp.data ?? []) {
    const c = (t as { conference: string }).conference;
    if (c) confCounts[c] = (confCounts[c] ?? 0) + 1;
  }
  const totalCount = (allResp.data ?? []).length;

  const slugMap = Object.fromEntries((slugsResp.data ?? []).map((t: { id: string; slug: string }) => [t.id, t.slug]));
  const teams = (data ?? []).map((t: TeamRosterSummary) => ({ ...t, slug: slugMap[t.id] ?? t.id }));

  const confLabel = confDb ? `${confDb} ` : "";

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "ItemList",
            name: "Team Valuations",
            description: "College football programs ranked by estimated roster value.",
            url: `${BASE_URL}/teams`,
            numberOfItems: teams.length,
            itemListElement: teams.map((team, i) => ({
              "@type": "ListItem",
              position: i + 1,
              url: `${BASE_URL}/teams/${slugMap[team.id] ?? team.id}`,
              name: team.university_name,
            })),
          }),
        }}
      />
      <ConferenceFilter activeConf={confSlug} counts={confCounts} totalCount={totalCount} />

      {teams.length === 0 ? (
        <div className="bg-white rounded-xl shadow-md p-16 text-center">
          <p className="text-slate-400 text-sm">No programs found.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-200">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 z-10 bg-slate-900 text-slate-300">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">
                    Program
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest hidden sm:table-cell">
                    Conference
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest">
                    Est. Roster Value
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-gray-100">
                {teams.map((team) => (
                  <tr key={team.id} className="hover:bg-slate-50 transition-colors group">
                    {/* Program */}
                    <td className="px-4 py-3.5">
                      <Link
                        href={`/teams/${team.slug}`}
                        className="flex items-center gap-3 group/link"
                      >
                        {team.logo_url ? (
                          /* eslint-disable-next-line @next/next/no-img-element */
                          <img
                            src={team.logo_url}
                            alt={`${team.university_name} logo`}
                            width={32}
                            height={32}
                            className="h-8 w-8 object-contain shrink-0"
                          />
                        ) : (
                          <div className="h-8 w-8 rounded-full bg-slate-200 shrink-0" />
                        )}
                        <span
                          className="font-semibold text-slate-900 group-hover/link:text-emerald-500 group-hover/link:underline transition-colors uppercase tracking-tight"
                          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                        >
                          {team.university_name}
                        </span>
                      </Link>
                    </td>

                    {/* Conference */}
                    <td className="px-4 py-3.5 hidden sm:table-cell">
                      {team.conference ? (
                        <span className="text-xs text-slate-500 font-medium">
                          {team.conference}
                        </span>
                      ) : (
                        <span className="text-slate-300 text-xs">—</span>
                      )}
                    </td>

                    {/* Roster value */}
                    <td className="px-4 py-3.5 text-right">
                      {team.total_program_value > 0 ? (
                        <span
                          className="font-bold text-emerald-600 tabular-nums"
                          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                        >
                          {formatCompactCurrency(team.total_program_value)}
                        </span>
                      ) : (
                        <span className="text-slate-400 text-xs">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Footer */}
          <div className="border-t border-gray-100 bg-slate-50 px-4 py-3 flex items-center justify-between">
            <p className="text-xs text-slate-400">
              <span className="font-semibold text-slate-600">{teams.length}</span> {confLabel}programs ranked
            </p>
            <p className="text-xs text-slate-400">
              C.F.O. Valuation Engine V3.6b
            </p>
          </div>
        </div>
      )}
    </>
  );
}

// ─── page ────────────────────────────────────────────────────────────────────

export default async function TeamsPage({
  searchParams,
}: {
  searchParams: Promise<{ conf?: string }>;
}) {
  const { conf } = await searchParams;
  const confSlug = conf ?? null;

  return (
    <main className="min-h-screen bg-gray-100">
      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="bg-slate-900 text-white px-6 py-8">
        <div className="mx-auto max-w-6xl">
          <h1
            className="text-4xl sm:text-5xl font-bold uppercase tracking-tight leading-none"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Team Valuations
          </h1>
        </div>
      </section>

      {/* ── Content ──────────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-6xl px-4 py-8">
        <Suspense fallback={<TeamsTableSkeleton />}>
          <TeamsGrid confSlug={confSlug} />
        </Suspense>
      </div>
    </main>
  );
}
