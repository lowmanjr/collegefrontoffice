import { describe, it, expect } from "vitest";
import {
  isEligibleForValuation,
  getPositionBaseValue,
  getDraftPremium,
  getTalentModifier,
  getMarketMultiplier,
  getExperienceMultiplier,
  calculateSocialPremium,
  getDepthChartRankMultiplier,
  getHsBaseValue,
  getHsPositionPremium,
  calculateCfoValuation,
  type PlayerValuationInput,
} from "../valuation";

// ─── isEligibleForValuation ─────────────────────────────────────────────────

describe("isEligibleForValuation", () => {
  it("college on DC → true", () => expect(isEligibleForValuation("College Athlete", true, 3)).toBe(true));
  it("college off DC → false", () => expect(isEligibleForValuation("College Athlete", false, 5)).toBe(false));
  it("college null DC → false", () => expect(isEligibleForValuation("College Athlete", null, 4)).toBe(false));
  it("HS 5-star → true", () => expect(isEligibleForValuation("High School Recruit", false, 5)).toBe(true));
  it("HS 4-star → true", () => expect(isEligibleForValuation("High School Recruit", false, 4)).toBe(true));
  it("HS 3-star → false", () => expect(isEligibleForValuation("High School Recruit", false, 3)).toBe(false));
  it("HS null star → false", () => expect(isEligibleForValuation("High School Recruit", false, null)).toBe(false));
  it("override bypasses", () => expect(isEligibleForValuation("College Athlete", false, 2, true)).toBe(true));
  it("unknown tag → true", () => expect(isEligibleForValuation("Other", false, null)).toBe(true));
  it("null tag → true", () => expect(isEligibleForValuation(null, null, null)).toBe(true));
});

// ─── getPositionBaseValue ───────────────────────────────────────────────────

describe("getPositionBaseValue", () => {
  // Recalibrated base values — April 2026 market update
  it("QB → $1.2M", () => expect(getPositionBaseValue("QB").value).toBe(1_200_000));
  it("WR → $550K", () => expect(getPositionBaseValue("WR").value).toBe(550_000));
  it("K → $100K", () => expect(getPositionBaseValue("K").value).toBe(100_000));
  it("unknown → $400K", () => expect(getPositionBaseValue("XYZ").value).toBe(400_000));
  it("null → $400K", () => expect(getPositionBaseValue(null).value).toBe(400_000));
  it("lowercase", () => expect(getPositionBaseValue("qb").value).toBe(1_200_000));
  it("whitespace", () => expect(getPositionBaseValue(" QB ").value).toBe(1_200_000));
  it("label", () => expect(getPositionBaseValue("QB").label).toBe("Quarterback"));
});

// ─── getDraftPremium ────────────────────────────────────────────────────────

describe("getDraftPremium", () => {
  it("pick 1 → 2.5x", () => expect(getDraftPremium(1).multiplier).toBe(2.5));
  it("pick 5 → 2.5x", () => expect(getDraftPremium(5).multiplier).toBe(2.5));
  it("pick 6 → 1.9x", () => expect(getDraftPremium(6).multiplier).toBe(1.9));
  it("pick 32 → 1.5x", () => expect(getDraftPremium(32).multiplier).toBe(1.5));
  it("pick 33 → 1.25x", () => expect(getDraftPremium(33).multiplier).toBe(1.25));
  it("pick 100 → 1.1x", () => expect(getDraftPremium(100).multiplier).toBe(1.1));
  it("pick 180 → 1.0x", () => expect(getDraftPremium(180).multiplier).toBe(1.0));
  it("pick 260 → 0.9x", () => expect(getDraftPremium(260).multiplier).toBe(0.9));
  it("null → 1.0x", () => expect(getDraftPremium(null).multiplier).toBe(1.0));
  it("0 sentinel", () => expect(getDraftPremium(0).multiplier).toBe(1.0));
  it("999 sentinel", () => expect(getDraftPremium(999).multiplier).toBe(1.0));
  it("500 sentinel", () => expect(getDraftPremium(500).multiplier).toBe(1.0));
  it("499 → 0.9x", () => expect(getDraftPremium(499).multiplier).toBe(0.9));
});

// ─── getTalentModifier (V3.2 steeper low tiers) ────────────────────────────

