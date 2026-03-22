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

function renderStars(rating: number) {
  const clamped = Math.min(Math.max(rating, 0), 5);
  return (
    <span className="tracking-tight text-3xl">
      <span className="text-yellow-400">{"★".repeat(clamped)}</span>
      <span className="text-slate-600">{"☆".repeat(5 - clamped)}</span>
    </span>
  );
}

// ─── positional multiplier label (mirrors V1.0 algorithm) ───────────────────

function positionalMultiplier(position: string): { label: string; value: string } {
  if (position === "QB")                          return { label: "Franchise QB", value: "2.5×" };
  if (position === "LT" || position === "EDGE")   return { label: "Premium Protector / Pass-Rusher", value: "1.5×" };
  if (["WR", "CB", "DT"].includes(position))      return { label: "Skill / Coverage / Interior", value: "1.2×" };
  return { label: "Standard", value: "1.0×" };
}

function experienceMultiplier(level: string): { label: string; value: string } {
  if (level === "Portal")        return { label: "Transfer Portal Starter", value: "3.0×" };
  if (level === "Active Roster") return { label: "Active Roster Starter", value: "2.0×" };
  return { label: "High School Recruit", value: "1.0×" };
}

function baseRate(stars: number): string {
  if (stars === 5) return "$100,000";
  if (stars === 4) return "$50,000";
  return "$25,000";
}

const EXPERIENCE_BADGE: Record<string, string> = {
  "Active Roster": "bg-blue-500 text-white",
  Portal:          "bg-orange-500 text-white",
  "High School":   "bg-emerald-500 text-white",
};

// ─── page ────────────────────────────────────────────────────────────────────

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function PlayerProfilePage({ params }: PageProps) {
  const { id } = await params;

  const { data: player, error } = await supabase
    .from("players")
    .select("*")
    .eq("id", id)
    .single();

  if (error || !player) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
        <div className="text-center">
          <p className="text-6xl font-bold text-slate-700 mb-4">404</p>
          <p className="text-slate-400 mb-6">Player not found.</p>
          <Link
            href="/"
            className="text-blue-400 hover:underline text-sm"
          >
            ← Back to Dashboard
          </Link>
        </div>
      </main>
    );
  }

  const posMult = positionalMultiplier(player.position);
  const expMult = experienceMultiplier(player.experience_level);
  const base    = baseRate(player.star_rating);

  return (
    <main className="min-h-screen bg-gray-100">

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <div className="bg-slate-900 text-white px-6 py-10">
        <div className="mx-auto max-w-4xl">

          {/* Back link */}
          <Link
            href="/"
            className="inline-block mb-6 text-slate-400 hover:text-white text-sm transition-colors"
          >
            ← Back to Dashboard
          </Link>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              {/* Badges */}
              <div className="mb-3 flex flex-wrap gap-2">
                <span className="rounded px-2.5 py-0.5 text-xs font-semibold bg-slate-700 text-slate-300 uppercase tracking-widest">
                  {player.position}
                </span>
                <span
                  className={`rounded px-2.5 py-0.5 text-xs font-semibold uppercase tracking-widest ${
                    EXPERIENCE_BADGE[player.experience_level] ?? "bg-slate-600 text-white"
                  }`}
                >
                  {player.experience_level}
                </span>
              </div>

              {/* Name */}
              <h1
                className="text-4xl sm:text-5xl font-bold uppercase tracking-tight leading-none"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                {player.name}
              </h1>

              {/* Stars */}
              <div className="mt-3">{renderStars(player.star_rating)}</div>
            </div>

            {/* CFO Valuation hero number */}
            <div className="mt-4 sm:mt-0 sm:text-right">
              <p className="text-xs uppercase tracking-widest text-slate-400 mb-1">
                C.F.O. Valuation
              </p>
              <p
                className="text-5xl sm:text-6xl font-bold text-white leading-none"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                {formatCurrency(player.cfo_valuation)}
              </p>
              <p className="mt-1 text-xs text-slate-500">V1.0 Algorithm</p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Body ─────────────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-4xl px-6 py-10 grid grid-cols-1 gap-6 md:grid-cols-2">

        {/* Algorithm Breakdown card */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <h2
            className="text-xs uppercase tracking-widest text-slate-400 mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Algorithm Breakdown
          </h2>
          <dl className="space-y-4">

            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <dt className="text-xs text-slate-500 uppercase tracking-wide">Base Rate</dt>
                <dd className="text-sm text-slate-700 mt-0.5">{player.star_rating}-Star Recruit</dd>
              </div>
              <span
                className="text-xl font-bold text-slate-900"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                {base}
              </span>
            </div>

            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <dt className="text-xs text-slate-500 uppercase tracking-wide">Positional Scarcity</dt>
                <dd className="text-sm text-slate-700 mt-0.5">{posMult.label}</dd>
              </div>
              <span
                className="text-xl font-bold text-slate-900"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                {posMult.value}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <dt className="text-xs text-slate-500 uppercase tracking-wide">Experience Premium</dt>
                <dd className="text-sm text-slate-700 mt-0.5">{expMult.label}</dd>
              </div>
              <span
                className="text-xl font-bold text-slate-900"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                {expMult.value}
              </span>
            </div>
          </dl>
        </div>

        {/* Player Status card */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <h2
            className="text-xs uppercase tracking-widest text-slate-400 mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Player Status
          </h2>
          <dl className="space-y-4">

            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <dt className="text-xs text-slate-500 uppercase tracking-wide">Position</dt>
              <dd>
                <span className="rounded bg-slate-900 text-white px-2.5 py-0.5 text-xs font-semibold uppercase">
                  {player.position}
                </span>
              </dd>
            </div>

            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <dt className="text-xs text-slate-500 uppercase tracking-wide">Status</dt>
              <dd>
                <span
                  className={`rounded px-2.5 py-0.5 text-xs font-semibold ${
                    EXPERIENCE_BADGE[player.experience_level] ?? "bg-slate-100 text-slate-600"
                  }`}
                >
                  {player.experience_level}
                </span>
              </dd>
            </div>

            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <dt className="text-xs text-slate-500 uppercase tracking-wide">Star Rating</dt>
              <dd className="text-sm">{renderStars(player.star_rating)}</dd>
            </div>

            {player.high_school && (
              <div className="flex items-center justify-between">
                <dt className="text-xs text-slate-500 uppercase tracking-wide">High School</dt>
                <dd className="text-sm font-medium text-slate-800">{player.high_school}</dd>
              </div>
            )}
          </dl>
        </div>

        {/* Valuation context card — full width */}
        <div className="bg-slate-900 text-white rounded-xl shadow-md p-6 md:col-span-2">
          <h2
            className="text-xs uppercase tracking-widest text-slate-400 mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Market Valuation
          </h2>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <p className="text-slate-400 text-sm max-w-lg">
              This valuation is calculated by the C.F.O. V1.0 algorithm, which weights positional
              scarcity and experience premium against a star-rating base rate to approximate
              fair-market NIL compensation.
            </p>
            <p
              className="text-5xl font-bold text-white shrink-0"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              {formatCurrency(player.cfo_valuation)}
            </p>
          </div>
        </div>

      </div>
    </main>
  );
}
