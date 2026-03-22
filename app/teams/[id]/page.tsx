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

// ─── page ────────────────────────────────────────────────────────────────────

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function TeamProfilePage({ params }: PageProps) {
  const { id } = await params;

  const { data: team, error } = await supabase
    .from("teams")
    .select("id, university_name, conference, logo_url, ncaa_revenue_share, football_allocation_pct, nil_collective_tier")
    .eq("id", id)
    .single();

  const { data: players } = await supabase
    .from("players")
    .select("id, name, position, star_rating, cfo_valuation, reported_nil_deal")
    .eq("team_id", id)
    .order("cfo_valuation", { ascending: false });

  if (error || !team) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
        <div className="text-center">
          <p className="text-6xl font-bold text-slate-700 mb-4">404</p>
          <p className="text-slate-400 mb-6">Team not found.</p>
          <Link href="/teams" className="text-blue-400 hover:underline text-sm">
            ← Back to Leaderboard
          </Link>
        </div>
      </main>
    );
  }

  // Derived financials with fallbacks
  const revenueShare      = team.ncaa_revenue_share      ?? 20_500_000;
  const allocationPct     = team.football_allocation_pct ?? 0.75;
  const footballAlloc     = Math.round(revenueShare * allocationPct);
  const collectiveTier    = team.nil_collective_tier     ?? "Tier 1: High Net-Worth Backers";

  return (
    <div className="min-h-screen bg-gray-100">

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="bg-slate-900 text-white pt-10 pb-20 px-4">
        <div className="mx-auto max-w-6xl">

          <Link
            href="/teams"
            className="inline-block mb-8 text-slate-400 hover:text-white text-sm transition-colors"
          >
            ← Back to Leaderboard
          </Link>

          <div className="flex flex-col sm:flex-row sm:items-center gap-6">
            {team.logo_url && (
              <img
                src={team.logo_url}
                alt={`${team.university_name} logo`}
                width={96}
                height={96}
                className="h-24 w-24 object-contain shrink-0"
              />
            )}
            <div>
              <h1
                className="text-5xl sm:text-6xl font-bold uppercase tracking-tight leading-none text-white"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                {team.university_name}
              </h1>
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <span className="rounded px-2.5 py-0.5 text-xs font-semibold uppercase tracking-widest bg-slate-700 text-slate-300">
                  {team.conference}
                </span>
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* ── Financial Dashboard ───────────────────────────────────────────── */}
      <div className="mx-auto max-w-6xl px-4 -mt-8 relative z-10 space-y-6 pb-12">

        {/* 3-column stat cards */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">

          {/* Card 1 — Institutional Rev Share */}
          <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100">
            <p
              className="text-xs uppercase tracking-widest text-slate-400 mb-2"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              Institutional Rev Share
            </p>
            <p
              className="text-4xl font-bold text-gray-900 leading-none"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              {formatCurrency(revenueShare)}
            </p>
            <p className="mt-2 text-xs text-gray-400">NCAA House settlement allocation</p>
          </div>

          {/* Card 2 — Est. Football Allocation */}
          <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100">
            <p
              className="text-xs uppercase tracking-widest text-slate-400 mb-2"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              Est. Football Allocation
            </p>
            <p
              className="text-4xl font-bold text-gray-900 leading-none"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              {formatCurrency(footballAlloc)}
            </p>
            <p className="mt-2 text-xs text-gray-400">
              {Math.round(allocationPct * 100)}% of institutional share
            </p>
          </div>

          {/* Card 3 — NIL Collective Tier */}
          <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100">
            <p
              className="text-xs uppercase tracking-widest text-slate-400 mb-2"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              NIL Collective Tier
            </p>
            <p
              className="text-2xl font-bold text-violet-600 leading-snug"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              {collectiveTier}
            </p>
            <p className="mt-2 text-xs text-gray-400">Booster collective classification</p>
          </div>

        </div>

        {/* ── Roster ────────────────────────────────────────────────────── */}
        <section>
          <div className="mb-4 flex items-baseline justify-between">
            <h2
              className="text-2xl font-bold text-slate-900 uppercase tracking-wide"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              Current Roster &amp; Commits
            </h2>
            {players && players.length > 0 && (
              <span className="text-sm text-gray-400">{players.length} players</span>
            )}
          </div>

          {!players || players.length === 0 ? (
            <div className="bg-white rounded-xl shadow-md border border-gray-100 p-10 text-center">
              <p className="text-sm font-semibold text-slate-500">No commitments found for this university yet.</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-md border border-gray-100 overflow-hidden">

              {/* Table header */}
              <div className="grid grid-cols-[1fr_auto_auto_auto_auto] bg-slate-900 px-5 py-3 text-xs font-semibold uppercase tracking-widest text-slate-400">
                <span>Player</span>
                <span className="text-center px-4">Pos</span>
                <span className="text-center px-4">Stars</span>
                <span className="text-right px-4">CFO Baseline</span>
                <span className="text-right">Reported Deal</span>
              </div>

              {/* Rows */}
              {players.map((player, idx) => (
                <Link
                  key={player.id}
                  href={`/players/${player.id}`}
                  className={`grid grid-cols-[1fr_auto_auto_auto_auto] items-center px-5 py-4 transition-colors hover:bg-slate-50 ${
                    idx !== players.length - 1 ? "border-b border-gray-100" : ""
                  }`}
                >
                  {/* Name + rank */}
                  <span className="flex items-center gap-3">
                    <span className="text-xs font-bold text-slate-300 w-5 shrink-0">
                      {idx + 1}
                    </span>
                    <span className="font-semibold text-gray-900 group-hover:text-blue-700 transition-colors">
                      {player.name}
                    </span>
                  </span>

                  {/* Position */}
                  <span className="px-4 text-center">
                    <span className="rounded bg-slate-900 text-white px-2 py-0.5 text-xs font-semibold uppercase">
                      {player.position}
                    </span>
                  </span>

                  {/* Stars */}
                  <span className="px-4 text-center tracking-tight">
                    <span className="text-yellow-500">
                      {"★".repeat(Math.min(Math.max(player.star_rating, 0), 5))}
                    </span>
                    <span className="text-gray-300">
                      {"☆".repeat(5 - Math.min(Math.max(player.star_rating, 0), 5))}
                    </span>
                  </span>

                  {/* CFO Baseline */}
                  <span
                    className="px-4 text-right font-bold text-gray-900"
                    style={{ fontFamily: "var(--font-oswald), sans-serif", fontSize: "1.05rem", letterSpacing: "0.02em" }}
                  >
                    {formatCurrency(player.cfo_valuation)}
                  </span>

                  {/* Reported Deal */}
                  {player.reported_nil_deal != null ? (
                    <span
                      className="text-right font-black text-emerald-600"
                      style={{ fontFamily: "var(--font-oswald), sans-serif", fontSize: "1.05rem", letterSpacing: "0.02em" }}
                    >
                      {formatCurrency(player.reported_nil_deal)}
                    </span>
                  ) : (
                    <span className="text-right text-sm text-slate-400">
                      Undisclosed
                    </span>
                  )}
                </Link>
              ))}
            </div>
          )}
        </section>

      </div>
    </div>
  );
}