describe("getTalentModifier", () => {
  it("prod 95 → 1.4", () => expect(getTalentModifier(95, 3).modifier).toBe(1.4));
  it("prod 90 → 1.4", () => expect(getTalentModifier(90, null).modifier).toBe(1.4));
  it("prod 75 → 1.2", () => expect(getTalentModifier(75, null).modifier).toBe(1.2));
  it("prod 50 → 1.0", () => expect(getTalentModifier(50, null).modifier).toBe(1.0));
  it("prod 25 → 0.65", () => expect(getTalentModifier(25, null).modifier).toBe(0.65));
  it("prod 10 → 0.4", () => expect(getTalentModifier(10, null).modifier).toBe(0.4));
  it("prod 0 sentinel → star 5 → 1.15", () => {
    const r = getTalentModifier(0, 5);
    expect(r.modifier).toBe(1.15); expect(r.usedProduction).toBe(false);
  });
  it("null/4 → 1.0", () => expect(getTalentModifier(null, 4).modifier).toBe(1.0));
  it("null/3 → 0.9", () => expect(getTalentModifier(null, 3).modifier).toBe(0.9));
  it("null/null → 1.0", () => expect(getTalentModifier(null, null).modifier).toBe(1.0));
  it("prod 80 beats star 5", () => {
    const r = getTalentModifier(80, 5);
    expect(r.modifier).toBe(1.2); expect(r.usedProduction).toBe(true);
  });

  // EA rating fallback
  it("prod 80 + EA 90 → use production (1.2, not 1.4)", () =>
    expect(getTalentModifier(80, 4, 90).modifier).toBe(1.2));
  it("prod 0 + EA 86 → EA fallback (1.2)", () =>
    expect(getTalentModifier(0, 4, 86).modifier).toBe(1.2));
  it("prod null + EA null + star 4 → star fallback (1.0)", () =>
    expect(getTalentModifier(null, 4, null).modifier).toBe(1.0));
  it("prod null + EA 72 → EA fallback (0.65)", () =>
    expect(getTalentModifier(null, 3, 72).modifier).toBe(0.65));
  it("EA 90 → 1.4", () => expect(getTalentModifier(null, null, 90).modifier).toBe(1.4));
  it("EA 82 → 1.2", () => expect(getTalentModifier(null, null, 82).modifier).toBe(1.2));
  it("EA 75 → 1.0", () => expect(getTalentModifier(null, null, 75).modifier).toBe(1.0));
  it("EA 67 → 0.4", () => expect(getTalentModifier(null, null, 67).modifier).toBe(0.4));
  it("EA fallback label includes 'EA Rating'", () =>
    expect(getTalentModifier(0, 4, 86).label).toContain("EA Rating"));
});

// ─── getMarketMultiplier ────────────────────────────────────────────────────

describe("getMarketMultiplier", () => {
  it("1.2 in range", () => expect(getMarketMultiplier(1.2)).toBe(1.2));
  it("1.5 clamped", () => expect(getMarketMultiplier(1.5)).toBe(1.3));
  it("0.5 clamped", () => expect(getMarketMultiplier(0.5)).toBe(0.8));
  it("null → 1.0", () => expect(getMarketMultiplier(null)).toBe(1.0));
  it("0.8 edge", () => expect(getMarketMultiplier(0.8)).toBe(0.8));
  it("1.3 edge", () => expect(getMarketMultiplier(1.3)).toBe(1.3));
});

// ─── getExperienceMultiplier ────────────────────────────────────────────────

describe("getExperienceMultiplier", () => {
  it("FR → 0.90", () => expect(getExperienceMultiplier("College Athlete", 1, null).multiplier).toBe(0.90));
  it("SO → 1.00", () => expect(getExperienceMultiplier("College Athlete", 2, null).multiplier).toBe(1.00));
  it("JR → 1.10", () => expect(getExperienceMultiplier("College Athlete", 3, null).multiplier).toBe(1.10));
  it("SR → 1.15", () => expect(getExperienceMultiplier("College Athlete", 4, null).multiplier).toBe(1.15));
  it("5Y → 1.20", () => expect(getExperienceMultiplier("College Athlete", 5, null).multiplier).toBe(1.20));
  it("null → 1.0", () => expect(getExperienceMultiplier("College Athlete", null, null).multiplier).toBe(1.0));
  it("HS 2027 → 0.80", () => expect(getExperienceMultiplier("High School Recruit", null, 2027).multiplier).toBe(0.80));
  it("HS 2028 → 0.35", () => expect(getExperienceMultiplier("High School Recruit", null, 2028).multiplier).toBe(0.35));
  it("HS 2029 → 0.25", () => expect(getExperienceMultiplier("High School Recruit", null, 2029).multiplier).toBe(0.25));
  it("HS null → 0.75", () => expect(getExperienceMultiplier("High School Recruit", null, null).multiplier).toBe(0.75));
  it("monotonic", () => {
    const m = [1, 2, 3, 4, 5].map(cy => getExperienceMultiplier("College Athlete", cy, null).multiplier);
    for (let i = 1; i < m.length; i++) expect(m[i]).toBeGreaterThanOrEqual(m[i - 1]);
  });
});

