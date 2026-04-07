// V3.1 — Must stay in sync with VALUATION_ENGINE.md and python_engine/calculate_cfo_valuations.py

// ─── Position base values ────────────────────────────────────────────────────
// VALUATION_ENGINE.md §3.2

const POSITION_BASE_VALUES: Record<string, number> = {
  QB: 1_200_000,
  OT: 800_000,
  EDGE: 700_000,
  DE: 700_000,
  DT: 500_000,
  WR: 550_000,
  CB: 500_000,
  OG: 475_000,
  C: 475_000,
  IOL: 475_000,
  OL: 475_000,
  S: 450_000,
  RB: 400_000,
  TE: 325_000,
  LB: 325_000,
  K: 100_000,
  P: 100_000,
  ATH: 400_000,
  LS: 100_000,
};

const POSITION_LABELS: Record<string, string> = {
  QB: "Quarterback",
  OT: "Offensive Tackle",
  EDGE: "Edge Rusher",
  DE: "Defensive End",
  DT: "Defensive Tackle",
  WR: "Wide Receiver",
  CB: "Cornerback",
  OG: "Offensive Guard",
  C: "Center",
  IOL: "Interior O-Line",
  OL: "Offensive Line",
  S: "Safety",
  RB: "Running Back",
  TE: "Tight End",
  LB: "Linebacker",
  K: "Kicker",
  P: "Punter",
  ATH: "Athlete",
  LS: "Long Snapper",
};

const DEFAULT_BASE_VALUE = 400_000;
const SOCIAL_CAP = 150_000;
const CURRENT_YEAR = 2026; // Fall season — update annually

// ─── Eligibility ─────────────────────────────────────────────────────────────

/**
 * Returns true if this player should receive a valuation.
 * College athletes: must be on an active depth chart.
 * HS recruits: must be 4★ or 5★.
 * isOverride: if true, always returns true — verified deals bypass the eligibility gate.
 * VALUATION_ENGINE.md §3.0
 */
export function isEligibleForValuation(
  playerTag: string | null,
  isOnDepthChart: boolean | null,
  starRating: number | null,
  isOverride?: boolean,
): boolean {
  if (isOverride === true) return true;
  const tag = (playerTag ?? "").trim();
  if (tag === "College Athlete") {
    return isOnDepthChart === true;
  }
  if (tag === "High School Recruit") {
    return (starRating ?? 0) >= 4;
  }
  return true;
}

// ─── Component functions ─────────────────────────────────────────────────────

/** Returns the position label and its base dollar value. VALUATION_ENGINE.md §3.2 */
export function getPositionBaseValue(position: string | null): { label: string; value: number } {
  if (!position) return { label: "Unknown Position", value: DEFAULT_BASE_VALUE };
  const key = position.toUpperCase().trim();
  return {
    label: POSITION_LABELS[key] ?? key,
    value: POSITION_BASE_VALUES[key] ?? DEFAULT_BASE_VALUE,
  };
}

/**
 * Returns draft premium multiplier.
 * Sentinel values: null, 0, >=500 → 1.0 (neutral — no data).
 * Key change from V3: null → 1.0 instead of 0.75.
 * VALUATION_ENGINE.md §3.3
 */
export function getDraftPremium(nflDraftProjection: number | null): {
  label: string;
  multiplier: number;
} {
  if (nflDraftProjection == null || nflDraftProjection === 0 || nflDraftProjection >= 500) {
    return { label: "No Projection", multiplier: 1.0 };
  }
  if (nflDraftProjection <= 5) return { label: "Top 5 Pick", multiplier: 2.5 };
  if (nflDraftProjection <= 15) return { label: "First Round (6–15)", multiplier: 1.9 };
  if (nflDraftProjection <= 32) return { label: "Late First Round", multiplier: 1.5 };
  if (nflDraftProjection <= 64) return { label: "Second Round", multiplier: 1.25 };
  if (nflDraftProjection <= 100) return { label: "Day 2 Draft Stock", multiplier: 1.1 };
  if (nflDraftProjection <= 180) return { label: "Day 3 Draft Stock", multiplier: 1.0 };
  return { label: "Late Round / Fringe", multiplier: 0.9 };
}

