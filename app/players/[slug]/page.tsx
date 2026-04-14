import Link from "next/link";
import Image from "next/image";
import { supabase } from "@/lib/supabase";
import { formatCurrency } from "@/lib/utils";
import { BASE_URL } from "@/lib/constants";
import PlayerAvatar from "@/components/PlayerAvatar";

export const revalidate = 300;

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const { data } = await supabase.from("players").select("name, position").eq("slug", slug).single();
  return {
    title: data
      ? `${data.name} — ${data.position} | CFO NIL Valuation`
      : "Player Profile | College Front Office",
    description: data
      ? `NIL valuation and profile for ${data.name}, ${data.position}`
      : "Player NIL valuation profile",
    alternates: {
      canonical: `${BASE_URL}/players/${slug}`,
    },
  };
}

// ─── types ───────────────────────────────────────────────────────────────────

interface Team {
  university_name: string;
  logo_url: string | null;
  market_multiplier: number | null;
  slug: string | null;
}

interface Player {
  id: string;
  slug: string | null;
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
  team_id: string | null;
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
  params: Promise<{ slug: string }>;
}

export default async function PlayerProfilePage({ params }: PageProps) {
  const { slug } = await params;

  const playerResp = await supabase
    .from("players")
    .select("*, teams(university_name, logo_url, market_multiplier, slug)")
    .eq("slug", slug)
    .single();

  const playerId = playerResp.data?.id;
  const overridesResp = playerId
    ? await supabase
        .from("nil_overrides")
        .select("total_value, years, annualized_value, source_name, source_url")
        .eq("player_id", playerId)
    : { data: [] };

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
  const nilOverrides = (overridesResp.data ?? []) as NilOverride[];

  const team = p.teams;
  const isHS            = p.player_tag === "High School Recruit";
  const isPrivate       = p.is_public === false;

  const hasOverrideData = p.is_override === true && nilOverrides.length > 0;
  const bestOverride = hasOverrideData
    ? nilOverrides.reduce((best, curr) =>
        curr.annualized_value > best.annualized_value ? curr : best
      )
    : null;
  const displayValuation = p.cfo_valuation ?? (bestOverride?.annualized_value ?? null);
  const isIneligible    = displayValuation == null && !hasOverrideData && !isPrivate;
  const isOffDepthChart = isIneligible && p.player_tag === "College Athlete";

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
              url: `https://collegefrontoffice.com/players/${p.slug ?? slug}`,
            }),
          }}
        />
      )}

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <div className="bg-slate-900 text-white px-6 py-8">
        <div className="mx-auto max-w-3xl">
          <div className="flex flex-col sm:flex-row sm:items-center gap-6">
            {/* Avatar */}
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
                  <span className="rounded px-2.5 py-0.5 text-xs font-semibold bg-slate-700 text-slate-300 uppercase tracking-widest">
                    {p.position}
                  </span>
                )}
                {isHS && (p.hs_grad_year || p.class_year) && (
                  <span className="rounded px-2.5 py-0.5 text-xs font-semibold uppercase tracking-widest bg-slate-700 text-slate-300">
                    Class of {p.hs_grad_year ?? p.class_year}
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
                    <Image
                      src={team.logo_url}
                      alt={`${team.university_name} logo`}
                      width={20}
                      height={20}
                      className="h-5 w-5 object-contain"
                    />
                  )}
                  <span className="text-sm text-slate-400">
                    {isHS ? "Committed to" : ""}{" "}
                    <span className="text-slate-200 font-medium">{team.university_name}</span>
                  </span>
                </div>
              )}

              {/* Valuation */}
              <div className="mt-4">
                {isPrivate ? (
                  <p className="text-lg text-slate-500">Financial Data Private</p>
                ) : isIneligible ? (
                  <div>
                    <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">CFO Valuation</p>
                    <p className="text-lg text-slate-500 italic">Pending</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">
                      {hasOverrideData ? "NIL Valuation" : isHS ? "CFO Futures Value" : "CFO Valuation"}
                    </p>
                    <p
                      className="text-4xl sm:text-5xl font-bold text-emerald-400 leading-none"
                      style={{ fontFamily: "var(--font-oswald), sans-serif" }}
                    >
                      {displayValuation != null ? formatCurrency(displayValuation) : "—"}
                    </p>
                    {/* Contract details for override players */}
                    {hasOverrideData && bestOverride && (
                      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-400">
                        {bestOverride.years && (
                          <span>{bestOverride.years} yr{bestOverride.years !== 1 ? "s" : ""}</span>
                        )}
                        {bestOverride.years && bestOverride.total_value && bestOverride.years !== 1 && (
                          <>
                            <span className="text-slate-600">·</span>
                            <span>{formatCurrency(bestOverride.total_value)} total</span>
                          </>
                        )}
                        {nilOverrides.some(ov => ov.source_url || ov.source_name) && (
                          <>
                            <span className="text-slate-600">·</span>
                            {nilOverrides.map((ov, i) => {
                              const displayName = (ov.source_name ?? "")
                                .replace(" (algorithmic)", "")
                                .replace(" (pending verification)", "");
                              if (!displayName) return null;
                              const isAlgorithmic = (ov.source_name ?? "").includes("(algorithmic)") ||
                                (ov.source_name ?? "").includes("(pending verification)");
                              const hasRealUrl = ov.source_url != null && !isAlgorithmic;

                              if (hasRealUrl) {
                                return (
                                  <a key={i} href={ov.source_url!} target="_blank" rel="noopener noreferrer"
                                    className="text-slate-400 hover:text-white underline transition-colors">
                                    {displayName}
                                  </a>
                                );
                              }
                              return <span key={i}>{displayName}</span>;
                            })}
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
        {/* ── Recruiting Profile — HS recruits only ────────────────────────── */}
        {isHS && !isPrivate && !isIneligible && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
            <h2 className="text-xs uppercase tracking-widest text-slate-400 mb-4"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
              Recruiting Profile
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              {p.star_rating != null && p.star_rating > 0 && (
                <div>
                  <p className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">Rating</p>
                  <span className="text-base text-yellow-400 leading-none">{"★".repeat(Math.min(p.star_rating, 5))}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Methodology note — HS recruits ──────────────────────────────── */}
        {isHS && !isPrivate && !isIneligible && displayValuation != null && (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <svg className="h-3.5 w-3.5 text-slate-300 shrink-0" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
            </svg>
            <p>
              This futures valuation is generated by the C.F.O. V3.6b engine based on recruiting profile and position premium.{" "}
              <Link href="/methodology" className="text-slate-500 hover:text-slate-700 underline transition-colors">
                Learn more
              </Link>
            </p>
          </div>
        )}

        {/* ── Methodology note — regular college athletes ──────────────────── */}
        {!isPrivate && !isIneligible && !hasOverrideData && !isHS && displayValuation != null && (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <svg className="h-3.5 w-3.5 text-slate-300 shrink-0" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
            </svg>
            <p>
              This valuation is generated by the C.F.O. V3.5 engine based on position, production, draft projection, and market factors.{" "}
              <Link href="/methodology" className="text-slate-500 hover:text-slate-700 underline transition-colors">
                Learn more
              </Link>
            </p>
          </div>
        )}

        {/* ── Team link card ───────────────────────────────────────────────── */}
        {team && (
          <Link
            href={`/teams/${team.slug ?? ""}`}
            className="group block bg-white rounded-xl shadow-sm border border-gray-200 p-5 hover:border-slate-300 hover:shadow-md transition-all"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {team.logo_url && (
                  <Image
                    src={team.logo_url}
                    alt={team.university_name}
                    width={40}
                    height={40}
                    className="h-10 w-10 object-contain shrink-0"
                  />
                )}
                <div>
                  <p className="text-sm font-bold text-slate-900 uppercase tracking-wide group-hover:text-emerald-600 transition-colors"
                    style={{ fontFamily: "var(--font-oswald), sans-serif" }}>
                    {team.university_name}
                  </p>
                  <p className="text-xs text-slate-500">View full roster and team valuation</p>
                </div>
              </div>
              <svg className="h-5 w-5 text-slate-300 group-hover:text-emerald-500 transition-colors shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z" clipRule="evenodd" />
              </svg>
            </div>
          </Link>
        )}
      </div>
    </main>
  );
}
