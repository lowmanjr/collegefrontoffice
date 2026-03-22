import Link from "next/link";
import { supabase } from "@/lib/supabase";

// ─── helpers ────────────────────────────────────────────────────────────────

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function capUsedPct(payroll: number, cap: number): number {
  return Math.round((payroll / cap) * 100);
}

function capBadgeStyle(pct: number): string {
  if (pct >= 90) return "bg-red-100 text-red-700";
  if (pct >= 75) return "bg-yellow-100 text-yellow-700";
  return "bg-green-100 text-green-700";
}

function capBarColor(pct: number): string {
  if (pct >= 90) return "bg-red-500";
  if (pct >= 75) return "bg-yellow-400";
  return "bg-green-500";
}

// ─── page ────────────────────────────────────────────────────────────────────

export default async function TeamsPage() {
  const { data: teams, error } = await supabase
    .from("teams")
    .select("id, university_name, conference, estimated_cap_space, active_payroll, logo_url")
    .order("active_payroll", { ascending: false });

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center px-4">
        <p className="text-sm text-red-500">Failed to load teams: {error.message}</p>
      </div>
    );
  }

  return (
    <>
      {/* ── Hero ───────────────────────────────────────────────────────────── */}
      <section className="bg-slate-900 py-14 px-4">
        <div className="mx-auto max-w-6xl">
          <span className="inline-block mb-4 rounded-full bg-slate-700 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-green-400">
            CFB 2026 · V1 Estimates
          </span>
          <h1
            className="text-4xl sm:text-5xl font-bold text-white leading-tight"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            University Cap Space Leaderboard
          </h1>
          <p className="mt-4 text-slate-300 text-base max-w-2xl leading-relaxed">
            Estimated NIL budget utilization ranked by active payroll. Figures are proprietary
            projections based on the C.F.O. V1.0 algorithm — not official financial disclosures.
          </p>
        </div>
      </section>

      {/* ── Grid ───────────────────────────────────────────────────────────── */}
      <div className="bg-gray-100 px-4 py-12">
        <div className="mx-auto max-w-6xl">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {teams.map((team, rank) => {
              const pct       = capUsedPct(team.active_payroll, team.estimated_cap_space);
              const remaining = team.estimated_cap_space - team.active_payroll;

              return (
                <Link
                  key={team.id}
                  href={`/teams/${team.id}`}
                  className="group block rounded-xl bg-white border border-gray-100 shadow-md p-5
                             transition-all duration-200 hover:-translate-y-1 hover:shadow-lg"
                >
                  {/* Rank + badge row */}
                  <div className="mb-3 flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                      #{rank + 1}
                    </span>
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${capBadgeStyle(pct)}`}>
                      {pct}% used
                    </span>
                  </div>

                  {/* Logo + name */}
                  <div className="flex items-center gap-3 mb-4">
                    {team.logo_url && (
                      <img
                        src={team.logo_url}
                        alt={`${team.university_name} logo`}
                        width={40}
                        height={40}
                        className="h-10 w-10 object-contain"
                      />
                    )}
                    <div>
                      <p className="text-lg font-semibold text-gray-900 group-hover:text-blue-700 transition-colors leading-tight">
                        {team.university_name}
                      </p>
                      <p className="text-xs text-gray-500">{team.conference}</p>
                    </div>
                  </div>

                  {/* Active payroll — heavy Oswald number */}
                  <p
                    className="text-3xl font-bold text-gray-900"
                    style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                  >
                    {formatCurrency(team.active_payroll)}
                  </p>
                  <p
                    className="mb-3 text-xs text-gray-500"
                    style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                  >
                    of {formatCurrency(team.estimated_cap_space)} cap
                  </p>

                  {/* Progress bar — native div so no Tremor client boundary needed */}
                  <div className="h-2 w-full rounded-full bg-gray-100 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${capBarColor(pct)}`}
                      style={{ width: `${Math.min(pct, 100)}%` }}
                    />
                  </div>

                  {/* Remaining */}
                  <p className="mt-2 text-xs text-gray-500">
                    <span
                      className="font-medium text-gray-700"
                      style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                    >
                      {formatCurrency(remaining)}
                    </span>{" "}
                    remaining
                  </p>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