// ─── calculateSocialPremium ─────────────────────────────────────────────────

describe("calculateSocialPremium", () => {
  it("100K → $100K", () => expect(calculateSocialPremium(100_000)).toBe(100_000));
  it("200K → $150K cap", () => expect(calculateSocialPremium(200_000)).toBe(150_000));
  it("0 → $0", () => expect(calculateSocialPremium(0)).toBe(0));
  it("null → $0", () => expect(calculateSocialPremium(null)).toBe(0));
  it("negative → $0", () => expect(calculateSocialPremium(-100)).toBe(0));
});

// ─── getDepthChartRankMultiplier (position-aware) ───────────────────────────

describe("getDepthChartRankMultiplier", () => {
  // Single-starter positions
  it("QB rank 1 → 1.0 (starter)", () =>
    expect(getDepthChartRankMultiplier(1, true, "QB").multiplier).toBe(1.0));
  it("QB rank 2 → 0.35 (1st backup, single)", () =>
    expect(getDepthChartRankMultiplier(2, true, "QB").multiplier).toBe(0.35));
  it("QB rank 3 → 0.20 (2nd backup, single)", () =>
    expect(getDepthChartRankMultiplier(3, true, "QB").multiplier).toBe(0.20));
  it("QB rank 4 → 0.12 (deep reserve, single)", () =>
    expect(getDepthChartRankMultiplier(4, true, "QB").multiplier).toBe(0.12));
  it("TE rank 2 → 1.0 (2nd TE is a starter)", () =>
    expect(getDepthChartRankMultiplier(2, true, "TE").multiplier).toBe(1.0));
  it("TE rank 3 → 0.55 (1st backup, multi-starter)", () =>
    expect(getDepthChartRankMultiplier(3, true, "TE").multiplier).toBe(0.55));
  it("K rank 2 → 0.35 (single-starter backup)", () =>
    expect(getDepthChartRankMultiplier(2, true, "K").multiplier).toBe(0.35));

  // Multi-starter positions
  it("OL rank 1 → 1.0 (starter)", () =>
    expect(getDepthChartRankMultiplier(1, true, "OL").multiplier).toBe(1.0));
  it("OL rank 5 → 1.0 (still starter — 5 OL start)", () =>
    expect(getDepthChartRankMultiplier(5, true, "OL").multiplier).toBe(1.0));
  it("OL rank 6 → 0.55 (1st backup, multi)", () =>
    expect(getDepthChartRankMultiplier(6, true, "OL").multiplier).toBe(0.55));
  it("OL rank 7 → 0.40 (2nd backup, multi)", () =>
    expect(getDepthChartRankMultiplier(7, true, "OL").multiplier).toBe(0.40));
  it("OL rank 8 → 0.25 (deep reserve, multi)", () =>
    expect(getDepthChartRankMultiplier(8, true, "OL").multiplier).toBe(0.25));
  it("WR rank 3 → 1.0 (3rd WR is a starter)", () =>
    expect(getDepthChartRankMultiplier(3, true, "WR").multiplier).toBe(1.0));
  it("WR rank 4 → 0.55 (1st backup WR)", () =>
    expect(getDepthChartRankMultiplier(4, true, "WR").multiplier).toBe(0.55));
  it("CB rank 2 → 1.0 (2nd CB is a starter)", () =>
    expect(getDepthChartRankMultiplier(2, true, "CB").multiplier).toBe(1.0));
  it("CB rank 3 → 0.55 (1st backup CB)", () =>
    expect(getDepthChartRankMultiplier(3, true, "CB").multiplier).toBe(0.55));
  it("LB rank 3 → 1.0 (3rd LB is a starter)", () =>
    expect(getDepthChartRankMultiplier(3, true, "LB").multiplier).toBe(1.0));
  it("LB rank 4 → 0.55 (1st backup LB)", () =>
    expect(getDepthChartRankMultiplier(4, true, "LB").multiplier).toBe(0.55));
  it("S rank 2 → 1.0 (2nd S is a starter)", () =>
    expect(getDepthChartRankMultiplier(2, true, "S").multiplier).toBe(1.0));
  it("S rank 3 → 0.55 (1st backup S)", () =>
    expect(getDepthChartRankMultiplier(3, true, "S").multiplier).toBe(0.55));

  // Edge cases
  it("null rank on DC → 0.55", () =>
    expect(getDepthChartRankMultiplier(null, true, "QB").multiplier).toBe(0.55));
  it("not on DC → 0.12", () =>
    expect(getDepthChartRankMultiplier(null, false, "QB").multiplier).toBe(0.12));
  it("null position → starter_count=1, multi-starter path", () =>
    expect(getDepthChartRankMultiplier(2, true, null).multiplier).toBe(0.55));

  // Recruiting pedigree floor
  it("5★ FR at LB rank 7 → 1.0 (floor, not 0.25)", () =>
    expect(getDepthChartRankMultiplier(7, true, "LB", 5, 1).multiplier).toBe(1.0));
  it("4★ SO at WR rank 8 → 0.45 (floor, not 0.25)", () =>
    expect(getDepthChartRankMultiplier(8, true, "WR", 4, 2).multiplier).toBe(0.45));
  it("5★ SR (class 4) at LB rank 7 → 0.25 (no floor)", () =>
    expect(getDepthChartRankMultiplier(7, true, "LB", 5, 4).multiplier).toBe(0.25));
  it("4★ JR at QB rank 3 → 0.45 (floor, not 0.20)", () =>
    expect(getDepthChartRankMultiplier(3, true, "QB", 4, 3).multiplier).toBe(0.45));
  it("3★ FR at LB rank 7 → 0.25 (no floor)", () =>
    expect(getDepthChartRankMultiplier(7, true, "LB", 3, 1).multiplier).toBe(0.25));
  it("5★ JR at WR rank 1 → 1.0 (starter, floor irrelevant)", () =>
    expect(getDepthChartRankMultiplier(1, true, "WR", 5, 3).multiplier).toBe(1.0));
  it("5★ FR at LB rank 7 label includes pedigree", () =>
    expect(getDepthChartRankMultiplier(7, true, "LB", 5, 1).label).toContain("Pedigree Floor"));
  it("4★ SO at WR rank 8 label includes pedigree", () =>
    expect(getDepthChartRankMultiplier(8, true, "WR", 4, 2).label).toContain("Pedigree Floor"));
  it("5★ SR at LB rank 7 label does NOT include pedigree", () =>
    expect(getDepthChartRankMultiplier(7, true, "LB", 5, 4).label).not.toContain("Pedigree"));
});