/**
 * Three-tier talent assessment.
 * 1. production_score > 0  → production tiers (primary signal).
 * 2. ea_rating exists      → EA OVR tiers (video game fallback).
 * 3. star_rating           → star proxy (last resort).
 * VALUATION_ENGINE.md §3.4
 */
export function getTalentModifier(
  productionScore: number | null,
  starRating: number | null,
  eaRating: number | null = null,
): { label: string; modifier: number; usedProduction: boolean } {
  const hasProduction = productionScore != null && productionScore > 0;

  if (hasProduction) {
    const ps = productionScore!;
    const score = Math.round(ps);
    if (ps >= 90) return { label: `Production Score ${score}`, modifier: 1.4, usedProduction: true };
    if (ps >= 75) return { label: `Production Score ${score}`, modifier: 1.2, usedProduction: true };
    if (ps >= 50) return { label: `Production Score ${score}`, modifier: 1.0, usedProduction: true };
    if (ps >= 25) return { label: `Production Score ${score}`, modifier: 0.65, usedProduction: true };
    return { label: `Production Score ${score}`, modifier: 0.4, usedProduction: true };
  }

  // Fallback 1: EA rating (calibrated to match production tiers)
  if (eaRating != null && eaRating > 0) {
    if (eaRating >= 90) return { label: `EA Rating ${eaRating} (fallback)`, modifier: 1.4, usedProduction: false };
    if (eaRating >= 82) return { label: `EA Rating ${eaRating} (fallback)`, modifier: 1.2, usedProduction: false };
    if (eaRating >= 75) return { label: `EA Rating ${eaRating} (fallback)`, modifier: 1.0, usedProduction: false };
    if (eaRating >= 68) return { label: `EA Rating ${eaRating} (fallback)`, modifier: 0.65, usedProduction: false };
    return { label: `EA Rating ${eaRating} (fallback)`, modifier: 0.4, usedProduction: false };
  }

  // Fallback 2: star rating proxy (narrower band)
  const star = starRating ?? 0;
  if (star >= 5) return { label: "5★ Recruit (star rating proxy)", modifier: 1.15, usedProduction: false };
  if (star === 4) return { label: "4★ Recruit (star rating proxy)", modifier: 1.0, usedProduction: false };
  if (star === 3) return { label: "3★ Recruit (star rating proxy)", modifier: 0.9, usedProduction: false };
  if (star >= 1) return { label: `${star}★ Recruit (star rating proxy)`, modifier: 0.8, usedProduction: false };
  return { label: "No talent data (neutral)", modifier: 1.0, usedProduction: false };
}

/**
 * Market multiplier clamped to [0.8, 1.3]. VALUATION_ENGINE.md §3.5
 */
export function getMarketMultiplier(teamMarketMultiplier: number | null): number {
  if (teamMarketMultiplier == null) return 1.0;
  return Math.max(0.8, Math.min(1.3, teamMarketMultiplier));
}

/**
 * Monotonically increasing experience curve. Replaces getYoeMultiplier from V3.
 * For HS recruits: derives from hs_grad_year.
 * For college athletes: uses class_year (1–5). Curve only goes up.
 * VALUATION_ENGINE.md §3.6
 */
