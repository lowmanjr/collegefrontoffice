import Link from "next/link";
import { Suspense } from "react";
import { supabase } from "@/lib/supabase";
import { formatCompactCurrency } from "@/lib/utils";
import type { Metadata } from "next";
import { BASE_URL } from "@/lib/constants";
import BasketballConferenceFilter from "@/components/basketball/BasketballConferenceFilter";

const CONF_SLUG_TO_DB: Record<string, string> = {
  sec: "SEC",
  "big-ten": "Big Ten",
  "big-12": "Big 12",
  acc: "ACC",
  "big-east": "Big East",
};

const MAJOR_CONFERENCES = new Set(["SEC", "Big Ten", "Big 12", "ACC", "Big East"]);

export const revalidate = 3600;

export const metadata: Metadata = {
  title: "College Basketball Team NIL Valuations — Program Rankings | College Front Office",
  description:
    "College basketball programs ranked by estimated roster value.",
  openGraph: {
    title: "College Basketball Team NIL Valuations | College Front Office",
    description:
      "College basketball programs ranked by estimated roster value.",
  },
  alternates: { canonical: `${BASE_URL}/basketball/teams` },
};

function TeamsTableSkeleton() {
  return (
    <div className="animate-pulse bg-white rounded-xl shadow-sm p-4 space-y-2">
      <div className="h-10 rounded-md bg-slate-800 mb-4" />
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="h-12 rounded-md bg-gray-100" />
      ))}
    </div>
  );
}

interface TeamWithValue {
  id: string;
  university_name: string;
  conference: string | null;
  logo_url: string | null;
  slug: string | null;
  total_value: number;
}

async function TeamsGrid({ confSlug }: { confSlug: string | null }) {
  // No team_roster_summary view for basketball yet — compute inline
  const teamsResp = await supabase
    .from("basketball_teams")
    .select("id, university_name, conference, logo_url, slug");

  // Paginate player fetch — Supabase default limit is 1,000 rows
  const PAGE_SIZE = 1000;
  let allPlayers: { team_id: string; cfo_valuation: number | null }[] = [];
  let offset = 0;
  while (true) {
    const { data } = await supabase
      .from("basketball_players")
      .select("team_id, cfo_valuation")
      .eq("roster_status", "active")
      .eq("is_public", true)
      .range(offset, offset + PAGE_SIZE - 1);
    allPlayers.push(...(data ?? []));
    if (!data || data.length < PAGE_SIZE) break;
    offset += PAGE_SIZE;
  }

  const teamsRaw = teamsResp.data ?? [];
  const playersRaw = allPlayers;

  // Aggregate per team
  const teamTotals: Record<string, { total: number }> = {};
  for (const p of playersRaw) {
    if (!p.team_id) continue;
    if (!teamTotals[p.team_id]) teamTotals[p.team_id] = { total: 0 };
    teamTotals[p.team_id].total += p.cfo_valuation ?? 0;
  }

  const allTeams: TeamWithValue[] = teamsRaw
    .map((t) => ({
      ...t,
      total_value: teamTotals[t.id]?.total ?? 0,
    }))
    .sort((a, b) => b.total_value - a.total_value);

  // Apply conference filter (client-side — all data already fetched)
  const confDb = confSlug ? CONF_SLUG_TO_DB[confSlug] ?? null : null;
  const teams = confSlug
    ? allTeams.filter((t) =>
        confSlug === "other"
          ? !MAJOR_CONFERENCES.has(t.conference ?? "")
          : t.conference === confDb
      )
    : allTeams;

  const confLabel = confDb ? `${confDb} ` : confSlug === "other" ? "Other " : "";

  return (
    <>
      <BasketballConferenceFilter activeConf={confSlug ?? null} />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "ItemList",
            name: "Basketball Team Valuations",
            description: "College basketball programs ranked by estimated roster value.",
            url: `${BASE_URL}/basketball/teams`,
            numberOfItems: teams.length,
            itemListElement: teams.map((team, i) => ({
              "@type": "ListItem",
              position: i + 1,
              url: `${BASE_URL}/basketball/teams/${team.slug ?? team.id}`,
              name: team.university_name,
            })),
          }),
        }}
      />
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
                    <td className="px-4 py-3.5">
                      <Link
                        href={`/basketball/teams/${team.slug}`}
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

                    <td className="px-4 py-3.5 hidden sm:table-cell">
                      {team.conference ? (
                        <span className="text-xs text-slate-500 font-medium">
                          {team.conference}
                        </span>
                      ) : (
                        <span className="text-slate-300 text-xs">—</span>
                      )}
                    </td>

                    <td className="px-4 py-3.5 text-right">
                      {team.total_value > 0 ? (
                        <span
                          className="font-bold text-emerald-600 tabular-nums"
                          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                        >
                          {formatCompactCurrency(team.total_value)}
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

        </div>
      )}
    </>
  );
}

export default async function BasketballTeamsPage({
  searchParams,
}: {
  searchParams: Promise<{ conf?: string }>;
}) {
  const { conf } = await searchParams;
  const confSlug = conf ?? null;

  return (
    <main className="min-h-screen bg-gray-100">
      <section className="bg-slate-900 text-white px-6 py-8">
        <div className="mx-auto max-w-6xl">
          <h1
            className="text-4xl sm:text-5xl font-bold uppercase tracking-tight leading-none"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Basketball Team Valuations
          </h1>
        </div>
      </section>

      <div className="mx-auto max-w-6xl px-4 py-8">
        <Suspense fallback={<TeamsTableSkeleton />}>
          <TeamsGrid confSlug={confSlug} />
        </Suspense>
      </div>
    </main>
  );
}
