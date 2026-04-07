import Link from "next/link";
import Image from "next/image";
import { supabase } from "@/lib/supabase";
import { formatCurrency } from "@/lib/utils";
import { calculateCfoValuation } from "@/lib/valuation";
import PlayerAvatar from "@/components/PlayerAvatar";

export const revalidate = 300;

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { data } = await supabase.from("players").select("name, position").eq("id", id).single();
  return {
    title: data
      ? `${data.name} — ${data.position} | CFO NIL Valuation`
      : "Player Profile | College Front Office",
    description: data
      ? `NIL valuation and profile for ${data.name}, ${data.position}`
      : "Player NIL valuation profile",
  };
}

// ─── helpers ────────────────────────────────────────────────────────────────

function StarRating({ rating }: { rating: number | null }) {
  const count = Math.min(Math.max(rating ?? 0, 0), 5);
  if (count === 0) return <span className="text-slate-500 text-sm">Unrated</span>;
  return (
    <span className="text-2xl leading-none tracking-tight">
      <span className="text-yellow-400">{"★".repeat(count)}</span>
      <span className="text-slate-600">{"☆".repeat(5 - count)}</span>
    </span>
  );
}

// ─── constants ───────────────────────────────────────────────────────────────

const TAG_STYLES: Record<string, string> = {
  "College Athlete": "bg-blue-500 text-white",
  "High School Recruit": "bg-purple-500 text-white",
};

const EXPERIENCE_STYLES: Record<string, string> = {
  "Active Roster": "bg-blue-500 text-white",
  Portal: "bg-orange-500 text-white",
  "High School": "bg-emerald-500 text-white",
};

// ─── types ───────────────────────────────────────────────────────────────────

interface Team {
  university_name: string;
  logo_url: string | null;
  market_multiplier: number | null;
}

interface Player {
  id: string;
  name: string;
  position: string | null;
  star_rating: number | null;
  experience_level: string | null;
  player_tag: string | null;
  class_year: string | null;
  hs_grad_year: number | null;
  composite_score: number | null;
  high_school: string | null;
  cfo_valuation: number | null;
  reported_nil_deal: number | null;
  national_rank: number | null;
  is_on_depth_chart: boolean | null;
  depth_chart_rank: number | null;
  is_public: boolean | null;
  is_override: boolean | null;
  status: string | null;
  cfbd_id: number | null;
  headshot_url: string | null;
  nfl_draft_projection: number | null;
  production_score: number | null;
  total_followers: number | null;
  ig_followers: number | null;
  x_followers: number | null;
  tiktok_followers: number | null;
  ea_rating: number | null;
  teams: Team | null;
}

interface NilOverride {
  total_value: number;
  years: number;
  annualized_value: number;
  source_name: string | null;
  source_url: string | null;
}

