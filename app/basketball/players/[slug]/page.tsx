import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { formatCurrency } from "@/lib/utils";
import { BASE_URL } from "@/lib/constants";
import PlayerAvatar from "@/components/PlayerAvatar";
import { basketballPositionBadgeClass } from "@/lib/ui-helpers";

export const revalidate = 300;

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const { data } = await supabase
    .from("basketball_players")
    .select("name, position")
    .eq("slug", slug)
    .single();
  return {
    title: data
      ? `${data.name} — ${data.position ?? "Basketball"} | CFO Basketball`
      : "Player Profile | College Front Office",
    description: data
      ? `NIL valuation and profile for ${data.name}, ${data.position ?? "basketball player"}`
      : "Player NIL valuation profile",
    alternates: { canonical: `${BASE_URL}/basketball/players/${slug}` },
  };
}

// ─── types ───────────────────────────────────────────────────────────────────

interface Team {
  university_name: string;
  logo_url: string | null;
  market_multiplier: number | null;
  slug: string | null;
  conference: string | null;
}

interface Player {
  id: string;
  slug: string | null;
  name: string;
  position: string | null;
  star_rating: number | null;
  composite_score: number | null;
  class_year: string | null;
  experience_level: string | null;
  player_tag: string | null;
  cfo_valuation: number | null;
  is_public: boolean | null;
  is_override: boolean | null;
  rotation_status: string | null;
  rotation_rank: number | null;
  usage_rate: number | null;
  ppg: number | null;
  rpg: number | null;
  apg: number | null;
  per: number | null;
  nba_draft_projection: number | null;
  headshot_url: string | null;
  roster_status: string | null;
  acquisition_type: string | null;
  team_id: string | null;
  basketball_teams: Team | null;
}

interface NilOverride {
  total_value: number;
  years: number;
  annualized_value: number;
  source_name: string | null;
  source_url: string | null;
}

function formatDraftProjection(pick: number | null): string {
  if (!pick) return "Undrafted";
  if (pick <= 14) return `Lottery pick (#${pick})`;
  if (pick <= 30) return `First round (#${pick})`;
  return `Second round (#${pick})`;
}

// ─── page ────────────────────────────────────────────────────────────────────

interface PageProps {
  params: Promise<{ slug: string }>;
}