// ─── calculateCfoValuation — Full integration ───────────────────────────────

describe("calculateCfoValuation", () => {
  it("ineligible college → null", () => {
    const p: PlayerValuationInput = {
      player_tag: "College Athlete", is_on_depth_chart: false,
      position: "QB", nfl_draft_projection: null, production_score: null,
      star_rating: 4, class_year: 3, hs_grad_year: null,
    };
    expect(calculateCfoValuation(p, 1.0)).toBeNull();
  });

  it("starter QB rank 1, prod 78, market 1.2, 5Y, 41K followers", () => {
    const p: PlayerValuationInput = {
      player_tag: "College Athlete", is_on_depth_chart: true, depth_chart_rank: 1,
      position: "QB", nfl_draft_projection: null, production_score: 78,
      star_rating: 4, class_year: 5, hs_grad_year: null, total_followers: 41_338,
    };
    const r = calculateCfoValuation(p, 1.2);
    expect(r).not.toBeNull();
    // Recalibrated: 1200000 * 1.0 * 1.2 * 1.2 * 1.20 * 1.0 = 2,073,600 + 41338 = 2,114,938
    expect(r!.total).toBe(2_114_938);
  });

  it("elite WR starter rank 1, pick 8, prod 92, market 1.3", () => {
    const p: PlayerValuationInput = {
      player_tag: "College Athlete", is_on_depth_chart: true, depth_chart_rank: 1,
      position: "WR", nfl_draft_projection: 8, production_score: 92,
      star_rating: 5, class_year: 3, hs_grad_year: null, total_followers: 800_000,
    };
    const r = calculateCfoValuation(p, 1.3);
    expect(r).not.toBeNull();
    // Recalibrated: 550000 * 1.9 * 1.4 * 1.3 * 1.10 * 1.0 = 2,092,090 + 150000 = 2,242,090
    expect(r!.total).toBe(2_242_090);
  });

  it("backup QB rank 2 → 0.35x (single-starter, senior = no pedigree floor)", () => {
    const p: PlayerValuationInput = {
      player_tag: "College Athlete", is_on_depth_chart: true, depth_chart_rank: 2,
      position: "QB", nfl_draft_projection: null, production_score: 40,
      star_rating: 4, class_year: 4, hs_grad_year: null, total_followers: 5_000,
    };
    const r = calculateCfoValuation(p, 1.2);
    expect(r).not.toBeNull();
    // Recalibrated: 1200000 * 1.0 * 0.65 * 1.2 * 1.15 * 0.35 = 376,740 + 5000 = 381,740
    expect(r!.total).toBe(381_740);
  });

  it("OL rank 5 = starter (5 OL start)", () => {
    const p: PlayerValuationInput = {
      player_tag: "College Athlete", is_on_depth_chart: true, depth_chart_rank: 5,
      position: "OL", nfl_draft_projection: null, production_score: null,
      star_rating: null, class_year: 5, hs_grad_year: null, total_followers: 0,
    };
    const r = calculateCfoValuation(p, 1.2);
    expect(r).not.toBeNull();
    // Recalibrated: 475000 * 1.0 * 1.0 * 1.2 * 1.20 * 1.0 = 684,000
    expect(r!.total).toBe(684_000);
    expect(r!.breakdown.depthChartRank!.multiplier).toBe(1.0);
  });

  it("WR rank 4 = 1st backup (multi-starter, senior = no pedigree floor) → 0.55x", () => {
    const p: PlayerValuationInput = {
      player_tag: "College Athlete", is_on_depth_chart: true, depth_chart_rank: 4,
      position: "WR", nfl_draft_projection: null, production_score: 72,
      star_rating: 4, class_year: 4, hs_grad_year: null, total_followers: 0,
    };
    const r = calculateCfoValuation(p, 1.2);
    expect(r).not.toBeNull();
    // Recalibrated: 550000 * 1.0 * 1.0 * 1.2 * 1.15 * 0.55 = 417,449 (FP)
    expect(r!.total).toBe(417_449);
    expect(r!.breakdown.depthChartRank!.multiplier).toBe(0.55);
  });

  it("kicker starter", () => {
    const p: PlayerValuationInput = {
      player_tag: "College Athlete", is_on_depth_chart: true, depth_chart_rank: 1,
      position: "K", nfl_draft_projection: null, production_score: null,
      star_rating: null, class_year: 4, hs_grad_year: null, total_followers: 2_000,
    };
    const r = calculateCfoValuation(p, 1.0);
    expect(r).not.toBeNull();
    // Recalibrated: 100000 * 1.0 * 1.0 * 1.0 * 1.15 * 1.0 = 114,999 (FP) + 2000 = 116,999
    expect(r!.total).toBe(116_999);
  });

  it("$10K floor", () => {
    const p: PlayerValuationInput = {
      player_tag: "College Athlete", is_on_depth_chart: true, depth_chart_rank: 4,
      position: "LS", nfl_draft_projection: 260, production_score: 5,
      star_rating: null, class_year: 1, hs_grad_year: null, total_followers: 0,
    };
    const r = calculateCfoValuation(p, 0.8);
    expect(r).not.toBeNull();
    expect(r!.total).toBe(10_000);
  });

  it("HS recruit uses composite path (no DC multiplier)", () => {
    const p: PlayerValuationInput = {
      player_tag: "High School Recruit", is_on_depth_chart: false,
      position: "QB", nfl_draft_projection: null, production_score: null,
      star_rating: 5, composite_score: 99.0, class_year: null, hs_grad_year: 2027,
      total_followers: 80_000,
    };
    const r = calculateCfoValuation(p, 1.25);
    expect(r).not.toBeNull();
    // HS: 800000 * 2.0 * 1.25 * 0.80 = 1,600,000 + 80000 = 1,680,000
    expect(r!.total).toBe(1_680_000);
    expect(r!.breakdown.isHsPath).toBe(true);
  });
});

