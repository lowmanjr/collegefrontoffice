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
  if (position === "QB")                        return { label: "Franchise QB", value: "2.5×" };
  if (position === "LT" || position === "EDGE") return { label: "Premium Protector / Pass-Rusher", value: "1.5×" };
  if (["WR", "CB", "DT"].includes(position))   return { label: "Skill / Coverage / Interior", value: "1.2×" };
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
    .select("*, teams(university_name, logo_url), reported_nil_deal, status, is_public")
    .eq("id", id)
    .single();

  if (error) console.error("Supabase Error:", error);

  const { data: events } = await supabase
    .from("player_events")
    .select("*")
    .eq("player_id", id)
    .order("event_date", { ascending: false });

  if (error || !player) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
        <div className="text-center">
          <p className="text-6xl font-bold text-slate-700 mb-4">404</p>
          <p className="text-slate-400 mb-6">Player not found.</p>
          <Link href="/" className="text-blue-400 hover:underline text-sm">
            ← Back to Dashboard
          </Link>
        </div>
      </main>
    );
  }

  const posMult    = positionalMultiplier(player.position);
  const expMult    = experienceMultiplier(player.experience_level);
  const base       = baseRate(player.star_rating);
  const team       = player.teams as { university_name: string; logo_url?: string } | null;
  const isPrivate   = player.is_public === false;
  const hasReported = player.reported_nil_deal != null;
  const isFrozen    = !isPrivate && (player.status === "Medical Exemption" || player.status === "Inactive");

  return (
    <main className="min-h-screen bg-gray-100">

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <div className="bg-slate-900 text-white px-6 py-10">
        <div className="mx-auto max-w-4xl">

          <Link
            href="/"
            className="inline-block mb-6 text-slate-400 hover:text-white text-sm transition-colors"
          >
            ← Back to Dashboard
          </Link>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              {/* Position + experience badges */}
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

              {/* Commitment badge */}
              {team && (
                <div className="mt-4 inline-flex items-center gap-2 rounded-lg bg-slate-800 border border-slate-700 px-3 py-2">
                  {team.logo_url && (
                    <img
                      src={team.logo_url}
                      alt={`${team.university_name} logo`}
                      width={20}
                      height={20}
                      className="h-5 w-5 object-contain"
                    />
                  )}
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wide">
                    Committed to{" "}
                    <span className="text-white">{team.university_name}</span>
                  </span>
                </div>
              )}
            </div>

            {/* Valuation column — CFO Baseline + Reported Deal stacked */}
            <div className="mt-4 sm:mt-0 sm:text-right space-y-4 shrink-0">

              {isPrivate ? (
                <div>
                  <p className="text-xs uppercase tracking-widest text-slate-400 mb-1">
                    Financial Data
                  </p>
                  <p className="text-2xl font-semibold text-slate-400 leading-none">
                    Financial Data Private
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    This athlete or their representatives have opted out of public financial estimations and disclosures.
                  </p>
                </div>
              ) : isFrozen ? (
                <div>
                  <p className="text-xs uppercase tracking-widest text-slate-400 mb-1">
                    CFO Baseline Value
                  </p>
                  <p className="text-2xl font-semibold text-slate-400 leading-none">
                    Valuation Frozen
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Algorithmic valuation paused due to medical exemption or inactive status.
                  </p>
                </div>
              ) : (
                <>
                  {/* CFO Baseline */}
                  <div>
                    <p className="text-xs uppercase tracking-widest text-slate-400 mb-1">
                      CFO Baseline Value
                    </p>
                    <p
                      className="text-4xl sm:text-5xl font-bold text-white leading-none"
                      style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                    >
                      {formatCurrency(player.cfo_valuation)}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      Algorithmic value based on talent and positional scarcity.
                    </p>
                  </div>

                  {/* Reported Market Deal */}
                  <div>
                    <p className="text-xs uppercase tracking-widest text-slate-400 mb-1">
                      Reported Market Deal
                    </p>
                    {hasReported ? (
                      <>
                        <p
                          className="text-4xl sm:text-5xl font-black text-emerald-400 leading-none"
                          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                        >
                          {formatCurrency(player.reported_nil_deal)}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          Publicly reported third-party NIL or collective agreement.
                        </p>
                      </>
                    ) : (
                      <>
                        <p className="text-2xl font-semibold text-slate-500 leading-none">
                          Undisclosed
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          Publicly reported third-party NIL or collective agreement.
                        </p>
                      </>
                    )}
                  </div>
                </>
              )}

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

            <div className={`flex items-center justify-between ${player.high_school || team ? "border-b border-slate-100 pb-3" : ""}`}>
              <dt className="text-xs text-slate-500 uppercase tracking-wide">Star Rating</dt>
              <dd className="text-sm">{renderStars(player.star_rating)}</dd>
            </div>

            {player.high_school && (
              <div className={`flex items-center justify-between ${team ? "border-b border-slate-100 pb-3" : ""}`}>
                <dt className="text-xs text-slate-500 uppercase tracking-wide">High School</dt>
                <dd className="text-sm font-medium text-slate-800">{player.high_school}</dd>
              </div>
            )}

            {team && (
              <div className="flex items-center justify-between">
                <dt className="text-xs text-slate-500 uppercase tracking-wide">Commitment</dt>
                <dd className="flex items-center gap-1.5">
                  {team.logo_url && (
                    <img
                      src={team.logo_url}
                      alt={team.university_name}
                      width={16}
                      height={16}
                      className="h-4 w-4 object-contain"
                    />
                  )}
                  <span className="text-sm font-medium text-slate-800">{team.university_name}</span>
                </dd>
              </div>
            )}
          </dl>
        </div>

        {/* Market Valuation card — full width */}
        <div className="bg-slate-900 text-white rounded-xl shadow-md p-6 md:col-span-2">
          <h2
            className="text-xs uppercase tracking-widest text-slate-400 mb-5"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Market Valuation
          </h2>

          {isPrivate ? (
            <div className="flex flex-col gap-2">
              <p className="text-2xl font-semibold text-slate-400 leading-none">
                Financial Data Private
              </p>
              <p className="text-xs text-slate-500 leading-relaxed">
                This athlete or their representatives have opted out of public financial estimations and disclosures.
              </p>
            </div>
          ) : isFrozen ? (
            <div className="flex flex-col gap-2">
              <p className="text-2xl font-semibold text-slate-400 leading-none">
                Valuation Frozen
              </p>
              <p className="text-xs text-slate-500 leading-relaxed">
                Algorithmic valuation paused due to medical exemption or inactive status.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">

              {/* CFO Baseline */}
              <div className="border-b border-slate-700 pb-6 sm:border-b-0 sm:border-r sm:pb-0 sm:pr-6">
                <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">CFO Baseline Value</p>
                <p
                  className="text-4xl font-bold text-white leading-none"
                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                >
                  {formatCurrency(player.cfo_valuation)}
                </p>
                <p className="mt-2 text-xs text-slate-500 leading-relaxed">
                  Algorithmic value based on talent and positional scarcity.
                </p>
              </div>

              {/* Reported Deal */}
              <div className="sm:pl-6">
                <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Reported Market Deal</p>
                {hasReported ? (
                  <>
                    <p
                      className="text-4xl font-black text-emerald-400 leading-none"
                      style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                    >
                      {formatCurrency(player.reported_nil_deal)}
                    </p>
                    <p className="mt-2 text-xs text-slate-500 leading-relaxed">
                      Publicly reported third-party NIL or collective agreement.
                    </p>
                  </>
                ) : (
                  <>
                    <p className="text-2xl font-semibold text-slate-500 leading-none">Undisclosed</p>
                    <p className="mt-2 text-xs text-slate-500 leading-relaxed">
                      Publicly reported third-party NIL or collective agreement.
                    </p>
                  </>
                )}
              </div>

            </div>
          )}
        </div>

        {/* ── Valuation Timeline — full width ──────────────────────────── */}
        <div className="md:col-span-2">
          <h2
            className="mb-4 text-2xl font-bold text-slate-900 uppercase tracking-wide"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Valuation Timeline
          </h2>

          {isPrivate ? (
            <div className="bg-white rounded-xl shadow-md border border-gray-100 p-8 text-center">
              <p className="text-sm font-semibold text-slate-500">
                Timeline hidden due to privacy settings.
              </p>
            </div>
          ) : !events || events.length === 0 ? (
            <div className="bg-white rounded-xl shadow-md border border-gray-100 p-8 text-center">
              <p className="text-sm font-semibold text-slate-500">
                No historical valuation events logged for this player yet.
              </p>
            </div>
          ) : (
            <div className="relative border-l-2 border-slate-200 ml-3 space-y-8">
              {events.map((event) => {
                const date = new Date(event.event_date).toLocaleDateString("en-US", {
                  year: "numeric", month: "long", day: "numeric",
                });
                const hasValuationChange = event.new_valuation != null;
                const hasPrevious        = event.previous_valuation != null;
                const hasReportedDeal    = event.reported_deal != null;

                return (
                  <div key={event.id} className="relative pl-8">
                    {/* Timeline dot */}
                    <span className="absolute -left-[25px] top-1 h-4 w-4 rounded-full border-4 border-white bg-blue-600 shadow-sm" />

                    <div className="bg-white rounded-xl shadow-md border border-gray-100 p-5">
                      {/* Date + type row */}
                      <div className="flex flex-wrap items-center gap-3 mb-3">
                        <span className="text-xs font-bold uppercase tracking-widest text-slate-400">
                          {date}
                        </span>
                        <span
                          className="rounded bg-slate-900 text-white px-2 py-0.5 text-xs font-bold uppercase tracking-wide"
                          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                        >
                          {event.event_type}
                        </span>
                        {hasReportedDeal && (
                          <span className="rounded-full bg-emerald-100 text-emerald-700 px-2.5 py-0.5 text-xs font-bold">
                            Reported Deal: {formatCurrency(event.reported_deal)}
                          </span>
                        )}
                      </div>

                      {/* Valuation change */}
                      {hasValuationChange && (
                        <div className="flex items-center gap-2 mb-3">
                          {hasPrevious && (
                            <>
                              <span
                                className="text-xl font-bold text-slate-400 line-through"
                                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                              >
                                {formatCurrency(event.previous_valuation)}
                              </span>
                              <span className="text-slate-300 font-bold">→</span>
                            </>
                          )}
                          <span
                            className="text-2xl font-black text-gray-900"
                            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                          >
                            {formatCurrency(event.new_valuation)}
                          </span>
                        </div>
                      )}

                      {/* Description */}
                      {event.description && (
                        <p className="text-sm text-slate-500 leading-relaxed">
                          {event.description}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

      </div>
    </main>
  );
}