export function getExperienceMultiplier(
  playerTag: string | null,
  classYear: number | string | null,
  hsGradYear: number | null,
): { label: string; multiplier: number } {
  const COLLEGE_MAP: Record<number, { label: string; multiplier: number }> = {
    1: { label: "Freshman", multiplier: 0.90 },
    2: { label: "Sophomore", multiplier: 1.00 },
    3: { label: "Junior", multiplier: 1.10 },
    4: { label: "Senior", multiplier: 1.15 },
    5: { label: "Super Senior", multiplier: 1.20 },
  };

  const tag = (playerTag ?? "").trim();

  if (tag === "High School Recruit") {
    if (hsGradYear != null) {
      if (hsGradYear <= CURRENT_YEAR + 1) return { label: "HS Senior", multiplier: 0.80 };
      if (hsGradYear === CURRENT_YEAR + 2) return { label: "HS Junior", multiplier: 0.35 };
      return { label: "HS Underclassman", multiplier: 0.25 };
    }
    return { label: "HS Recruit (unknown grad year)", multiplier: 0.75 };
  }

  // College athlete
  if (classYear == null) return { label: "Unknown Year", multiplier: 1.0 };
  const cy = typeof classYear === "string" ? parseInt(classYear, 10) : classYear;
  if (isNaN(cy)) return { label: "Unknown Year", multiplier: 1.0 };
  return COLLEGE_MAP[cy] ?? { label: "Unknown Year", multiplier: 1.0 };
}

/**
 * Social premium: $1 per follower, capped at $150,000. VALUATION_ENGINE.md §3.7
 */
export function calculateSocialPremium(totalFollowers: number | null): number {
  if (!totalFollowers || totalFollowers <= 0) return 0;
  return Math.min(totalFollowers, SOCIAL_CAP);
}

/**
 * Position-aware depth chart rank multiplier.
 * Multi-starter positions (OL, WR, LB, DL, CB, S, EDGE) treat more players
 * as starters and apply softer backup discounts.
 * Single-starter positions (QB, RB, TE, K, P) use steeper backup discounts.
 * VALUATION_ENGINE.md §3.8
 */

const POSITION_STARTER_COUNTS: Record<string, number> = {
  QB: 1, RB: 1, TE: 2, K: 1, P: 1, LS: 1, PK: 1,
  WR: 3,
  OL: 5, OT: 5, OG: 5, C: 5, IOL: 5,
  EDGE: 2, DE: 2,
  DT: 2, DL: 2,
  LB: 3, DB: 3,
  CB: 2,
  S: 2,
  ATH: 1,
};

const SINGLE_STARTER_POSITIONS = new Set(["QB", "RB", "K", "P", "LS", "PK", "ATH"]);

export function getDepthChartRankMultiplier(
  depthChartRank: number | null,
  isOnDepthChart: boolean | null,
  position: string | null = null,
  starRating: number | null = null,
  classYear: number | string | null = null,
): { label: string; multiplier: number } {
  if (!isOnDepthChart) {
    return { label: "Not on Depth Chart", multiplier: 0.12 };
  }

  const pos = (position ?? "").toUpperCase().trim();
  const starterCount = POSITION_STARTER_COUNTS[pos] ?? 1;
  const isSingle = SINGLE_STARTER_POSITIONS.has(pos);

  // Compute raw positional multiplier
  let rawMult: number;
  let rawLabel: string;

  if (depthChartRank == null) {
    rawMult = 0.55;
    rawLabel = "Unknown Rank";
  } else if (depthChartRank <= starterCount) {
    rawMult = 1.0;
    rawLabel = starterCount > 1
      ? `Starter (${depthChartRank} of ${starterCount} ${pos})`
      : "Starter";
  } else {
    const backupDepth = depthChartRank - starterCount;
    const ordinal = backupDepth === 1 ? "1st" : backupDepth === 2 ? "2nd" : `${backupDepth}th`;

    if (isSingle) {
      if (backupDepth === 1) { rawMult = 0.35; rawLabel = `${ordinal} Backup ${pos}`; }
      else if (backupDepth === 2) { rawMult = 0.20; rawLabel = `${ordinal} Backup ${pos}`; }
      else { rawMult = 0.12; rawLabel = `Deep Reserve ${pos}`; }
    } else {
      if (backupDepth === 1) { rawMult = 0.55; rawLabel = `${ordinal} Backup (multi-starter)`; }
      else if (backupDepth === 2) { rawMult = 0.40; rawLabel = `${ordinal} Backup (multi-starter)`; }
      else { rawMult = 0.25; rawLabel = `Deep Reserve (multi-starter)`; }
    }
  }

  // ── Recruiting pedigree floor (§3.8.1) ────────────────────────────────
  // Elite recruits (4-5★) in their first 3 years keep a minimum multiplier.
  const star = starRating ?? 0;
  const cy = typeof classYear === "string" ? parseInt(classYear, 10) : (classYear ?? 99);
  const cyNum = isNaN(cy) ? 99 : cy;

  let floor = 0;
  if (cyNum <= 3 && star >= 5) floor = 1.0;
  else if (cyNum <= 3 && star === 4) floor = 0.45;

  if (floor > 0 && rawMult < floor) {
    const rankDesc = depthChartRank != null ? `rank ${depthChartRank} ${pos}` : pos;
    return { label: `${star}★ Pedigree Floor (${rankDesc})`, multiplier: floor };
  }

  return { label: rawLabel, multiplier: rawMult };
}