// ─── getHsBaseValue ─────────────────────────────────────────────────────────

describe("getHsBaseValue", () => {
  it("composite 99.5 → $800K", () => expect(getHsBaseValue(99.5, 5).value).toBe(800_000));
  it("composite 98.5 → $575K", () => expect(getHsBaseValue(98.5, 5).value).toBe(575_000));
  it("composite 97.0 → $375K", () => expect(getHsBaseValue(97.0, 5).value).toBe(375_000));
  it("composite 96.5 → $275K", () => expect(getHsBaseValue(96.5, 4).value).toBe(275_000));
  it("composite 95.2 → $200K", () => expect(getHsBaseValue(95.2, 4).value).toBe(200_000));
  it("composite 94.0 → $175K", () => expect(getHsBaseValue(94.0, 4).value).toBe(175_000));
  it("composite 93.5 → $150K", () => expect(getHsBaseValue(93.5, 4).value).toBe(150_000));
  it("composite 91.5 → $125K", () => expect(getHsBaseValue(91.5, 4).value).toBe(125_000));
  it("composite 89.5 → $100K", () => expect(getHsBaseValue(89.5, 4).value).toBe(100_000));
  it("null composite, 5-star → $450K", () => expect(getHsBaseValue(null, 5).value).toBe(450_000));
  it("null composite, 4-star → $150K", () => expect(getHsBaseValue(null, 4).value).toBe(150_000));
  it("composite 85 (below min) → star fallback", () => expect(getHsBaseValue(85.0, 4).value).toBe(150_000));
});

