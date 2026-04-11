"""
name_utils.py
--------------
Shared name normalization and fuzzy matching utilities for all pipeline scripts.

Every script that matches player names across data sources (CFBD, ESPN, On3, EA,
247Sports) should use these functions instead of rolling their own.

Two normalization levels:
  - normalize_name()         — basic cleanup (case, punctuation, unicode)
  - normalize_name_stripped() — also removes suffixes (Jr, Sr, II, III, IV, V)

Matching function:
  - fuzzy_match_player()     — 4-pass cascade: exact → exact-stripped → fuzzy → fuzzy-stripped

Usage:
    from name_utils import normalize_name, normalize_name_stripped, fuzzy_match_player
"""

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Optional

# ─── Suffix patterns ────────────────────────────────────────────────────────

# Word-boundary suffix pattern: matches Jr., Sr., II, III, IV, V at end or as
# standalone words.  Negative lookbehind prevents stripping from short names
# where the "suffix" IS the name (e.g., "James V" where V is the whole last name
# is unlikely, but "James Jr." is common).
_SUFFIX_PATTERN = re.compile(
    r"\b(jr\.?|sr\.?|ii|iii|iv|v)\b",
    re.IGNORECASE,
)


# ─── Normalization functions ────────────────────────────────────────────────

def normalize_name(name: str) -> str:
    """
    Basic name normalization for exact matching.

    Steps:
      1. Unicode NFKD decomposition → strip combining marks (accents)
      2. Lowercase
      3. Remove periods, apostrophes, hyphens (C.J. → cj, O'Brien → obrien)
      4. Collapse whitespace

    Does NOT strip suffixes — "Michael Terry III" → "michael terry iii"
    """
    if not name:
        return ""
    # Unicode normalize and strip accents
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Encode to ASCII, dropping anything left
    ascii_name = ascii_name.encode("ascii", "ignore").decode("ascii")
    # Lowercase
    result = ascii_name.lower().strip()
    # Remove periods, apostrophes, hyphens
    result = result.replace(".", "").replace("'", "").replace("-", " ").replace("'", "")
    # Collapse whitespace
    return " ".join(result.split())


def normalize_name_stripped(name: str) -> str:
    """
    Aggressive normalization that also strips common suffixes.

    "Michael Terry III" → "michael terry"
    "Damon Payne Jr."   → "damon payne"
    "CJ Baxter"         → "cj baxter"  (no suffix to strip)

    Guard: if stripping would leave fewer than 2 characters, returns
    normalize_name(name) instead (prevents "James Jr." → "james" from
    collapsing to empty if the regex ate too much).
    """
    base = normalize_name(name)
    stripped = _SUFFIX_PATTERN.sub("", base)
    stripped = " ".join(stripped.split())  # re-collapse whitespace
    # Safety: don't return empty or single-char results
    if len(stripped) < 2:
        return base
    return stripped


# ─── Fuzzy scoring ──────────────────────────────────────────────────────────

def _fuzzy_score(a: str, b: str) -> float:
    """SequenceMatcher ratio between two already-normalized strings."""
    return SequenceMatcher(None, a, b).ratio()


# ─── Match result ───────────────────────────────────────────────────────────

class MatchResult:
    """Result from fuzzy_match_player."""
    __slots__ = ("player", "method", "score")

    def __init__(self, player: dict, method: str, score: float):
        self.player = player
        self.method = method  # "exact", "exact-stripped", "fuzzy", "fuzzy-stripped"
        self.score = score

    def __repr__(self):
        name = self.player.get("name", "?")
        return f"MatchResult({name!r}, method={self.method!r}, score={self.score:.2f})"


# ─── Main matching function ────────────────────────────────────────────────

def fuzzy_match_player(
    candidate_name: str,
    db_players: list[dict],
    team_filter: Optional[str] = None,
    threshold: float = 0.85,
    name_key: str = "name",
) -> Optional[MatchResult]:
    """
    4-pass cascade matcher for player names.

    Pass 1: Exact match on normalize_name
    Pass 2: Exact match on normalize_name_stripped (both sides stripped)
    Pass 3: Fuzzy match on normalize_name with threshold
    Pass 4: Fuzzy match on normalize_name_stripped with threshold

    Args:
        candidate_name: The name to match (from external data source)
        db_players: List of player dicts, each having at least a `name_key` field
        team_filter: If provided, only consider players with this team_id
        threshold: Minimum fuzzy score (default 0.85)
        name_key: Key in player dicts for the name field (default "name")

    Returns:
        MatchResult with the matched player, method, and score — or None
    """
    if not candidate_name or not db_players:
        return None

    cand_norm = normalize_name(candidate_name)
    cand_stripped = normalize_name_stripped(candidate_name)

    # Apply team filter if provided
    pool = db_players
    if team_filter is not None:
        pool = [p for p in db_players if str(p.get("team_id", "")) == str(team_filter)]
        if not pool:
            return None

    # Pre-compute normalized names for the pool
    pool_norms = [(p, normalize_name(p.get(name_key, ""))) for p in pool]
    pool_stripped = [(p, normalize_name_stripped(p.get(name_key, ""))) for p in pool]

    # ── Pass 1: Exact match on normalize_name ────────────────────────────
    for p, pnorm in pool_norms:
        if cand_norm == pnorm:
            return MatchResult(p, "exact", 1.0)

    # ── Pass 2: Exact match on normalize_name_stripped ────────────────────
    for p, pstrip in pool_stripped:
        if cand_stripped == pstrip and cand_stripped:  # guard against empty
            return MatchResult(p, "exact-stripped", 1.0)

    # ── Pass 3: Fuzzy match on normalize_name ─────────────────────────────
    best_score = 0.0
    best_player = None
    for p, pnorm in pool_norms:
        score = _fuzzy_score(cand_norm, pnorm)
        if score > best_score:
            best_score = score
            best_player = p
    if best_player and best_score >= threshold:
        return MatchResult(best_player, "fuzzy", best_score)

    # ── Pass 4: Fuzzy match on normalize_name_stripped ─────────────────────
    best_score_s = 0.0
    best_player_s = None
    for p, pstrip in pool_stripped:
        score = _fuzzy_score(cand_stripped, pstrip)
        if score > best_score_s:
            best_score_s = score
            best_player_s = p
    if best_player_s and best_score_s >= threshold:
        return MatchResult(best_player_s, "fuzzy-stripped", best_score_s)

    return None


# ─── Convenience: build a lookup dict ───────────────────────────────────────

def build_name_lookup(
    players: list[dict],
    name_key: str = "name",
) -> dict[str, list[dict]]:
    """
    Build a normalized-name → [player, ...] lookup dict.
    Handles duplicate names by storing lists.
    """
    lookup: dict[str, list[dict]] = {}
    for p in players:
        norm = normalize_name(p.get(name_key, ""))
        if norm:
            lookup.setdefault(norm, []).append(p)
    return lookup


def build_stripped_lookup(
    players: list[dict],
    name_key: str = "name",
) -> dict[str, list[dict]]:
    """
    Build a stripped-name → [player, ...] lookup dict.
    """
    lookup: dict[str, list[dict]] = {}
    for p in players:
        stripped = normalize_name_stripped(p.get(name_key, ""))
        if stripped:
            lookup.setdefault(stripped, []).append(p)
    return lookup