// ─── HS Recruit valuation ────────────────────────────────────────────────────

const HS_COMPOSITE_TIERS: [number, number][] = [
  [99.0, 800_000], [98.0, 575_000], [97.0, 375_000], [96.0, 275_000],
  [95.0, 200_000], [94.0, 175_000], [93.0, 150_000], [91.0, 125_000], [89.0, 100_000],
];

const HS_STAR_FALLBACK: Record<number, number> = { 5: 450_000, 4: 150_000 };

export function getHsBaseValue(
  compositeScore: number | null,
  starRating: number | null,
): { label: string; value: number } {
  if (compositeScore != null && compositeScore >= 89.0) {
    for (const [threshold, value] of HS_COMPOSITE_TIERS) {
      if (compositeScore >= threshold) {
        const tierLabel = threshold >= 99 ? "Elite 5-Star" : threshold >= 98 ? "High 5-Star"
          : threshold >= 97 ? "Mid 5-Star" : threshold >= 96 ? "Low 5-Star"
          : threshold >= 95 ? "High 4-Star" : threshold >= 94 ? "Mid 4-Star"
          : threshold >= 93 ? "Low 4-Star" : threshold >= 91 ? "4-Star" : "Low 4-Star";
        return { label: `${tierLabel} (${compositeScore.toFixed(2)})`, value };
      }
    }
  }
  const star = starRating ?? 0;
  const value = HS_STAR_FALLBACK[star] ?? 100_000;
  return { label: star >= 4 ? `${star}-Star Fallback` : "Unranked", value };
}

const HS_POSITION_PREMIUMS: Record<string, number> = {
  QB: 2.0, OT: 1.5, LT: 1.5,
  OL: 1.2, OG: 1.2, C: 1.2, IOL: 1.2,
  WR: 1.1, EDGE: 1.1, DE: 1.1, DT: 1.1, DL: 1.1,
  CB: 1.05, LB: 1.0, S: 1.0, TE: 0.9, RB: 0.85,
  ATH: 1.0, K: 0.5, P: 0.5, LS: 0.5, DB: 1.0,
};

export function getHsPositionPremium(position: string | null): { label: string; multiplier: number } {
  if (!position) return { label: "Unknown Position", multiplier: 1.0 };
  const key = position.toUpperCase().trim();
  const mult = HS_POSITION_PREMIUMS[key] ?? 1.0;
  return { label: POSITION_LABELS[key] ?? key, multiplier: mult };
}

// ─── Full valuation ───────────────────────────────────────────────────────────

export interface ValuationBreakdown {
  // College-specific (null for HS)
  positionBase: { label: string; value: number } | null;
  draftPremium: { label: string; multiplier: number } | null;
  talentModifier: { label: string; modifier: number; usedProduction: boolean } | null;
  depthChartRank: { label: string; multiplier: number } | null;
  // HS-specific (null for college)
  hsBaseValue: { label: string; value: number } | null;
  hsPositionPremium: { label: string; multiplier: number } | null;
  // Shared
  marketMultiplier: { teamName: string; multiplier: number };
  experienceMultiplier: { label: string; multiplier: number };
  socialPremium: { followers: number; premium: number; capped: boolean };
  footballValue: number;
  total: number;
  isHsPath: boolean;
}