// ─── getHsPositionPremium ───────────────────────────────────────────────────

describe("getHsPositionPremium", () => {
  it("QB → 2.0", () => expect(getHsPositionPremium("QB").multiplier).toBe(2.0));
  it("OT → 1.5", () => expect(getHsPositionPremium("OT").multiplier).toBe(1.5));
  it("WR → 1.1", () => expect(getHsPositionPremium("WR").multiplier).toBe(1.1));
  it("RB → 0.85", () => expect(getHsPositionPremium("RB").multiplier).toBe(0.85));
  it("null → 1.0", () => expect(getHsPositionPremium(null).multiplier).toBe(1.0));
});

// ─── HS integration tests ───────────────────────────────────────────────────

describe("calculateCfoValuation HS path", () => {
  it("elite 5-star QB, 99.0 composite, SEC 1.3x, 2026 senior, 20K followers", () => {
    const p: PlayerValuationInput = {
      player_tag: "High School Recruit", is_on_depth_chart: false,
      position: "QB", nfl_draft_projection: null, production_score: null,
      star_rating: 5, composite_score: 99.0, class_year: null, hs_grad_year: 2026,
      total_followers: 20_000,
    };
    const r = calculateCfoValuation(p, 1.3);
    expect(r).not.toBeNull();
    // 800000 * 2.0 * 1.3 * 0.80 = 1,664,000 + 20000 = 1,684,000
    expect(r!.total).toBe(1_684_000);
  });

  it("4-star RB, 95.5 composite, mid P4 1.0x, 2028 junior, 5K followers", () => {
    const p: PlayerValuationInput = {
      player_tag: "High School Recruit", is_on_depth_chart: false,
      position: "RB", nfl_draft_projection: null, production_score: null,
      star_rating: 4, composite_score: 95.5, class_year: null, hs_grad_year: 2028,
      total_followers: 5_000,
    };
    const r = calculateCfoValuation(p, 1.0);
    expect(r).not.toBeNull();
    // Recalibrated: 200000 * 0.85 * 1.0 * 0.35 = 59,499 + 5000 = 64,499
    expect(r!.total).toBe(64_499);
  });

  it("4-star no composite, uncommitted, 2027 junior", () => {
    const p: PlayerValuationInput = {
      player_tag: "High School Recruit", is_on_depth_chart: false,
      position: "LB", nfl_draft_projection: null, production_score: null,
      star_rating: 4, composite_score: null, class_year: null, hs_grad_year: 2027,
      total_followers: 0,
    };
    const r = calculateCfoValuation(p, 1.0);
    expect(r).not.toBeNull();
    // 150000 * 1.0 * 1.0 * 0.80 = 120,000
    expect(r!.total).toBe(120_000);
  });
});
