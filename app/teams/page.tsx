import Link from "next/link";
import Image from "next/image";
import { Suspense } from "react";
import { supabase } from "@/lib/supabase";
import { formatCurrency } from "@/lib/utils";
import CapSpaceComparisonChart from "@/components/CapSpaceComparisonChart";
import type { TeamRosterSummary } from "@/lib/database.types";
import type { Metadata } from "next";

export const revalidate = 3600;

export const metadata: Metadata = {
  title: "CFO Program Valuations — Team Rankings | College Front Office",
  description: "Ranking college football programs by total active roster market cap. 16 Power 4 programs tracked with proprietary NIL valuations.",
  openGraph: {
    title: "CFO Program Valuations | College Front Office",
    description: "Ranking college football programs by total active roster market cap.",
  },
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

async function TeamsGrid() {
  const { data, error } = await supabase
    .from("team_roster_summary")
    .select("*")
    .order("total_roster_value", { ascending: false });

  if (error) {
    return <p className="text-sm text-red-500">Failed to load teams: {error.message}</p>;
  }

  const teams = (data ?? []) as TeamRosterSummary[];
  const grandTotal = teams.reduce((sum, t) => sum + (t.total_roster_value ?? 0), 0);

  const capData = teams.map((t) => {
    const cap = t.estimated_cap_space ?? 20_500_000;
    const payroll = t.total_roster_value ?? 0;
    return {
      name: (t.university_name ?? "Unknown")
        .replace("University of ", "")
        .replace(" University", ""),
      payroll,
      cap,
      pct: Math.round((payroll / cap) * 100),
    };
  });

  return (
    <>
      {/* Combined market summary */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 px-5 py-4 shrink-0">
          <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">Combined Market</p>
          <p
            className="text-3xl font-bold text-emerald-600 leading-none"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            {formatCurrency(grandTotal)}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 px-5 py-4 shrink-0">
          <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">Programs</p>
          <p
            className="text-3xl font-bold text-slate-900 leading-none"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            {teams.length}
          </p>
        </div>
      </div>

      {/* Market cap comparison chart */}
      {capData.length > 0 && (
        <div className="bg-white rounded-xl shadow-md border border-gray-200 p-6 mb-6">
          <h2
            className="text-xs uppercase tracking-widest text-slate-400 mb-1"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Market Cap Comparison
          </h2>
          <p className="text-xs text-slate-400 mb-4">Active roster valuations across all programs</p>
          <CapSpaceComparisonChart data={capData} />
        </div>
      )}

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
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest w-12">
                    #
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest">
                    Program
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest hidden sm:table-cell">
                    Conference
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-widest hidden md:table-cell w-36">
                    Active Contributors
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-widest">
                    Total Market Cap
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-gray-100">
                {teams.map((team, index) => {
                  const rank = index + 1;

                  return (
                    <tr key={team.id} className="hover:bg-slate-50 transition-colors group">
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

                      {/* Program */}
                      <td className="px-4 py-3">
                        <Link
                          href={`/teams/${team.id}`}
                          className="flex items-center gap-3 group/link"
                        >
                          {team.logo_url ? (
                            <Image
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
                            className="font-semibold text-slate-900 group-hover/link:text-green-500 group-hover/link:underline transition-colors uppercase tracking-tight"
                            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                          >
                            {team.university_name}
                          </span>
                        </Link>
                      </td>

                      {/* Conference */}
                      <td className="px-4 py-3 hidden sm:table-cell">
                        {team.conference ? (
                          <span className="text-xs text-slate-500 font-medium">
                            {team.conference}
                          </span>
                        ) : (
                          <span className="text-slate-300 text-xs">—</span>
                        )}
                      </td>

                      {/* Active contributors */}
                      <td className="px-4 py-3 text-center hidden md:table-cell">
                        <span className="inline-block rounded-full bg-slate-100 text-slate-600 px-3 py-0.5 text-xs font-semibold tabular-nums">
                          {team.college_count} player{team.college_count !== 1 ? "s" : ""}
                        </span>
                      </td>

                      {/* Total market cap */}
                      <td className="px-4 py-3 text-right">
                        {team.total_roster_value > 0 ? (
                          <span
                            className="font-bold text-emerald-600 tabular-nums"
                            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                          >
                            {formatCurrency(team.total_roster_value)}
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
              <span className="font-semibold text-slate-600">{teams.length}</span> programs ranked
            </p>
            <p className="text-xs text-slate-400">
              Valuations computed from active College Athlete rosters · C.F.O. Valuation Engine V3.5
            </p>
          </div>
        </div>
      )}
    </>
  );
}

// ─── page ────────────────────────────────────────────────────────────────────

export default function TeamsPage() {
  return (
    <main className="min-h-screen bg-gray-100">
      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="bg-slate-900 text-white px-6 py-10">
        <div className="mx-auto max-w-6xl">
          <Link
            href="/"
            className="inline-block mb-6 text-slate-400 hover:text-white text-sm transition-colors"
          >
            ← Back to Dashboard
          </Link>
          <p className="text-xs uppercase tracking-widest text-slate-400 mb-1">C.F.O. Rankings</p>
          <h1
            className="text-4xl sm:text-5xl font-bold uppercase tracking-tight leading-none"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            CFO Program Valuations
          </h1>
          <p className="mt-3 text-slate-400 text-sm max-w-xl leading-relaxed">
            Ranking college football programs by total active roster market cap.
          </p>
        </div>
      </section>

      {/* ── Content ──────────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-6xl px-4 py-8">
        <Suspense fallback={<TeamsTableSkeleton />}>
          <TeamsGrid />
        </Suspense>
      </div>
    </main>
  );
}