export interface PlayerValuationInput {
  player_tag: string | null;
  is_on_depth_chart: boolean | null;
  depth_chart_rank?: number | null;
  is_override?: boolean | null;
  position: string | null;
  nfl_draft_projection: number | null;
  production_score: number | null;
  star_rating: number | null;
  ea_rating?: number | null;
  composite_score?: number | null;
  class_year: number | string | null;
  hs_grad_year: number | null;
  total_followers?: number | null;
  ig_followers?: number | null;
  x_followers?: number | null;
  tiktok_followers?: number | null;
}

/**
 * Runs the full valuation formula.
 * Routes HS recruits through composite-based path, college athletes through
 * production/draft-based path.
 * Returns null for ineligible players.
 */
export function calculateCfoValuation(
  player: PlayerValuationInput,
  teamMarketMultiplier: number | null,
  teamName = "Unknown Program",
): { breakdown: ValuationBreakdown; total: number } | null {
  if (
    !isEligibleForValuation(
      player.player_tag,
      player.is_on_depth_chart,
      player.star_rating,
      player.is_override ?? false,
    )
  ) {
    return null;
  }

  const tag = (player.player_tag ?? "").trim();
  const marketMult = getMarketMultiplier(teamMarketMultiplier);
  const expMult = getExperienceMultiplier(player.player_tag, player.class_year, player.hs_grad_year);

  const totalFollowers =
    player.total_followers != null
      ? player.total_followers
      : (player.ig_followers ?? 0) + (player.x_followers ?? 0) + (player.tiktok_followers ?? 0);
  const socialPremiumRaw = calculateSocialPremium(totalFollowers);
  const capped = totalFollowers > 0 && totalFollowers > SOCIAL_CAP;

  let footballValue: number;
  let breakdown: ValuationBreakdown;

  if (tag === "High School Recruit") {
    // HS path: composite-based
    const hsBase = getHsBaseValue(player.composite_score ?? null, player.star_rating);
    const hsPosP = getHsPositionPremium(player.position);
    footballValue = hsBase.value * hsPosP.multiplier * marketMult * expMult.multiplier;

    breakdown = {
      positionBase: null, draftPremium: null, talentModifier: null, depthChartRank: null,
      hsBaseValue: hsBase,
      hsPositionPremium: hsPosP,
      marketMultiplier: { teamName, multiplier: marketMult },
      experienceMultiplier: expMult,
      socialPremium: { followers: totalFollowers, premium: socialPremiumRaw, capped },
      footballValue: Math.floor(footballValue),
      total: 0,
      isHsPath: true,
    };
  } else {
    // College path: production/draft-based
    const positionBase = getPositionBaseValue(player.position);
    const draftP = getDraftPremium(player.nfl_draft_projection);
    const talentMod = getTalentModifier(player.production_score, player.star_rating, player.ea_rating ?? null);
    const dcRank = getDepthChartRankMultiplier(player.depth_chart_rank ?? null, player.is_on_depth_chart, player.position, player.star_rating, player.class_year);
    footballValue = positionBase.value * draftP.multiplier * talentMod.modifier * marketMult * expMult.multiplier * dcRank.multiplier;

    breakdown = {
      positionBase, draftPremium: draftP, talentModifier: talentMod, depthChartRank: dcRank,
      hsBaseValue: null, hsPositionPremium: null,
      marketMultiplier: { teamName, multiplier: marketMult },
      experienceMultiplier: expMult,
      socialPremium: { followers: totalFollowers, premium: socialPremiumRaw, capped },
      footballValue: Math.floor(footballValue),
      total: 0,
      isHsPath: false,
    };
  }

  const total = Math.max(Math.floor(footballValue + socialPremiumRaw), 10_000);
  breakdown.total = total;

  return { breakdown, total };
}
