"""
Unit tests for the V3.2 valuation engine (position-aware depth chart rank).
Mirrors lib/__tests__/valuation.test.ts.

Run: cd python_engine && python -m pytest tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculate_cfo_valuations import (
    is_eligible_for_valuation, position_base_value, draft_premium,
    talent_modifier, market_multiplier, experience_multiplier,
    social_premium, depth_chart_rank_multiplier, calculate_valuation,
    hs_base_value, hs_position_premium,
)


class TestIsEligible:
    def test_college_on_dc(self):   assert is_eligible_for_valuation({"player_tag": "College Athlete", "is_on_depth_chart": True, "star_rating": 3})
    def test_college_off_dc(self):  assert not is_eligible_for_valuation({"player_tag": "College Athlete", "is_on_depth_chart": False, "star_rating": 5})
    def test_college_null_dc(self): assert not is_eligible_for_valuation({"player_tag": "College Athlete", "is_on_depth_chart": None})
    def test_hs_5(self):            assert is_eligible_for_valuation({"player_tag": "High School Recruit", "star_rating": 5})
    def test_hs_4(self):            assert is_eligible_for_valuation({"player_tag": "High School Recruit", "star_rating": 4})
    def test_hs_3(self):            assert not is_eligible_for_valuation({"player_tag": "High School Recruit", "star_rating": 3})
    def test_hs_null(self):         assert not is_eligible_for_valuation({"player_tag": "High School Recruit", "star_rating": None})
    def test_override(self):        assert is_eligible_for_valuation({"player_tag": "College Athlete", "is_on_depth_chart": False}, is_override=True)
    def test_unknown(self):         assert is_eligible_for_valuation({"player_tag": "Other"})
    def test_null(self):            assert is_eligible_for_valuation({"player_tag": None})
    def test_ls_excluded(self):     assert not is_eligible_for_valuation({"player_tag": "College Athlete", "is_on_depth_chart": True, "position": "LS"})
    def test_ls_override(self):     assert is_eligible_for_valuation({"player_tag": "College Athlete", "is_on_depth_chart": True, "position": "LS"}, is_override=True)


class TestPositionBase:
    # Recalibrated base values — April 2026 market update
    def test_qb(self):    assert position_base_value("QB") == 1_500_000
    def test_wr(self):    assert position_base_value("WR") == 550_000
    def test_k(self):     assert position_base_value("K") == 100_000
    def test_unk(self):   assert position_base_value("XYZ") == 400_000
    def test_none(self):  assert position_base_value(None) == 400_000
    def test_lower(self): assert position_base_value("qb") == 1_500_000
    def test_space(self): assert position_base_value(" QB ") == 1_500_000
    def test_dt(self):    assert position_base_value("DT") == 600_000
    def test_dl(self):    assert position_base_value("DL") == 600_000


class TestDraftPremium:
    def test_1(self):    assert draft_premium(1) == 2.5
    def test_5(self):    assert draft_premium(5) == 2.5
    def test_6(self):    assert draft_premium(6) == 1.9
    def test_32(self):   assert draft_premium(32) == 1.5
    def test_33(self):   assert draft_premium(33) == 1.25
    def test_100(self):  assert draft_premium(100) == 1.1
    def test_180(self):  assert draft_premium(180) == 1.0
    def test_260(self):  assert draft_premium(260) == 0.9
    def test_null(self): assert draft_premium(None) == 1.0
    def test_0(self):    assert draft_premium(0) == 1.0
    def test_999(self):  assert draft_premium(999) == 1.0
    def test_500(self):  assert draft_premium(500) == 1.0
    def test_499(self):  assert draft_premium(499) == 0.9


class TestTalentModifier:
    def test_95(self):       assert talent_modifier(95, 3) == 1.4
    def test_90(self):       assert talent_modifier(90, None) == 1.4
    def test_75(self):       assert talent_modifier(75, None) == 1.2
    def test_50(self):       assert talent_modifier(50, None) == 1.0
    def test_25(self):       assert talent_modifier(25, None) == 0.65
    def test_10(self):       assert talent_modifier(10, None) == 0.4
    def test_0_star5(self):  assert talent_modifier(0, 5) == 1.30   # V3.6b widened
    def test_null4(self):    assert talent_modifier(None, 4) == 1.0
    def test_null3(self):    assert talent_modifier(None, 3) == 0.80  # V3.6b widened
    def test_nullnull(self): assert talent_modifier(None, None) == 0.70  # V3.6b no-data penalty
    # V3.6b new tests
    def test_star2(self):    assert talent_modifier(None, 2) == 0.65   # V3.6b widened
    def test_star1(self):    assert talent_modifier(None, 1) == 0.65   # V3.6b widened
    def test_nodata_all_zero(self): assert talent_modifier(0, 0, ea_rating=0) == 0.70
    def test_80star5(self):  assert talent_modifier(80, 5) == 1.2

    # EA rating fallback
    def test_prod_beats_ea(self):
        # production_score 80 AND ea_rating 90 → use production (1.2, not 1.4)
        assert talent_modifier(80, 4, ea_rating=90) == 1.2
    def test_ea_fallback_86(self):
        # production_score 0 AND ea_rating 86 → use EA fallback (1.2)
        assert talent_modifier(0, 4, ea_rating=86) == 1.2
    def test_star_fallback_no_ea(self):
        # production_score NULL AND ea_rating NULL AND star 4 → star fallback (1.0)
        assert talent_modifier(None, 4, ea_rating=None) == 1.0
    def test_ea_fallback_72(self):
        # production_score NULL AND ea_rating 72 → EA fallback (0.65)
        assert talent_modifier(None, 3, ea_rating=72) == 0.65
    def test_ea_90(self):  assert talent_modifier(None, None, ea_rating=90) == 1.4
    def test_ea_82(self):  assert talent_modifier(None, None, ea_rating=82) == 1.2
    def test_ea_75(self):  assert talent_modifier(None, None, ea_rating=75) == 1.0
    def test_ea_67(self):  assert talent_modifier(None, None, ea_rating=67) == 0.4


class TestMarketMult:
    def test_in(self):   assert market_multiplier(1.2) == 1.2
    def test_max(self):  assert market_multiplier(1.5) == 1.3
    def test_min(self):  assert market_multiplier(0.5) == 0.8
    def test_null(self): assert market_multiplier(None) == 1.0
    def test_lo(self):   assert market_multiplier(0.8) == 0.8
    def test_hi(self):   assert market_multiplier(1.3) == 1.3


class TestExpMult:
    def test_fr(self):      assert experience_multiplier("College Athlete", 1, None) == 0.90
    def test_so(self):      assert experience_multiplier("College Athlete", 2, None) == 1.00
    def test_jr(self):      assert experience_multiplier("College Athlete", 3, None) == 1.10
    def test_sr(self):      assert experience_multiplier("College Athlete", 4, None) == 1.15
    def test_5y(self):      assert experience_multiplier("College Athlete", 5, None) == 1.20
    def test_null(self):    assert experience_multiplier("College Athlete", None, None) == 1.0
    def test_hs2027(self):  assert experience_multiplier("High School Recruit", None, 2027) == 0.80
    def test_hs2028(self):  assert experience_multiplier("High School Recruit", None, 2028) == 0.35
    def test_hs2029(self):  assert experience_multiplier("High School Recruit", None, 2029) == 0.25
    def test_hsnull(self):  assert experience_multiplier("High School Recruit", None, None) == 0.75
    def test_mono(self):
        m = [experience_multiplier("College Athlete", cy, None) for cy in range(1, 6)]
        for i in range(1, len(m)): assert m[i] >= m[i - 1]


class TestSocial:
    def test_100k(self): assert social_premium(100_000) == 100_000
    def test_200k(self): assert social_premium(200_000) == 150_000
    def test_0(self):    assert social_premium(0) == 0
    def test_null(self): assert social_premium(None) == 0
    def test_neg(self):  assert social_premium(-100) == 0


class TestDepthChartRankMultiplier:
    # Single-starter
    def test_qb_r1(self): assert depth_chart_rank_multiplier(1, True, "QB") == 1.0
    def test_qb_r2(self): assert depth_chart_rank_multiplier(2, True, "QB") == 0.35
    def test_qb_r3(self): assert depth_chart_rank_multiplier(3, True, "QB") == 0.20
    def test_qb_r4(self): assert depth_chart_rank_multiplier(4, True, "QB") == 0.12
    def test_te_r2(self): assert depth_chart_rank_multiplier(2, True, "TE") == 0.90  # V3.6b graduated TE2
    def test_te_r3(self): assert depth_chart_rank_multiplier(3, True, "TE") == 0.55  # 1st backup, multi
    def test_k_r2(self):  assert depth_chart_rank_multiplier(2, True, "K") == 0.35

    # Multi-starter
    def test_ol_r1(self): assert depth_chart_rank_multiplier(1, True, "OL") == 1.0
    def test_ol_r2(self): assert depth_chart_rank_multiplier(2, True, "OL") == 0.90  # V3.6b graduated
    def test_ol_r3(self): assert depth_chart_rank_multiplier(3, True, "OL") == 0.80  # V3.6b graduated
    def test_ol_r4(self): assert depth_chart_rank_multiplier(4, True, "OL") == 0.75  # V3.6b graduated
    def test_ol_r5(self): assert depth_chart_rank_multiplier(5, True, "OL") == 0.70  # V3.6b graduated
    def test_ol_r6(self): assert depth_chart_rank_multiplier(6, True, "OL") == 0.55
    def test_ol_r7(self): assert depth_chart_rank_multiplier(7, True, "OL") == 0.40
    def test_ol_r8(self): assert depth_chart_rank_multiplier(8, True, "OL") == 0.25
    def test_wr_r2(self): assert depth_chart_rank_multiplier(2, True, "WR") == 0.90  # V3.6b graduated
    def test_wr_r3(self): assert depth_chart_rank_multiplier(3, True, "WR") == 0.80  # V3.6b graduated
    def test_wr_r4(self): assert depth_chart_rank_multiplier(4, True, "WR") == 0.55
    def test_cb_r2(self): assert depth_chart_rank_multiplier(2, True, "CB") == 0.90  # V3.6b graduated
    def test_cb_r3(self): assert depth_chart_rank_multiplier(3, True, "CB") == 0.55
    def test_lb_r2(self): assert depth_chart_rank_multiplier(2, True, "LB") == 0.90  # V3.6b graduated
    def test_lb_r3(self): assert depth_chart_rank_multiplier(3, True, "LB") == 0.80  # V3.6b graduated
    def test_lb_r4(self): assert depth_chart_rank_multiplier(4, True, "LB") == 0.55
    def test_s_r2(self):  assert depth_chart_rank_multiplier(2, True, "S") == 0.90  # V3.6b graduated
    def test_s_r3(self):  assert depth_chart_rank_multiplier(3, True, "S") == 0.55

    # Edge cases
    def test_null_on_dc(self):  assert depth_chart_rank_multiplier(None, True, "QB") == 0.55
    def test_off_dc(self):      assert depth_chart_rank_multiplier(None, False, "QB") == 0.12
    def test_null_pos(self):    assert depth_chart_rank_multiplier(2, True, None) == 0.55

    # Recruiting pedigree floor
    def test_5star_fr_lb_r7(self):
        # 5★ FR at LB rank 7 → deep reserve would be 0.25, but floor = 1.0
        assert depth_chart_rank_multiplier(7, True, "LB", star_rating=5, class_year=1) == 1.0
    def test_4star_so_wr_r8(self):
        # 4★ SO at WR rank 8 → deep reserve would be 0.25, but floor = 0.45
        assert depth_chart_rank_multiplier(8, True, "WR", star_rating=4, class_year=2) == 0.45
    def test_5star_sr_lb_r7(self):
        # 5★ SR (class 4) → no floor, normal 0.25
        assert depth_chart_rank_multiplier(7, True, "LB", star_rating=5, class_year=4) == 0.25
    def test_4star_jr_qb_r3(self):
        # 4★ JR at QB rank 3 → 2nd backup = 0.20, but floor = 0.45
        assert depth_chart_rank_multiplier(3, True, "QB", star_rating=4, class_year=3) == 0.45
    def test_3star_fr_no_floor(self):
        # 3★ FR → no floor, normal multiplier
        assert depth_chart_rank_multiplier(7, True, "LB", star_rating=3, class_year=1) == 0.25
    def test_5star_jr_wr_r1(self):
        # 5★ JR at WR rank 1 → starter 1.0, floor irrelevant
        assert depth_chart_rank_multiplier(1, True, "WR", star_rating=5, class_year=3) == 1.0
    def test_5star_so_backup_qb(self):
        # 5★ SO at QB rank 2 → 1st backup = 0.35, floor = 1.0
        assert depth_chart_rank_multiplier(2, True, "QB", star_rating=5, class_year=2) == 1.0
    def test_5star_fr_wr_r3_floor(self):
        # 5★ FR at WR rank 3 → graduated 0.80, but pedigree floor = 1.0
        assert depth_chart_rank_multiplier(3, True, "WR", star_rating=5, class_year=1) == 1.0
    def test_4star_fr_starter(self):
        # 4★ FR at OL rank 3 → graduated 0.80, which is > 0.45 floor → 0.80
        assert depth_chart_rank_multiplier(3, True, "OL", star_rating=4, class_year=1) == 0.80
    def test_no_star_no_floor(self):
        # No star data → no floor
        assert depth_chart_rank_multiplier(7, True, "LB", star_rating=None, class_year=1) == 0.25


class TestCalculateValuation:
    # Recalibrated base values — April 2026 market update
    def test_starter_qb(self):
        p = {"player_tag": "College Athlete", "is_on_depth_chart": True, "depth_chart_rank": 1,
             "position": "QB", "nfl_draft_projection": None, "production_score": 78,
             "star_rating": 4, "class_year": 5, "hs_grad_year": None, "total_followers": 41_338}
        # V3.6b: 1500000 * 1.0 * 1.2 * 1.2 * 1.20 * 1.0 = 2,592,000 + 41338 = 2,633,338
        assert calculate_valuation(p, 1.2) == 2_633_338

    def test_elite_wr(self):
        p = {"player_tag": "College Athlete", "is_on_depth_chart": True, "depth_chart_rank": 1,
             "position": "WR", "nfl_draft_projection": 8, "production_score": 92,
             "star_rating": 5, "class_year": 3, "hs_grad_year": None, "total_followers": 800_000}
        # 550000 * 1.9 * 1.4 * 1.3 * 1.10 * 1.0 = 2,092,090 + 150000 = 2,242,090
        assert calculate_valuation(p, 1.3) == 2_242_090

    def test_backup_qb_single_starter(self):
        p = {"player_tag": "College Athlete", "is_on_depth_chart": True, "depth_chart_rank": 2,
             "position": "QB", "nfl_draft_projection": None, "production_score": 40,
             "star_rating": 4, "class_year": 4, "hs_grad_year": None, "total_followers": 5_000}
        # V3.6b: 1500000 * 1.0 * 0.65 * 1.2 * 1.15 * 0.35 = 470,924.99.. + 5000 = 475,924
        assert calculate_valuation(p, 1.2) == 475_924

    def test_ol_rank5_starter(self):
        p = {"player_tag": "College Athlete", "is_on_depth_chart": True, "depth_chart_rank": 5,
             "position": "OL", "nfl_draft_projection": None, "production_score": None,
             "star_rating": None, "class_year": 5, "hs_grad_year": None, "total_followers": 0}
        # V3.6b: 475000 * 1.0 * 0.70 * 1.2 * 1.20 * 0.70 = 335,160
        assert calculate_valuation(p, 1.2) == 335_160

    def test_wr_rank4_multi_backup(self):
        p = {"player_tag": "College Athlete", "is_on_depth_chart": True, "depth_chart_rank": 4,
             "position": "WR", "nfl_draft_projection": None, "production_score": 72,
             "star_rating": 4, "class_year": 4, "hs_grad_year": None, "total_followers": 0}
        # Recalibrated: 550000 * 1.0 * 1.0 * 1.2 * 1.15 * 0.55 = 417,449 (FP)
        assert calculate_valuation(p, 1.2) == 417_449

    def test_kicker_starter(self):
        p = {"player_tag": "College Athlete", "is_on_depth_chart": True, "depth_chart_rank": 1,
             "position": "K", "nfl_draft_projection": None, "production_score": None,
             "star_rating": None, "class_year": 4, "hs_grad_year": None, "total_followers": 2_000}
        # V3.6b: 100000 * 1.0 * 0.70 * 1.0 * 1.15 * 1.0 = 80,500 + 2000 = 82,500
        assert calculate_valuation(p, 1.0) == 82_500

    def test_floor_10k(self):
        p = {"player_tag": "College Athlete", "is_on_depth_chart": True, "depth_chart_rank": 4,
             "position": "PK", "nfl_draft_projection": 260, "production_score": 5,
             "star_rating": None, "class_year": 1, "hs_grad_year": None, "total_followers": 0}
        assert calculate_valuation(p, 0.8) == 10_000

    def test_hs_recruit_composite_path(self):
        p = {"player_tag": "High School Recruit", "is_on_depth_chart": False,
             "position": "QB", "nfl_draft_projection": None, "production_score": None,
             "star_rating": 5, "composite_score": 99.0, "class_year": None,
             "hs_grad_year": 2027, "total_followers": 80_000}
        # HS: 800000 * 2.0 * 1.25 * 0.80 = 1,600,000 + 80000 = 1,680,000
        assert calculate_valuation(p, 1.25) == 1_680_000

    def test_hs_4star_rb_junior(self):
        p = {"player_tag": "High School Recruit", "is_on_depth_chart": False,
             "position": "RB", "production_score": None, "composite_score": 95.5,
             "star_rating": 4, "class_year": None, "hs_grad_year": 2028, "total_followers": 5_000}
        # Recalibrated: 200000 * 0.85 * 1.0 * 0.35 = 59,499 + 5000 = 64,499
        assert calculate_valuation(p, 1.0) == 64_499

    def test_hs_no_composite_lb(self):
        p = {"player_tag": "High School Recruit", "is_on_depth_chart": False,
             "position": "LB", "production_score": None, "composite_score": None,
             "star_rating": 4, "class_year": None, "hs_grad_year": 2027, "total_followers": 0}
        # 150000 * 1.0 * 1.0 * 0.80 = 120,000
        assert calculate_valuation(p, 1.0) == 120_000

    def test_hs_elite_qb_sec(self):
        p = {"player_tag": "High School Recruit", "is_on_depth_chart": False,
             "position": "QB", "production_score": None, "composite_score": 99.0,
             "star_rating": 5, "class_year": None, "hs_grad_year": 2026, "total_followers": 20_000}
        # 800000 * 2.0 * 1.3 * 0.80 = 1,664,000 + 20000 = 1,684,000
        assert calculate_valuation(p, 1.3) == 1_684_000


class TestHsBaseValue:
    def test_99_5(self): assert hs_base_value(99.5, 5) == 800_000
    def test_98_5(self): assert hs_base_value(98.5, 5) == 575_000
    def test_97_0(self): assert hs_base_value(97.0, 5) == 375_000
    def test_96_5(self): assert hs_base_value(96.5, 4) == 275_000
    def test_95_2(self): assert hs_base_value(95.2, 4) == 200_000
    def test_94_0(self): assert hs_base_value(94.0, 4) == 175_000
    def test_93_5(self): assert hs_base_value(93.5, 4) == 150_000
    def test_91_5(self): assert hs_base_value(91.5, 4) == 125_000
    def test_89_5(self): assert hs_base_value(89.5, 4) == 100_000
    def test_null_5star(self): assert hs_base_value(None, 5) == 450_000
    def test_null_4star(self): assert hs_base_value(None, 4) == 150_000
    def test_below_min(self): assert hs_base_value(85.0, 4) == 150_000


class TestHsPositionPremium:
    def test_qb(self): assert hs_position_premium("QB") == 2.0
    def test_ot(self): assert hs_position_premium("OT") == 1.5
    def test_wr(self): assert hs_position_premium("WR") == 1.1
    def test_rb(self): assert hs_position_premium("RB") == 0.85
    def test_null(self): assert hs_position_premium(None) == 1.0
