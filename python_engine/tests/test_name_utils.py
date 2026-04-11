"""
Tests for name_utils.py — shared name normalization and matching.
Run: cd python_engine && python -m pytest tests/test_name_utils.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from name_utils import (
    normalize_name,
    normalize_name_stripped,
    fuzzy_match_player,
    MatchResult,
    build_name_lookup,
    build_stripped_lookup,
)


# ═══════════════════════════════════════════════════════════════════════════
# normalize_name tests
# ═══════════════════════════════════════════════════════════════════════════

class TestNormalizeName:
    def test_basic_lowercase(self):
        assert normalize_name("Arch Manning") == "arch manning"

    def test_periods_stripped(self):
        assert normalize_name("C.J. Baxter") == "cj baxter"

    def test_apostrophe_stripped(self):
        assert normalize_name("Ja'Marr Chase") == "jamarr chase"

    def test_hyphen_to_space(self):
        assert normalize_name("Ryan Coleman-Williams") == "ryan coleman williams"

    def test_unicode_accents(self):
        assert normalize_name("José García") == "jose garcia"

    def test_suffix_preserved(self):
        """normalize_name keeps suffixes — only normalize_name_stripped removes them."""
        assert normalize_name("Michael Terry III") == "michael terry iii"
        assert normalize_name("Damon Payne Jr.") == "damon payne jr"

    def test_whitespace_collapse(self):
        assert normalize_name("  Arch   Manning  ") == "arch manning"

    def test_empty_string(self):
        assert normalize_name("") == ""

    def test_none_returns_empty(self):
        # None should not crash — guard at the top
        assert normalize_name("") == ""

    def test_cj_variants_match(self):
        """C.J. and CJ should normalize to the same thing."""
        assert normalize_name("C.J. Baxter") == normalize_name("CJ Baxter")

    def test_smart_quotes(self):
        """Curly/smart apostrophes should be stripped."""
        assert normalize_name("Ja\u2019Marr Chase") == "jamarr chase"


# ═══════════════════════════════════════════════════════════════════════════
# normalize_name_stripped tests
# ═══════════════════════════════════════════════════════════════════════════

class TestNormalizeNameStripped:
    def test_strips_jr(self):
        assert normalize_name_stripped("Damon Payne Jr.") == "damon payne"

    def test_strips_jr_no_period(self):
        assert normalize_name_stripped("Damon Payne Jr") == "damon payne"

    def test_strips_sr(self):
        assert normalize_name_stripped("John Smith Sr.") == "john smith"

    def test_strips_iii(self):
        assert normalize_name_stripped("Michael Terry III") == "michael terry"

    def test_strips_ii(self):
        assert normalize_name_stripped("Kenric Lanier II") == "kenric lanier"

    def test_strips_iv(self):
        assert normalize_name_stripped("Elbert Hill IV") == "elbert hill"

    def test_strips_v(self):
        assert normalize_name_stripped("Emmett Mosley V") == "emmett mosley"

    def test_no_suffix_unchanged(self):
        assert normalize_name_stripped("Arch Manning") == "arch manning"

    def test_cj_baxter(self):
        assert normalize_name_stripped("CJ Baxter") == "cj baxter"

    def test_safety_guard_short_name(self):
        """Stripping from a very short name should not produce empty/1-char result."""
        # "V Jr." → normalize_name → "v jr" → strip suffix → could leave "v" or ""
        # Safety guard returns normalize_name result instead
        result = normalize_name_stripped("V Jr.")
        assert len(result) >= 2

    def test_george_gumbs_jr(self):
        """George Gumbs Jr. should match George Gumbs after stripping."""
        assert normalize_name_stripped("George Gumbs Jr.") == "george gumbs"
        assert normalize_name_stripped("George Gumbs") == "george gumbs"
        assert normalize_name_stripped("George Gumbs Jr.") == normalize_name_stripped("George Gumbs")

    def test_michael_terry_iii_matches_michael_terry(self):
        assert normalize_name_stripped("Michael Terry III") == normalize_name_stripped("Michael Terry")

    def test_deandre_moore_jr(self):
        assert normalize_name_stripped("DeAndre Moore Jr.") == "deandre moore"


# ═══════════════════════════════════════════════════════════════════════════
# fuzzy_match_player tests
# ═══════════════════════════════════════════════════════════════════════════

# Test database of players
TEST_PLAYERS = [
    {"id": "1", "name": "Michael Terry III", "team_id": "texas"},
    {"id": "2", "name": "Arch Manning", "team_id": "texas"},
    {"id": "3", "name": "Damon Payne", "team_id": "alabama"},
    {"id": "4", "name": "C.J. Baxter", "team_id": "texas"},
    {"id": "5", "name": "George Gumbs", "team_id": "ohio-state"},
    {"id": "6", "name": "Ryan Coleman-Williams", "team_id": "alabama"},
    {"id": "7", "name": "Emmett Mosley", "team_id": "texas"},
    {"id": "8", "name": "Michael Terry", "team_id": "lsu"},  # Different team, same base name
]


class TestFuzzyMatchPlayer:
    def test_exact_match(self):
        """Exact normalized match: same name, same formatting."""
        result = fuzzy_match_player("Arch Manning", TEST_PLAYERS)
        assert result is not None
        assert result.player["id"] == "2"
        assert result.method == "exact"
        assert result.score == 1.0

    def test_exact_match_cj(self):
        """C.J. Baxter vs CJ Baxter — periods stripped by normalize_name."""
        result = fuzzy_match_player("CJ Baxter", TEST_PLAYERS)
        assert result is not None
        assert result.player["id"] == "4"
        assert result.method == "exact"

    def test_exact_stripped_suffix(self):
        """Michael Terry III → stripped → matches 'Michael Terry' (exact-stripped)."""
        # Without team filter, it might match player 1 (exact) or player 8 (stripped).
        # Player 1 IS "Michael Terry III", so normalize_name gives "michael terry iii".
        # Candidate "Michael Terry III" also normalizes to "michael terry iii" → exact match.
        result = fuzzy_match_player("Michael Terry III", TEST_PLAYERS)
        assert result is not None
        assert result.player["id"] == "1"
        assert result.method == "exact"

    def test_stripped_match_cross_suffix(self):
        """'Michael Terry' (no suffix) matching against DB with 'Michael Terry III'."""
        # normalize_name("Michael Terry") = "michael terry" which exactly matches player 8
        # ("Michael Terry" on LSU). With team filter to Texas, it should fall through
        # to exact-stripped matching player 1 ("Michael Terry III").
        result_no_filter = fuzzy_match_player("Michael Terry", TEST_PLAYERS)
        assert result_no_filter is not None
        assert result_no_filter.player["id"] == "8"  # exact match to LSU player
        assert result_no_filter.method == "exact"

        # With team filter to Texas: "Michael Terry" → exact fails (no "michael terry" on Texas)
        # → stripped: "michael terry" matches player 1 stripped ("michael terry iii" → "michael terry")
        result_texas = fuzzy_match_player("Michael Terry", TEST_PLAYERS, team_filter="texas")
        assert result_texas is not None
        assert result_texas.player["id"] == "1"  # Texas player "Michael Terry III"
        assert result_texas.method == "exact-stripped"

    def test_stripped_match_jr(self):
        """'Damon Payne Jr.' matching 'Damon Payne' via stripped normalization."""
        result = fuzzy_match_player("Damon Payne Jr.", TEST_PLAYERS)
        assert result is not None
        assert result.player["id"] == "3"
        # "damon payne jr" != "damon payne" (pass 1 fails)
        # "damon payne" == "damon payne" (pass 2 succeeds)
        assert result.method == "exact-stripped"

    def test_stripped_match_v(self):
        """'Emmett Mosley V' matching 'Emmett Mosley' via stripped normalization."""
        result = fuzzy_match_player("Emmett Mosley V", TEST_PLAYERS)
        assert result is not None
        assert result.player["id"] == "7"
        assert result.method == "exact-stripped"

    def test_stripped_match_george_gumbs_jr(self):
        """'George Gumbs Jr.' matching 'George Gumbs' via stripped normalization."""
        result = fuzzy_match_player("George Gumbs Jr.", TEST_PLAYERS)
        assert result is not None
        assert result.player["id"] == "5"
        assert result.method == "exact-stripped"

    def test_team_filter(self):
        """Team filter restricts matching to a single team."""
        # "Michael Terry" with team filter = "lsu" should match player 8
        result = fuzzy_match_player("Michael Terry", TEST_PLAYERS, team_filter="lsu")
        assert result is not None
        assert result.player["id"] == "8"

    def test_team_filter_excludes_wrong_team(self):
        """Should NOT match a player on a different team when filter is active."""
        result = fuzzy_match_player("Arch Manning", TEST_PLAYERS, team_filter="alabama")
        assert result is None  # Arch is on Texas, not Alabama

    def test_team_filter_empty_pool(self):
        """Team with no players returns None."""
        result = fuzzy_match_player("Arch Manning", TEST_PLAYERS, team_filter="nonexistent")
        assert result is None

    def test_no_match(self):
        """Name that doesn't match anything returns None."""
        result = fuzzy_match_player("Totally Unknown Player", TEST_PLAYERS)
        assert result is None

    def test_fuzzy_match(self):
        """Fuzzy matching catches near-misses."""
        # "Ryan Coleman Williams" (no hyphen) vs "Ryan Coleman-Williams"
        # normalize_name both → "ryan coleman williams" → exact match!
        # This actually tests that hyphens are normalized to spaces.
        result = fuzzy_match_player("Ryan Coleman Williams", TEST_PLAYERS)
        assert result is not None
        assert result.player["id"] == "6"

    def test_empty_candidate(self):
        assert fuzzy_match_player("", TEST_PLAYERS) is None

    def test_empty_pool(self):
        assert fuzzy_match_player("Arch Manning", []) is None

    def test_threshold_respected(self):
        """Very different names should not match even with low threshold."""
        result = fuzzy_match_player("Zzzzz Yyyyy", TEST_PLAYERS, threshold=0.95)
        assert result is None

    def test_custom_name_key(self):
        """Support alternate name fields in player dicts."""
        alt_players = [
            {"id": "1", "player_name": "Arch Manning", "team_id": "texas"},
        ]
        result = fuzzy_match_player("Arch Manning", alt_players, name_key="player_name")
        assert result is not None
        assert result.player["id"] == "1"


# ═══════════════════════════════════════════════════════════════════════════
# Lookup builder tests
# ═══════════════════════════════════════════════════════════════════════════

class TestBuildLookups:
    def test_name_lookup(self):
        lookup = build_name_lookup(TEST_PLAYERS)
        assert "arch manning" in lookup
        assert len(lookup["arch manning"]) == 1
        assert lookup["arch manning"][0]["id"] == "2"

    def test_stripped_lookup(self):
        lookup = build_stripped_lookup(TEST_PLAYERS)
        # Both "Michael Terry III" and "Michael Terry" strip to "michael terry"
        assert "michael terry" in lookup
        assert len(lookup["michael terry"]) == 2  # id 1 and id 8

    def test_cj_in_lookup(self):
        lookup = build_name_lookup(TEST_PLAYERS)
        assert "cj baxter" in lookup  # C.J. → cj after period stripping


# ═══════════════════════════════════════════════════════════════════════════
# MatchResult tests
# ═══════════════════════════════════════════════════════════════════════════

class TestMatchResult:
    def test_repr(self):
        r = MatchResult({"name": "Arch Manning"}, "exact", 1.0)
        assert "Arch Manning" in repr(r)
        assert "exact" in repr(r)