// ─── page ────────────────────────────────────────────────────────────────────

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function PlayerProfilePage({ params }: PageProps) {
  const { id } = await params;

  const [playerResp, eventsResp, overridesResp] = await Promise.all([
    supabase
      .from("players")
      .select("*, teams(university_name, logo_url, market_multiplier)")
      .eq("id", id)
      .single(),
    supabase
      .from("player_events")
      .select("*")
      .eq("player_id", id)
      .order("event_date", { ascending: false }),
    supabase
      .from("nil_overrides")
      .select("total_value, years, annualized_value, source_name, source_url")
      .eq("player_id", id),
  ]);

  if (playerResp.error || !playerResp.data) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
        <div className="text-center">
          <p className="text-6xl font-bold text-slate-700 mb-4">404</p>
          <p className="text-slate-400 mb-6">Player not found.</p>
          <Link href="/players" className="text-blue-400 hover:underline text-sm">
            ← Back to Players
          </Link>
        </div>
      </main>
    );
  }

  const p = playerResp.data as unknown as Player;
  const events = eventsResp.data ?? [];
  const nilOverrides = (overridesResp.data ?? []) as NilOverride[];

  const team = p.teams;
  const isHS            = p.player_tag === "High School Recruit";
  const isPrivate       = p.is_public === false;
  const hasReported     = p.reported_nil_deal != null;

  // Override: is_override true + at least one nil_overrides row
  const hasOverrideData = p.is_override === true && nilOverrides.length > 0;
  // For display, use the highest annualized_value; show all sources
  const bestOverride = hasOverrideData
    ? nilOverrides.reduce((best, curr) =>
        curr.annualized_value > best.annualized_value ? curr : best
      )
    : null;
  // Defensive: override players always have a displayable valuation even if
  // cfo_valuation is NULL in the DB (e.g. before the Python engine is re-run).
  const displayValuation = p.cfo_valuation ?? (bestOverride?.annualized_value ?? null);
  const isIneligible    = displayValuation == null && !hasOverrideData && !isPrivate;
  const isOffDepthChart = isIneligible && p.player_tag === "College Athlete";

  // Compute V3.1 algorithm breakdown for eligible non-override players
  const breakdownResult =
    !hasOverrideData && p.cfo_valuation != null
      ? calculateCfoValuation(
          {
            player_tag:           p.player_tag,
            is_on_depth_chart:    p.is_on_depth_chart,
            depth_chart_rank:     p.depth_chart_rank,
            is_override:          p.is_override,
            position:             p.position,
            composite_score:      p.composite_score,
            nfl_draft_projection: p.nfl_draft_projection,
            production_score:     p.production_score,
            star_rating:          p.star_rating,
            class_year:           p.class_year,
            hs_grad_year:         p.hs_grad_year,
            total_followers:      p.total_followers,
            ig_followers:         p.ig_followers,
            x_followers:          p.x_followers,
            tiktok_followers:     p.tiktok_followers,
          },
          team?.market_multiplier ?? null,
          team?.university_name,
        )
      : null;
  const breakdown = breakdownResult?.breakdown ?? null;

  return (
    <main className="min-h-screen bg-gray-100">
      {!isPrivate && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "Person",
              name: p.name,
              description: `${p.position ?? "Player"} — ${
                isHS
                  ? `${p.star_rating ?? 0}★ High School Recruit${team ? ` committed to ${team.university_name}` : ""}`
                  : `College Athlete${team ? ` at ${team.university_name}` : ""}`
              }`,
              ...(team
                ? {
                    memberOf: {
                      "@type": "SportsTeam",
                      name: team.university_name,
                    },
                  }
                : {}),
              url: `https://collegefrontoffice.com/players/${p.id}`,
            }),
          }}
        />
      )}
      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <div className="bg-slate-900 text-white px-6 py-10">
        <div className="mx-auto max-w-4xl">
          <Link
            href="/players"
            className="inline-block mb-6 text-slate-400 hover:text-white text-sm transition-colors"
          >
            ← Back to Players
          </Link>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            {/* Left: identity */}
            <div>
              <PlayerAvatar
                headshot_url={p.headshot_url}
                name={p.name}
                position={p.position}
                size={80}
                className="mb-4 ring-2 ring-slate-700"
              />
              {/* Badges row */}
              <div className="mb-3 flex flex-wrap gap-2">
                {p.position && (
                  <span className="rounded px-2.5 py-0.5 text-xs font-semibold bg-slate-700 text-slate-300 uppercase tracking-widest">
                    {p.position}
                  </span>
                )}
                {p.player_tag && (
                  <span
                    className={`rounded px-2.5 py-0.5 text-xs font-semibold uppercase tracking-widest ${
                      TAG_STYLES[p.player_tag] ?? "bg-slate-600 text-white"
                    }`}
                  >
                    {p.player_tag}
                  </span>
                )}
                {p.experience_level && !isHS && (
                  <span
                    className={`rounded px-2.5 py-0.5 text-xs font-semibold uppercase tracking-widest ${
                      EXPERIENCE_STYLES[p.experience_level] ?? "bg-slate-600 text-white"
                    }`}
                  >
                    {p.experience_level}
                  </span>
                )}
                {isHS && p.class_year && (
                  <span className="rounded px-2.5 py-0.5 text-xs font-semibold uppercase tracking-widest bg-slate-700 text-slate-300">
                    Class of {p.class_year}
                  </span>
                )}
                {hasOverrideData && (
                  <span className="rounded px-2.5 py-0.5 text-xs font-semibold uppercase tracking-widest bg-emerald-600 text-white">
                    Verified Deal
                  </span>
                )}
              </div>

              {/* Name */}
              <h1
                className="text-4xl sm:text-5xl font-bold uppercase tracking-tight leading-none"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                {p.name}
              </h1>

              {/* Stars */}
              <div className="mt-3">
                <StarRating rating={p.star_rating} />
              </div>

              {/* Team commitment */}
              {team && (
                <div className="mt-4 inline-flex items-center gap-2 rounded-lg bg-slate-800 border border-slate-700 px-3 py-2">
                  {team.logo_url && (
                    <Image
                      src={team.logo_url}
                      alt={`${team.university_name} logo`}
                      width={20}
                      height={20}
                      className="h-5 w-5 object-contain"
                    />
                  )}
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wide">
                    {isHS ? "Committed to" : "Rostered at"}{" "}
                    <span className="text-white">{team.university_name}</span>
                  </span>
                </div>
              )}
            </div>

            {/* Right: valuation */}
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
                    This athlete has opted out of public financial estimations.
                  </p>
                </div>
              ) : isIneligible ? (
                isOffDepthChart ? (
                  <div>
                    <p className="text-xs uppercase tracking-widest text-slate-400 mb-1">
                      CFO Valuation
                    </p>
                    <p className="text-xl font-semibold text-slate-400 leading-none">
                      Not on Depth Chart
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      Valuations are calculated for active depth chart players only.
                    </p>
                  </div>
                ) : null
              ) : (
                <>
                  <div>
                    <p className="text-xs uppercase tracking-widest text-slate-400 mb-1">
                      {isHS ? "CFO Futures Value" : "CFO Baseline Value"}
                    </p>
                    <p
                      className="text-4xl sm:text-5xl font-bold text-white leading-none"
                      style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                    >
                      {displayValuation != null ? formatCurrency(displayValuation) : "—"}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {hasOverrideData
                        ? "Verified market deal — overrides algorithmic model."
                        : isHS
                          ? "Projected NIL value based on 247Sports Composite."
                          : "Algorithmic estimate based on position, production, and market."}
                    </p>
                  </div>

                  {/* Reported NIL deal — College Athletes only */}
                  {!isHS && (
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
                            {formatCurrency(p.reported_nil_deal!)}
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
                            No public NIL agreement on record.
                          </p>
                        </>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── Body ─────────────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-4xl px-6 py-10 space-y-6">
        {/* ── Row 1: Scouting Report + Market Cap ─────────────────────────── */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {/* Scouting Report */}
          <div className="bg-white rounded-xl shadow-md p-6">
            <h2
              className="text-xs uppercase tracking-widest text-slate-400 mb-4"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              Scouting Report
            </h2>
            <dl className="space-y-4">
              {/* Stars */}
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <dt className="text-xs text-slate-500 uppercase tracking-wide">Star Rating</dt>
                <dd>
                  <StarRating rating={p.star_rating} />
                </dd>
              </div>

              {isHS ? (
                <>
                  {p.national_rank != null && (
                    <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                      <dt className="text-xs text-slate-500 uppercase tracking-wide">
                        National Rank
                      </dt>
                      <dd
                        className="text-xl font-bold text-slate-900"
                        style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                      >
                        #{p.national_rank}
                      </dd>
                    </div>
                  )}
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <dt className="text-xs text-slate-500 uppercase tracking-wide">
                      Composite Score
                    </dt>
                    <dd className="font-mono text-sm font-semibold text-slate-900">
                      {p.composite_score != null ? p.composite_score.toFixed(4) : "—"}
                    </dd>
                  </div>
                  {p.class_year && (
                    <div className="flex items-center justify-between">
                      <dt className="text-xs text-slate-500 uppercase tracking-wide">Class Year</dt>
                      <dd className="text-sm font-semibold text-slate-900">{p.class_year}</dd>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <dt className="text-xs text-slate-500 uppercase tracking-wide">
                      Roster Status
                    </dt>
                    <dd>
                      {p.is_on_depth_chart ? (
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 text-emerald-700 px-3 py-0.5 text-xs font-semibold">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                          Active on Depth Chart
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 text-slate-500 px-3 py-0.5 text-xs font-semibold">
                          <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
                          Rotational / Bench
                        </span>
                      )}
                    </dd>
                  </div>
                  {p.ea_rating != null && p.ea_rating > 0 && (
                    <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                      <dt className="text-xs text-slate-500 uppercase tracking-wide">EA CFB 26 Rating</dt>
                      <dd className="flex items-center gap-2">
                        <span className="text-xl font-bold text-slate-900" style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
                          {p.ea_rating}
                        </span>
                        <span className="text-[10px] text-slate-400 uppercase">OVR</span>
                      </dd>
                    </div>
                  )}
                  {p.production_score != null && Number(p.production_score) > 0 && (
                    <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                      <dt className="text-xs text-slate-500 uppercase tracking-wide">Production Score</dt>
                      <dd className="flex items-center gap-2">
                        <span className="text-xl font-bold text-slate-900" style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
                          {Number(p.production_score).toFixed(1)}
                        </span>
                        <span className="text-[10px] text-slate-400 uppercase">/100</span>
                      </dd>
                    </div>
                  )}
                  {p.nfl_draft_projection != null && p.nfl_draft_projection > 0 && p.nfl_draft_projection < 500 && (
                    <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                      <dt className="text-xs text-slate-500 uppercase tracking-wide">Draft Projection</dt>
                      <dd>
                        <span className="text-xl font-bold text-slate-900" style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
                          #{p.nfl_draft_projection}
                        </span>
                        <span className="text-[10px] text-slate-400 ml-1 uppercase">overall</span>
                      </dd>
                    </div>
                  )}
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <dt className="text-xs text-slate-500 uppercase tracking-wide">Experience</dt>
                    <dd>
                      <span
                        className={`rounded px-2.5 py-0.5 text-xs font-semibold ${
                          EXPERIENCE_STYLES[p.experience_level ?? ""] ??
                          "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {p.experience_level ?? "—"}
                      </span>
                    </dd>
                  </div>
                  {p.high_school && (
                    <div className="flex items-center justify-between">
                      <dt className="text-xs text-slate-500 uppercase tracking-wide">
                        High School
                      </dt>
                      <dd className="text-sm font-medium text-slate-800 text-right max-w-[180px]">
                        {p.high_school}
                      </dd>
                    </div>
                  )}
                </>
              )}
            </dl>
          </div>

          {/* Market Cap Card */}
          <div className="bg-slate-900 text-white rounded-xl shadow-md p-6 border border-emerald-900/40">
            <h2
              className="text-xs uppercase tracking-widest text-slate-400 mb-5"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              {isHS ? "Futures Market Cap" : "Market Valuation"}
            </h2>

            {isPrivate ? (
              <div>
                <p className="text-xl font-semibold text-slate-400">Financial Data Private</p>
                <p className="mt-2 text-xs text-slate-500 leading-relaxed">
                  This athlete has opted out of public financial estimations and disclosures.
                </p>
              </div>
            ) : isIneligible ? (
              isOffDepthChart ? (
                <div>
                  <p className="text-xl font-semibold text-slate-400">Not on Active Depth Chart</p>
                  <p className="mt-2 text-xs text-slate-500 leading-relaxed">
                    This player is not currently on an active depth chart. C.F.O. valuations are
                    calculated for depth chart players only.
                  </p>
                </div>
              ) : (
                <p className="text-xl font-semibold text-slate-400">Valuation Not Available</p>
              )
            ) : (
              <div className="space-y-6">
                {/* Primary valuation */}
                <div>
                  <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">
                    {isHS ? "CFO Futures Value" : "CFO Baseline Value"}
                  </p>
                  <p
                    className="text-5xl font-bold text-emerald-400 leading-none"
                    style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                  >
                    {displayValuation != null ? formatCurrency(displayValuation) : "—"}
                  </p>
                  <p className="mt-2 text-xs text-slate-500 leading-relaxed">
                    {hasOverrideData
                      ? "Verified deal — overrides algorithmic estimate."
                      : isHS
                        ? "Projected value based on 247Sports Composite curve."
                        : "V3-Final algorithm: position × draft × production × market × experience."}
                  </p>
                </div>

                {/* Reported deal — College Athlete only */}
                {!isHS && (
                  <div className="border-t border-slate-700 pt-5">
                    <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">
                      Reported Market Deal
                    </p>
                    {hasReported ? (
                      <>
                        <p
                          className="text-4xl font-black text-white leading-none"
                          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                        >
                          {formatCurrency(p.reported_nil_deal!)}
                        </p>
                        <p className="mt-2 text-xs text-slate-500 leading-relaxed">
                          Publicly reported NIL or collective agreement.
                        </p>
                      </>
                    ) : (
                      <p className="text-xl font-semibold text-slate-500">Undisclosed</p>
                    )}
                  </div>
                )}

                {/* Composite breakdown — HS only */}
                {isHS && p.composite_score != null && (
                  <div className="border-t border-slate-700 pt-5 grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">
                        Composite
                      </p>
                      <p className="font-mono text-lg font-bold text-white">
                        {p.composite_score.toFixed(4)}
                      </p>
                    </div>
                    {p.national_rank != null && (
                      <div>
                        <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">
                          Natl. Rank
                        </p>
                        <p
                          className="text-lg font-bold text-white"
                          style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                        >
                          #{p.national_rank}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── Verified Market Report — override players only ─────────────── */}
        {hasOverrideData && bestOverride && (
          <div className="bg-emerald-950 border border-emerald-700/40 rounded-xl shadow-md p-6">
            <div className="flex flex-wrap items-center gap-3 mb-5">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-600 text-white px-3 py-1 text-xs font-bold uppercase tracking-widest">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                  <path
                    d="M2 6L5 9L10 3"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                Verified Market Report
              </span>
              <h2
                className="text-lg font-bold text-white"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                Reported NIL Deal
              </h2>
            </div>

            {/* Deal figures */}
            <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 mb-6">
              <div>
                <p className="text-xs uppercase tracking-widest text-emerald-400/70 mb-1">
                  Annualized Value
                </p>
                <p
                  className="text-3xl font-bold text-emerald-400 leading-none"
                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                >
                  {formatCurrency(bestOverride.annualized_value)}
                  <span className="text-sm font-normal text-emerald-500/70">/yr</span>
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-widest text-emerald-400/70 mb-1">
                  Total Value
                </p>
                <p
                  className="text-3xl font-bold text-white leading-none"
                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                >
                  {formatCurrency(bestOverride.total_value)}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-widest text-emerald-400/70 mb-1">
                  Contract Length
                </p>
                <p
                  className="text-3xl font-bold text-white leading-none"
                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                >
                  {bestOverride.years}
                  <span className="text-sm font-normal text-slate-400"> yr</span>
                </p>
              </div>
            </div>

            {/* All sources — distinguish verified articles from algorithmic valuations */}
            <div>
              <p className="text-xs uppercase tracking-widest text-emerald-400/70 mb-2">Sources</p>
              <div className="flex flex-wrap gap-2">
                {nilOverrides.map((ov, i) => {
                  const isAlgorithmic = (ov.source_name ?? "").includes("(algorithmic)") ||
                    (ov.source_name ?? "").includes("(pending verification)");
                  const hasRealUrl = ov.source_url != null && !isAlgorithmic;
                  const displayName = (ov.source_name ?? "Source")
                    .replace(" (algorithmic)", "")
                    .replace(" (pending verification)", "");

                  if (hasRealUrl) {
                    return (
                      <a
                        key={i}
                        href={ov.source_url!}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 rounded-full border border-emerald-600/40 bg-emerald-900/40 px-3 py-1 text-xs font-semibold text-emerald-300 hover:bg-emerald-800/60 transition-colors"
                      >
                        {displayName}
                        <svg
                          width="10"
                          height="10"
                          viewBox="0 0 10 10"
                          fill="none"
                          aria-hidden="true"
                        >
                          <path
                            d="M3 2H2a1 1 0 00-1 1v5a1 1 0 001 1h5a1 1 0 001-1V7M6 1h3m0 0v3m0-3L4 6"
                            stroke="currentColor"
                            strokeWidth="1.2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </a>
                    );
                  }

                  return (
                    <span
                      key={i}
                      className="inline-flex items-center gap-1.5 rounded-full border border-slate-600/40 bg-slate-800/40 px-3 py-1 text-xs font-semibold text-slate-400"
                    >
                      {displayName}
                    </span>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ── Off-depth-chart notice ───────────────────────────────────────── */}
        {isOffDepthChart && !breakdown && (
          <div className="bg-white rounded-xl shadow-md p-6 flex gap-3 items-start">
            <svg
              className="mt-0.5 h-4 w-4 shrink-0 text-slate-400"
              viewBox="0 0 20 20"
              fill="currentColor"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                clipRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
              />
            </svg>
            <div>
              <p className="text-xs font-semibold text-slate-700 mb-0.5">Not on Active Depth Chart</p>
              <p className="text-xs text-slate-400 leading-relaxed">
                This player is not currently listed on the active depth chart. C.F.O. Valuations are
                only calculated for players with confirmed roster spots. Check back after the next
                depth chart update.
              </p>
            </div>
          </div>
        )}

        {/* ── Algorithm Breakdown — non-override players with valuation ──────── */}
        {!hasOverrideData && breakdown && (
          <div className="bg-white rounded-xl shadow-md p-6">
            <div className="flex items-center justify-between mb-5">
              <h2
                className="text-xs uppercase tracking-widest text-slate-400"
                style={{ fontFamily: "var(--font-oswald), sans-serif" }}
              >
                V3.5 Algorithm Breakdown
              </h2>
              <Link
                href="/methodology"
                className="text-xs text-slate-400 hover:text-blue-600 transition-colors"
              >
                How this works →
              </Link>
            </div>

            <div className="divide-y divide-slate-100">
              {/* HS path: Composite Base + Position Premium */}
              {breakdown.isHsPath && breakdown.hsBaseValue && breakdown.hsPositionPremium && (
                <>
                  <div className="flex items-center justify-between py-3">
                    <div className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full shrink-0 bg-slate-300" />
                      <div>
                        <p className="text-xs font-semibold text-slate-700">Composite Base</p>
                        <p className="text-xs text-slate-400 mt-0.5">{breakdown.hsBaseValue.label}</p>
                      </div>
                    </div>
                    <span className="text-base font-bold text-slate-900 tabular-nums" style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
                      {formatCurrency(breakdown.hsBaseValue.value)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-3">
                    <div className="flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full shrink-0 ${breakdown.hsPositionPremium.multiplier >= 1 ? "bg-emerald-500" : "bg-amber-500"}`} />
                      <div>
                        <p className="text-xs font-semibold text-slate-700">Position Premium</p>
                        <p className="text-xs text-slate-400 mt-0.5">{breakdown.hsPositionPremium.label}</p>
                      </div>
                    </div>
                    <span className={`text-base font-bold tabular-nums ${breakdown.hsPositionPremium.multiplier >= 1 ? "text-emerald-600" : "text-amber-600"}`} style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
                      ×{breakdown.hsPositionPremium.multiplier}
                    </span>
                  </div>
                </>
              )}

              {/* College path: Position Base + Draft + Talent */}
              {!breakdown.isHsPath && breakdown.positionBase && breakdown.draftPremium && breakdown.talentModifier && (
                <>
                  <div className="flex items-center justify-between py-3">
                    <div className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full shrink-0 bg-slate-300" />
                      <div>
                        <p className="text-xs font-semibold text-slate-700">Position Base Value</p>
                        <p className="text-xs text-slate-400 mt-0.5">{breakdown.positionBase.label}</p>
                      </div>
                    </div>
                    <span className="text-base font-bold text-slate-900 tabular-nums" style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
                      {formatCurrency(breakdown.positionBase.value)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-3">
                    <div className="flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full shrink-0 ${breakdown.draftPremium.multiplier >= 1 ? "bg-emerald-500" : "bg-amber-500"}`} />
                      <div>
                        <p className="text-xs font-semibold text-slate-700">Draft Premium</p>
                        <p className="text-xs text-slate-400 mt-0.5">{breakdown.draftPremium.label}</p>
                      </div>
                    </div>
                    <span className={`text-base font-bold tabular-nums ${breakdown.draftPremium.multiplier >= 1 ? "text-emerald-600" : "text-amber-600"}`} style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
                      ×{breakdown.draftPremium.multiplier}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-3">
                    <div className="flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full shrink-0 ${breakdown.talentModifier.modifier >= 1 ? "bg-emerald-500" : "bg-amber-500"}`} />
                      <div>
                        <p className="text-xs font-semibold text-slate-700">Talent</p>
                        <p className="text-xs text-slate-400 mt-0.5">{breakdown.talentModifier.label}</p>
                      </div>
                    </div>
                    <span className={`text-base font-bold tabular-nums ${breakdown.talentModifier.modifier >= 1 ? "text-emerald-600" : "text-amber-600"}`} style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
                      ×{breakdown.talentModifier.modifier}
                    </span>
                  </div>
                </>
              )}

              {/* 4. Market Multiplier */}
              <div className="flex items-center justify-between py-3">
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full shrink-0 ${breakdown.marketMultiplier.multiplier >= 1 ? "bg-emerald-500" : "bg-amber-500"}`} />
                  <div>
                    <p className="text-xs font-semibold text-slate-700">Program Market</p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {breakdown.marketMultiplier.teamName}
                    </p>
                  </div>
                </div>
                <span
                  className={`text-base font-bold tabular-nums ${
                    breakdown.marketMultiplier.multiplier >= 1
                      ? "text-emerald-600"
                      : "text-amber-600"
                  }`}
                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                >
                  ×{breakdown.marketMultiplier.multiplier.toFixed(2)}
                </span>
              </div>

              {/* 5. Experience Multiplier */}
              <div className="flex items-center justify-between py-3">
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full shrink-0 ${breakdown.experienceMultiplier.multiplier >= 1 ? "bg-emerald-500" : "bg-amber-500"}`} />
                  <div>
                    <p className="text-xs font-semibold text-slate-700">Experience Premium</p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {breakdown.experienceMultiplier.label}
                    </p>
                  </div>
                </div>
                <span
                  className={`text-base font-bold tabular-nums ${
                    breakdown.experienceMultiplier.multiplier >= 1
                      ? "text-emerald-600"
                      : "text-amber-600"
                  }`}
                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                >
                  ×{breakdown.experienceMultiplier.multiplier}
                </span>
              </div>

              {/* 6. Depth Chart Role — college only */}
              {!breakdown.isHsPath && breakdown.depthChartRank && (
              <div className="flex items-center justify-between py-3">
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full shrink-0 ${breakdown.depthChartRank.multiplier >= 1 ? "bg-emerald-500" : "bg-amber-500"}`} />
                  <div>
                    <p className="text-xs font-semibold text-slate-700">Depth Chart Role</p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {breakdown.depthChartRank.label}
                    </p>
                  </div>
                </div>
                <span
                  className={`text-base font-bold tabular-nums ${
                    breakdown.depthChartRank.multiplier >= 1
                      ? "text-emerald-600"
                      : "text-amber-600"
                  }`}
                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                >
                  ×{breakdown.depthChartRank.multiplier}
                </span>
              </div>
              )}

              {/* Football subtotal */}
              <div className="flex items-center justify-between py-3 px-4 bg-slate-900 text-white rounded-lg mx-0">
                <div>
                  <p className="text-xs font-semibold text-slate-300">Football Value Subtotal</p>
                </div>
                <span
                  className="text-base font-bold text-emerald-400 tabular-nums"
                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                >
                  {formatCurrency(breakdown.footballValue)}
                </span>
              </div>

              {/* 6. Social Premium */}
              <div className="flex items-center justify-between py-3">
                <div>
                  <p className="text-xs font-semibold text-slate-700">Social Premium</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {breakdown.socialPremium.followers > 0
                      ? `${breakdown.socialPremium.followers.toLocaleString()} followers${
                          breakdown.socialPremium.capped ? " (capped at $150K)" : ""
                        }`
                      : "No social data"}
                  </p>
                  {(p.ig_followers || p.x_followers || p.tiktok_followers) && (
                    <div className="flex gap-3 mt-1.5">
                      {p.ig_followers ? (
                        <span className="text-[10px] text-slate-400">IG: {p.ig_followers.toLocaleString()}</span>
                      ) : null}
                      {p.x_followers ? (
                        <span className="text-[10px] text-slate-400">X: {p.x_followers.toLocaleString()}</span>
                      ) : null}
                      {p.tiktok_followers ? (
                        <span className="text-[10px] text-slate-400">TT: {p.tiktok_followers.toLocaleString()}</span>
                      ) : null}
                    </div>
                  )}
                </div>
                <span
                  className="text-base font-bold text-emerald-600 tabular-nums"
                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                >
                  +{formatCurrency(breakdown.socialPremium.premium)}
                </span>
              </div>

              {/* 7. Total */}
              <div className="flex items-center justify-between px-4 py-4 mt-1 mx-0 bg-emerald-50 border border-emerald-200 rounded-lg">
                <p
                  className="text-sm font-bold text-emerald-800 uppercase tracking-wide"
                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                >
                  CFO Valuation
                </p>
                <p
                  className="text-3xl font-black text-emerald-700 tabular-nums"
                  style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                >
                  {displayValuation != null
                    ? formatCurrency(displayValuation)
                    : formatCurrency(breakdown.total)}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ── Valuation Timeline ────────────────────────────────────────────── */}
        <div>
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
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                });
                const hasValuationChange = event.new_valuation != null;
                const hasPrevious = event.previous_valuation != null;
                const hasReportedDeal = event.reported_deal != null;

                return (
                  <div key={event.id} className="relative pl-8">
                    <span className="absolute -left-[25px] top-1 h-4 w-4 rounded-full border-4 border-white bg-blue-600 shadow-sm" />
                    <div className="bg-white rounded-xl shadow-md border border-gray-100 p-5">
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

        {/* ── Database Identity ─────────────────────────────────────────────── */}
        <div className="bg-white rounded-xl shadow-md border border-gray-100 p-6">
          <h2
            className="text-xs uppercase tracking-widest text-slate-400 mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Database Identity
          </h2>
          <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3 text-xs">
            <div>
              <dt className="text-slate-400 uppercase tracking-wide mb-1">Internal Player ID</dt>
              <dd className="font-mono text-slate-600 break-all">{p.id}</dd>
            </div>
            <div>
              <dt className="text-slate-400 uppercase tracking-wide mb-1">Class Year</dt>
              <dd className="font-mono text-slate-600">{p.class_year ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-400 uppercase tracking-wide mb-1">CFBD ID</dt>
              <dd className="font-mono text-slate-600">{p.cfbd_id ?? "—"}</dd>
            </div>
          </dl>
        </div>
      </div>
    </main>
  );
}