export default async function BasketballPlayerProfilePage({ params }: PageProps) {
  const { slug } = await params;

  const playerResp = await supabase
    .from("basketball_players")
    .select(
      "*, basketball_teams(university_name, logo_url, market_multiplier, slug, conference)"
    )
    .eq("slug", slug)
    .single();

  const playerId = playerResp.data?.id;
  const overridesResp = playerId
    ? await supabase
        .from("basketball_nil_overrides")
        .select("total_value, years, annualized_value, source_name, source_url")
        .eq("player_id", playerId)
    : { data: [] };

  if (playerResp.error || !playerResp.data) {
    return (
      <main className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
        <div className="text-center">
          <p className="text-6xl font-bold text-slate-700 mb-4">404</p>
          <p className="text-slate-400 mb-6">Player not found.</p>
          <Link
            href="/basketball/players"
            className="text-blue-400 hover:underline text-sm"
          >
            ← Back to Basketball Rankings
          </Link>
        </div>
      </main>
    );
  }

  const p = playerResp.data as unknown as Player;
  const nilOverrides = (overridesResp.data ?? []) as NilOverride[];

  const team = p.basketball_teams;
  const isPrivate = p.is_public === false;
  const hasStats = (p.usage_rate ?? 0) > 0;
  const mpg = p.usage_rate ? (p.usage_rate * 40).toFixed(1) : null;

  const hasOverrideData = p.is_override === true && nilOverrides.length > 0;
  const bestOverride = hasOverrideData
    ? nilOverrides.reduce((best, curr) =>
        curr.annualized_value > best.annualized_value ? curr : best
      )
    : null;
  const displayValuation =
    p.cfo_valuation ?? (bestOverride?.annualized_value ?? null);

  return (
    <main className="bg-gray-100">
      {!isPrivate && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "Person",
              name: p.name,
              description: `${p.position ?? "Player"} — College Basketball${team ? ` at ${team.university_name}` : ""}`,
              ...(team
                ? {
                    memberOf: {
                      "@type": "SportsTeam",
                      name: team.university_name,
                      sport: "Basketball",
                    },
                  }
                : {}),
              url: `${BASE_URL}/basketball/players/${p.slug ?? slug}`,
            }),
          }}
        />
      )}

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <div className="bg-slate-900 text-white px-6 py-8">
        <div className="mx-auto max-w-3xl">
          <div className="flex flex-col sm:flex-row sm:items-center gap-6">
            <PlayerAvatar
              headshot_url={p.headshot_url}
              name={p.name}
              position={p.position}
              size={120}
              className="shrink-0 border-2 border-slate-700"
            />

            <div className="flex-1">
              {/* Badges */}
              <div className="mb-2 flex flex-wrap gap-2">
                {p.position && (
                  <span
                    className={`rounded px-2.5 py-0.5 text-xs font-semibold uppercase tracking-widest ${basketballPositionBadgeClass(p.position)}`}
                  >
                    {p.position}
                  </span>
                )}
                {p.acquisition_type === "portal" && (
                  <span className="rounded px-2.5 py-0.5 text-xs font-semibold bg-blue-500/20 text-blue-300">
                    Transfer
                  </span>
                )}
                {p.acquisition_type === "portal_evaluating" && (
                  <span className="rounded px-2.5 py-0.5 text-xs font-semibold bg-amber-500/20 text-amber-300">
                    In Portal
                  </span>
                )}
                {p.roster_status === "departed_transfer" && (
                  <span className="rounded px-2.5 py-0.5 text-xs font-semibold bg-red-500/20 text-red-300">
                    Departed
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

              {/* Team */}
              {team && (
                <div className="mt-3 inline-flex items-center gap-2">
                  {team.logo_url && (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                      src={team.logo_url}
                      alt={`${team.university_name} logo`}
                      width={20}
                      height={20}
                      className="h-5 w-5 object-contain"
                    />
                  )}
                  <span className="text-sm text-slate-400">
                    {team.slug ? (
                      <Link
                        href={`/basketball/teams/${team.slug}`}
                        className="text-slate-200 font-medium hover:text-emerald-400 hover:underline transition-colors"
                      >
                        {team.university_name}
                      </Link>
                    ) : (
                      <span className="text-slate-200 font-medium">
                        {team.university_name}
                      </span>
                    )}
                    {team.conference && (
                      <span className="text-slate-500">
                        {" "}
                        · {team.conference}
                      </span>
                    )}
                  </span>
                </div>
              )}

              {/* Valuation */}
              <div className="mt-4">
                {isPrivate ? (
                  <p className="text-lg text-slate-500">
                    Financial Data Private
                  </p>
                ) : (
                  <div>
                    <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">
                      Est. NIL Valuation
                    </p>
                    <p
                      className="text-4xl sm:text-5xl font-bold text-emerald-400 leading-none"
                      style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                    >
                      {displayValuation != null
                        ? formatCurrency(displayValuation)
                        : "—"}
                    </p>
                    {hasOverrideData && bestOverride && (
                      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-400">
                        {bestOverride.years && (
                          <span>
                            {bestOverride.years} yr
                            {bestOverride.years !== 1 ? "s" : ""}
                          </span>
                        )}
                        {bestOverride.total_value &&
                          bestOverride.years !== 1 && (
                            <>
                              <span className="text-slate-600">·</span>
                              <span>
                                {formatCurrency(bestOverride.total_value)} total
                              </span>
                            </>
                          )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Body ─────────────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-3xl px-6 py-4 space-y-4">
        {/* ── Season stats ──────────────────────────────────────────────── */}
        {hasStats && !isPrivate && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
            <h2
              className="text-xs uppercase tracking-widest text-slate-400 mb-4"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              Season Stats
            </h2>
            <div className="grid grid-cols-3 sm:grid-cols-5 gap-4">
              {mpg && (
                <div>
                  <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">
                    MPG
                  </p>
                  <p
                    className="text-base font-bold text-slate-900 leading-none"
                    style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                  >
                    {mpg}
                  </p>
                </div>
              )}
              {p.ppg != null && (
                <div>
                  <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">
                    PPG
                  </p>
                  <p
                    className="text-base font-bold text-slate-900 leading-none"
                    style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                  >
                    {Number(p.ppg).toFixed(1)}
                  </p>
                </div>
              )}
              {p.rpg != null && (
                <div>
                  <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">
                    RPG
                  </p>
                  <p
                    className="text-base font-bold text-slate-900 leading-none"
                    style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                  >
                    {Number(p.rpg).toFixed(1)}
                  </p>
                </div>
              )}
              {p.apg != null && (
                <div>
                  <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">
                    APG
                  </p>
                  <p
                    className="text-base font-bold text-slate-900 leading-none"
                    style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                  >
                    {Number(p.apg).toFixed(1)}
                  </p>
                </div>
              )}
              {p.per != null && (
                <div>
                  <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">
                    PER
                  </p>
                  <p
                    className="text-base font-bold text-slate-900 leading-none"
                    style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                  >
                    {Number(p.per).toFixed(1)}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Recruiting profile — incoming players ───────────────────────── */}
        {!hasStats && !isPrivate && p.star_rating != null && p.star_rating > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
            <h2
              className="text-xs uppercase tracking-widest text-slate-400 mb-4"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              Recruiting Profile
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div>
                <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">
                  Rating
                </p>
                <span className="text-base text-yellow-400 leading-none">
                  {"★".repeat(Math.min(p.star_rating, 5))}
                </span>
              </div>
              {p.composite_score != null && (
                <div>
                  <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">
                    Composite
                  </p>
                  <p className="font-mono text-base font-bold text-slate-900 leading-none">
                    {Number(p.composite_score).toFixed(4)}
                  </p>
                </div>
              )}
              {p.nba_draft_projection != null && (
                <div>
                  <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">
                    NBA Draft
                  </p>
                  <p
                    className="text-base font-bold text-slate-900 leading-none"
                    style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                  >
                    {formatDraftProjection(p.nba_draft_projection)}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Methodology note ───────────────────────────────────────────── */}
        {!isPrivate && displayValuation != null && !hasOverrideData && (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <svg
              className="h-3.5 w-3.5 text-slate-300 shrink-0"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
                clipRule="evenodd"
              />
            </svg>
            <p>
              This valuation is generated by the C.F.O. Basketball V1 engine
              based on usage rate, PER, draft projection, and market factors.{" "}
              <Link
                href="/basketball/methodology"
                className="text-slate-500 hover:text-slate-700 underline transition-colors"
              >
                Learn more
              </Link>
            </p>
          </div>
        )}

        {/* ── Team link card ───────────────────────────────────────────────── */}
        {team && (
          <Link
            href={`/basketball/teams/${team.slug ?? ""}`}
            className="group block bg-white rounded-xl shadow-sm border border-gray-200 p-5 hover:border-slate-300 hover:shadow-md transition-all"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {team.logo_url && (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={team.logo_url}
                    alt={team.university_name}
                    width={40}
                    height={40}
                    className="h-10 w-10 object-contain shrink-0"
                  />
                )}
                <div>
                  <p
                    className="text-sm font-bold text-slate-900 uppercase tracking-wide group-hover:text-emerald-600 transition-colors"
                    style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                  >
                    {team.university_name}
                  </p>
                  <p className="text-xs text-slate-500">
                    View full roster and team valuation
                  </p>
                </div>
              </div>
              <svg
                className="h-5 w-5 text-slate-300 group-hover:text-emerald-500 transition-colors shrink-0"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
          </Link>
        )}
      </div>
    </main>
  );
}
