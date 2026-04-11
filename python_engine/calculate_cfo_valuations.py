"""
calculate_cfo_valuations.py  —  V3.1
--------------------------------------
Master valuation engine for College Front Office.

Specification: VALUATION_ENGINE.md (project root)

Formula:
    STEP 1 — Override Check (runs FIRST — bypasses eligibility gate):
        IF is_override AND nil_overrides row exists → use annualized_value

    STEP 0 — Eligibility Gate (only reached if not an override):
        IF college athlete AND is_on_depth_chart != True  → cfo_valuation = NULL
        IF HS recruit AND star_rating < 4                 → cfo_valuation = NULL

    STEP 2 — Algorithmic:
        football_value = position_base_value(position)
                         × draft_premium(nfl_draft_projection)
                         × talent_modifier(production_score, star_rating)
                         × market_multiplier(team.market_multiplier)  [clamped 0.8–1.3]
                         × experience_multiplier(player_tag, class_year, hs_grad_year)

        social_premium = min(total_followers × $1.00, $150,000)
        cfo_valuation  = max(int(football_value + social_premium), 10_000)

Usage:
    python calculate_cfo_valuations.py

Requirements:
    pip install -r requirements.txt
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import datetime
from supabase_client import supabase   # service-role client — bypasses RLS

# ─── Position base values ────────────────────────────────────────────────────
# VALUATION_ENGINE.md §3.2

POSITION_BASE_VALUES: dict[str, int] = {
    "QB":   1_500_000,
    "OT":     800_000,
    "EDGE":   700_000,
    "DE":     700_000,   # alias for EDGE
    "DT":     600_000,
    "DL":     600_000,   # generic defensive line (alias for DT)
    "WR":     550_000,
    "CB":     500_000,
    "OG":     475_000,
    "C":      475_000,
    "IOL":    475_000,   # alias for OG/C
    "OL":     475_000,   # generic offensive line
    "S":      450_000,
    "RB":     400_000,
    "TE":     325_000,
    "LB":     325_000,
    "K":      100_000,
    "P":      100_000,
    "ATH":    400_000,   # athlete/utility
    "LS":     100_000,   # long snapper
}
DEFAULT_BASE_VALUE = 400_000  # unknown/unrecognized position

# ─── Experience multiplier map ────────────────────────────────────────────────
# Monotonically increasing — VALUATION_ENGINE.md §3.6

COLLEGE_YOE_MAP: dict[int, float] = {
    1: 0.90,   # Freshman
    2: 1.00,   # Sophomore (baseline)
    3: 1.10,   # Junior
    4: 1.15,   # Senior
    5: 1.20,   # Super Senior / 5th year
}

CURRENT_YEAR = 2026   # Fall 2026 season — update annually
SOCIAL_CAP   = 150_000

# ─── Position starter counts ────────────────────────────────────────────────
# How many players at each position are "starters" in a typical formation.
# VALUATION_ENGINE.md §3.8

POSITION_STARTER_COUNTS: dict[str, int] = {
    "QB": 1, "RB": 1, "TE": 2, "K": 1, "P": 1, "LS": 1, "PK": 1,
    "WR": 3,
    "OL": 5, "OT": 5, "OG": 5, "C": 5, "IOL": 5,
    "EDGE": 2, "DE": 2,
    "DT": 2, "DL": 2,
    "LB": 3, "DB": 3,
    "CB": 2,
    "S": 2,
    "ATH": 1,
}

SINGLE_STARTER_POSITIONS = {"QB", "RB", "K", "P", "LS", "PK", "ATH"}


# ─── Component functions ──────────────────────────────────────────────────────

def is_eligible_for_valuation(player: dict, is_override: bool = False) -> bool:
    """
    Eligibility gate. Only called AFTER the override check — override players
    always bypass this gate (is_override=True → always returns True).
    Returns True if the player should receive an algorithmic valuation.
    Returns False if cfo_valuation should be set to NULL.
    VALUATION_ENGINE.md §3.0
    """
    if is_override:
        return True  # verified deals are valid regardless of depth chart status

    tag = (player.get("player_tag") or "").strip()

    if tag == "College Athlete":
        # Must be on an Ourlads depth chart
        return player.get("is_on_depth_chart") is True

    if tag == "High School Recruit":
        # Must be 4★ or 5★
        star = player.get("star_rating") or 0
        return star >= 4

    return True  # unknown tag — be conservative, include


def position_base_value(position: str | None) -> int:
    """VALUATION_ENGINE.md §3.2"""
    if position is None:
        return DEFAULT_BASE_VALUE
    return POSITION_BASE_VALUES.get(position.upper().strip(), DEFAULT_BASE_VALUE)


def draft_premium(nfl_draft_projection: int | None) -> float:
    """
    Maps draft pick number to a multiplier.
    Sentinel values (None, 0, ≥500 including 999) → 1.0 (neutral, no data).
    Key change from V3: None → 1.0 instead of 0.75.
    VALUATION_ENGINE.md §3.3
    """
    if nfl_draft_projection is None or nfl_draft_projection == 0:
        return 1.0
    p = int(nfl_draft_projection)
    if p >= 500:
        return 1.0    # includes sentinel 999
    if p <= 5:    return 2.50
    if p <= 15:   return 1.90
    if p <= 32:   return 1.50
    if p <= 64:   return 1.25
    if p <= 100:  return 1.10
    if p <= 180:  return 1.00
    return 0.90   # 181–499: late-round / fringe


def talent_modifier(
    production_score: float | None,
    star_rating: int | None,
    ea_rating: int | None = None,
) -> float:
    """
    Three-tier talent assessment.
    1. production_score > 0  → use production tiers (primary signal).
    2. ea_rating exists      → use EA OVR tiers (video game fallback).
    3. star_rating           → use star proxy (last resort).
    VALUATION_ENGINE.md §3.4
    """
    has_production = (
        production_score is not None
        and float(production_score) > 0
    )

    if has_production:
        ps = float(production_score)
        if ps >= 90: return 1.4
        if ps >= 75: return 1.2
        if ps >= 50: return 1.0
        if ps >= 25: return 0.65
        return 0.4

    # Fallback 1: EA rating (calibrated to match production tiers)
    if ea_rating is not None and int(ea_rating) > 0:
        ea = int(ea_rating)
        if ea >= 90: return 1.4
        if ea >= 82: return 1.2
        if ea >= 75: return 1.0
        if ea >= 68: return 0.65
        return 0.4

    # Fallback 2: star rating proxy (widened band — V3.6b)
    star = star_rating or 0
    if star >= 5:  return 1.30
    if star == 4:  return 1.00
    if star == 3:  return 0.80
    if star >= 1:  return 0.65
    return 0.70   # no talent data at all — penalty (V3.6b)


def market_multiplier(team_market_multiplier: float | None) -> float:
    """
    Program financial ecosystem multiplier. Clamped to [0.8, 1.3].
    VALUATION_ENGINE.md §3.5
    """
    if team_market_multiplier is None:
        return 1.0
    return max(0.8, min(1.3, float(team_market_multiplier)))


def experience_multiplier(
    player_tag: str | None,
    class_year: int | str | None,
    hs_grad_year: int | None,
) -> float:
    """
    Monotonically increasing experience curve. Replaces yoe_multiplier from V3.
    For HS recruits: derived from hs_grad_year.
    For college athletes: derived from class_year (1–5).
    VALUATION_ENGINE.md §3.6
    """
    tag = (player_tag or "").strip()

    if tag == "High School Recruit":
        if hs_grad_year is not None:
            gy = int(hs_grad_year)
            if gy <= CURRENT_YEAR + 1:    # 2027 or earlier = HS senior
                return 0.80
            elif gy == CURRENT_YEAR + 2:  # 2028 = HS junior
                return 0.35
            else:
                return 0.25   # 2029+ = HS underclassman
        return 0.75  # unknown HS grad year — conservative default

    # College athlete
    if class_year is None:
        return 1.0
    try:
        cy = int(class_year)
    except (TypeError, ValueError):
        return 1.0
    return COLLEGE_YOE_MAP.get(cy, 1.0)


def depth_chart_rank_multiplier(
    depth_chart_rank: int | None,
    is_on_depth_chart: bool | None,
    position: str | None = None,
    star_rating: int | None = None,
    class_year: int | str | None = None,
) -> float:
    """
    Position-aware depth chart multiplier with recruiting pedigree floor.
    Multi-starter positions (OL, WR, LB, DL, CB, S, EDGE) treat more players
    as starters and apply softer backup discounts.
    Single-starter positions (QB, RB, TE, K, P) use steeper backup discounts.

    Pedigree floor (§3.8.1): elite recruits who haven't yet had a full
    opportunity to earn playing time keep a minimum multiplier:
      5★, class_year <= 3 → floor 1.0
      4★, class_year <= 3 → floor 0.85
    VALUATION_ENGINE.md §3.8
    """
    if not is_on_depth_chart:
        return 0.12

    pos = (position or "").upper().strip()
    starter_count = POSITION_STARTER_COUNTS.get(pos, 1)
    is_single = pos in SINGLE_STARTER_POSITIONS

    # ── Graduated starter multiplier (V3.6b) ───────────────────────────
    STARTER_GRADIENT = {1: 1.0, 2: 0.90, 3: 0.80, 4: 0.75, 5: 0.70}

    if depth_chart_rank is None:
        raw = 0.55  # unknown rank — conservative
    elif depth_chart_rank <= starter_count:
        if is_single:
            raw = 1.0  # single-starter: rank 1 always 1.0
        else:
            raw = STARTER_GRADIENT.get(depth_chart_rank, 0.70)
    else:
        backup_depth = depth_chart_rank - starter_count
        if is_single:
            if backup_depth == 1:
                raw = 0.35
            elif backup_depth == 2:
                raw = 0.20
            else:
                raw = 0.12
        else:
            if backup_depth == 1:
                raw = 0.55
            elif backup_depth == 2:
                raw = 0.40
            else:
                raw = 0.25

    # ── Recruiting pedigree floor ────────────────────────────────────────
    star = star_rating or 0
    try:
        cy = int(class_year) if class_year is not None else 99
    except (TypeError, ValueError):
        cy = 99

    if cy <= 3 and star >= 5:
        return max(raw, 1.0)
    if cy <= 3 and star == 4:
        return max(raw, 0.45)

    return raw


def social_premium(total_followers: int | None) -> float:
    """
    $1.00 per follower, hard-capped at $150,000.
    VALUATION_ENGINE.md §3.7
    """
    if total_followers is None or total_followers <= 0:
        return 0.0
    return min(float(total_followers), float(SOCIAL_CAP))


# ─── HS Recruit valuation ────────────────────────────────────────────────────
# Composite-score-driven path for High School Recruits.
# VALUATION_ENGINE.md §4

HS_COMPOSITE_TIERS: list[tuple[float, int]] = [
    (99.0, 800_000),
    (98.0, 575_000),
    (97.0, 375_000),
    (96.0, 275_000),
    (95.0, 200_000),
    (94.0, 175_000),
    (93.0, 150_000),
    (91.0, 125_000),
    (89.0, 100_000),
]

HS_STAR_FALLBACK: dict[int, int] = {5: 450_000, 4: 150_000}


def hs_base_value(composite_score: float | None, star_rating: int | None) -> int:
    """Primary: composite tier. Fallback: star rating."""
    if composite_score is not None and float(composite_score) >= 89.0:
        cs = float(composite_score)
        for threshold, value in HS_COMPOSITE_TIERS:
            if cs >= threshold:
                return value
    star = star_rating or 0
    return HS_STAR_FALLBACK.get(star, 100_000)


HS_POSITION_PREMIUMS: dict[str, float] = {
    "QB": 2.0, "OT": 1.5, "LT": 1.5,
    "OL": 1.2, "OG": 1.2, "C": 1.2, "IOL": 1.2,
    "WR": 1.1, "EDGE": 1.1, "DE": 1.1, "DT": 1.1, "DL": 1.1,
    "CB": 1.05, "LB": 1.0, "S": 1.0, "TE": 0.9, "RB": 0.85,
    "ATH": 1.0, "K": 0.5, "P": 0.5, "LS": 0.5, "DB": 1.0,
}


def hs_position_premium(position: str | None) -> float:
    if position is None:
        return 1.0
    return HS_POSITION_PREMIUMS.get(position.upper().strip(), 1.0)


# ─── Core calculation ─────────────────────────────────────────────────────────

def _get_total_followers(player: dict) -> int:
    """Prefer pre-computed total_followers; fall back to summing platform columns."""
    total = player.get("total_followers")
    if total is not None:
        return total
    return (
        (player.get("ig_followers") or 0)
        + (player.get("x_followers") or 0)
        + (player.get("tiktok_followers") or 0)
    )


def calculate_valuation(player: dict, team_multiplier: float) -> int:
    """
    Compute cfo_valuation for a single eligible algorithmic player.
    Routes HS recruits through composite-based formula, college athletes
    through production/draft-based formula.
    Returns an integer >= $10,000.
    """
    tag = (player.get("player_tag") or "").strip()
    followers = _get_total_followers(player)
    soc = social_premium(followers)
    mkt_mult = market_multiplier(team_multiplier)
    exp_mult = experience_multiplier(
        player.get("player_tag"),
        player.get("class_year"),
        player.get("hs_grad_year"),
    )

    if tag == "High School Recruit":
        # HS formula: composite-based
        base = hs_base_value(player.get("composite_score"), player.get("star_rating"))
        pos_prem = hs_position_premium(player.get("position"))
        football_value = base * pos_prem * mkt_mult * exp_mult
    else:
        # College formula: production/draft-based
        base = position_base_value(player.get("position"))
        draft_mult = draft_premium(player.get("nfl_draft_projection"))
        talent_mod = talent_modifier(
            player.get("production_score"),
            player.get("star_rating"),
            player.get("ea_rating"),
        )
        dc_rank_mult = depth_chart_rank_multiplier(
            player.get("depth_chart_rank"),
            player.get("is_on_depth_chart"),
            player.get("position"),
            player.get("star_rating"),
            player.get("class_year"),
        )
        football_value = base * draft_mult * talent_mod * mkt_mult * exp_mult * dc_rank_mult

    return max(int(football_value + soc), 10_000)


# ─── Data fetching ────────────────────────────────────────────────────────────

def fetch_nil_overrides() -> dict[str, int]:
    """
    Returns overrides_map: player_id → highest annualized_value.
    Fetched in one query. VALUATION_ENGINE.md §3.1
    """
    print("Fetching nil_overrides...")
    resp = supabase.table("nil_overrides").select("player_id, annualized_value").execute()
    overrides: dict[str, int] = {}
    for row in resp.data or []:
        pid = str(row.get("player_id", ""))
        val = row.get("annualized_value") or 0
        if pid and val:
            if val > overrides.get(pid, 0):
                overrides[pid] = int(val)
    print(f"  {len(overrides)} override(s) loaded.\n")
    return overrides


def fetch_teams() -> tuple[dict[str, float], dict[str, str]]:
    """Returns (multipliers: team_id→float, names: team_id→str)."""
    print("Fetching teams...")
    resp = (
        supabase.table("teams")
        .select("id, university_name, market_multiplier")
        .execute()
    )
    multipliers: dict[str, float] = {}
    names: dict[str, str]         = {}
    for row in resp.data or []:
        tid               = str(row["id"])
        multipliers[tid]  = float(row.get("market_multiplier") or 1.0)
        names[tid]        = row.get("university_name") or "Unknown"
    print(f"  {len(multipliers)} team(s) loaded.\n")
    return multipliers, names


def fetch_players() -> list[dict]:
    """
    Fetches all players with every column required for V3.1 valuation.
    Includes: player_tag, is_on_depth_chart, star_rating, hs_grad_year (all new vs V3).
    Paginates at 1,000 rows.
    """
    PAGE_SIZE    = 1_000
    all_players: list[dict] = []
    offset       = 0

    print("Fetching players from Supabase...")
    while True:
        resp = (
            supabase.table("players")
            .select(
                "id, name, player_tag, is_override, is_on_depth_chart, "
                "position, star_rating, team_id, class_year, hs_grad_year, "
                "nfl_draft_projection, production_score, depth_chart_rank, "
                "composite_score, ea_rating, "
                "total_followers, ig_followers, x_followers, tiktok_followers"
            )
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    print(f"  {len(all_players)} player(s) fetched.\n")
    return all_players


# ─── Update loop ──────────────────────────────────────────────────────────────

BATCH_SIZE = 500


def run_valuations(
    players: list[dict],
    multipliers: dict[str, float],
    names: dict[str, str],
    overrides_map: dict[str, int],
) -> tuple[list[dict], dict]:
    """
    Compute and batch-upsert cfo_valuation for every player.
    Returns (results_list, stats_dict) for the summary report.
    Ineligible players get cfo_valuation = NULL (also upserted).
    """
    print("=" * 65)
    print(f"Computing CFO Valuations (V3.1) for {len(players)} players…")
    print("=" * 65)

    now    = datetime.datetime.utcnow().isoformat()
    batch: list[dict] = []
    results: list[dict] = []

    # Counters
    eligible_count       = 0
    ineligible_off_dc    = 0   # college athlete, not on depth chart
    ineligible_low_star  = 0   # HS recruit < 4★
    override_count       = 0
    errors               = 0
    eligible_valuations: list[int] = []

    for player in players:
        pid     = str(player["id"])
        tag     = (player.get("player_tag") or "").strip()
        team_id = player.get("team_id")

        multiplier = multipliers.get(str(team_id), 1.0) if team_id else 1.0
        team_name  = names.get(str(team_id), "Unknown") if team_id else "Unknown"

        # ── STEP 1: Override check (runs FIRST — verified deals bypass the gate) ──
        if player.get("is_override") is True:
            if pid in overrides_map:
                valuation      = overrides_map[pid]
                is_override    = True
                override_count += 1
                eligible_count += 1
                eligible_valuations.append(valuation)
                batch.append({
                    "id":            pid,
                    "cfo_valuation": valuation,
                    "is_override":   True,
                    "last_updated":  now,
                })
                results.append({
                    "name":        player.get("name") or "—",
                    "team":        team_name,
                    "position":    (player.get("position") or "ATH").upper().strip(),
                    "valuation":   valuation,
                    "is_override": True,
                })
                if len(batch) >= BATCH_SIZE:
                    _flush_batch(batch)
                    batch = []
                continue
            else:
                print(
                    f"  ⚠  WARNING: {player.get('name')} has is_override=True "
                    "but no nil_overrides row. Falling through to eligibility gate."
                )
                # Fall through to gate + algorithm below

        # ── STEP 0: Eligibility gate ──────────────────────────────────────────
        if not is_eligible_for_valuation(player):
            if tag == "College Athlete":
                ineligible_off_dc += 1
            elif tag == "High School Recruit":
                ineligible_low_star += 1
            # Upsert NULL valuation — profile is visible, no dollar figure
            batch.append({"id": pid, "cfo_valuation": None, "last_updated": now})
            if len(batch) >= BATCH_SIZE:
                _flush_batch(batch)
                batch = []
            continue

        eligible_count += 1

        # ── STEP 2: Algorithmic calculation ───────────────────────────────────
        try:
            valuation   = calculate_valuation(player, multiplier)
            is_override = False
        except Exception as exc:
            print(f"  [ERROR] {player.get('name')}: {exc}")
            errors += 1
            continue

        eligible_valuations.append(valuation)
        batch.append({
            "id":            pid,
            "cfo_valuation": valuation,
            "is_override":   is_override,
            "last_updated":  now,
        })
        results.append({
            "name":        player.get("name") or "—",
            "team":        team_name,
            "position":    (player.get("position") or "ATH").upper().strip(),
            "valuation":   valuation,
            "is_override": is_override,
        })

        if len(batch) >= BATCH_SIZE:
            _flush_batch(batch)
            batch = []

    # Flush remainder
    if batch:
        _flush_batch(batch)

    stats = {
        "total":               len(players),
        "eligible":            eligible_count,
        "overrides":           override_count,
        "ineligible_total":    ineligible_off_dc + ineligible_low_star,
        "ineligible_off_dc":   ineligible_off_dc,
        "ineligible_low_star": ineligible_low_star,
        "errors":              errors,
        "valuations":          eligible_valuations,
    }
    return results, stats


def _flush_batch(batch: list[dict]) -> None:
    """Upsert a batch of player valuation rows to Supabase.
    Falls back to row-by-row updates if the batch fails."""
    try:
        supabase.table("players").upsert(batch, on_conflict="id").execute()
    except Exception as exc:
        print(f"  [BATCH ERROR] {exc}")
        print(f"  Retrying {len(batch)} rows individually...")
        for row in batch:
            try:
                update_data = {k: v for k, v in row.items() if k != "id"}
                supabase.table("players").update(update_data).eq("id", row["id"]).execute()
            except Exception as row_exc:
                print(f"    [ROW ERROR] {row['id']}: {row_exc}")


# ─── Summary report ───────────────────────────────────────────────────────────

def print_summary(results: list[dict], stats: dict, top_n: int = 20) -> None:
    vals    = stats["valuations"]
    header  = f"{'RK':<4}  {'NAME':<28}  {'TEAM':<22}  {'POS':<5}  {'CFO VALUATION':>14}"
    divider = "─" * len(header)
    ranked  = sorted(results, key=lambda r: r["valuation"], reverse=True)[:top_n]

    print("=" * len(header))
    print(f"  TOP {top_n} CFO VALUATIONS — V3.1")
    print("=" * len(header))
    print(header)
    print(divider)
    for rank, r in enumerate(ranked, start=1):
        flag = " ✓" if r.get("is_override") else ""
        print(
            f"{rank:<4}  {r['name']:<28}  {r['team']:<22}  "
            f"{r['position']:<5}  ${r['valuation']:>13,}{flag}"
        )
    print(divider)
    print(f"  Total processed    : {stats['total']:,}")
    print(f"  Eligible           : {stats['eligible']:,}")
    print(f"    Algorithmic      : {stats['eligible'] - stats['overrides']:,}")
    print(f"    Override (✓)     : {stats['overrides']:,}")
    print(f"  Ineligible         : {stats['ineligible_total']:,}")
    print(f"    Off depth chart  : {stats['ineligible_off_dc']:,}")
    print(f"    HS recruit <4★   : {stats['ineligible_low_star']:,}")
    if vals:
        print(f"  Valuation range    : ${min(vals):,} – ${max(vals):,}")
        print(f"  Avg valuation      : ${sum(vals) // len(vals):,}")
    print(f"  Errors             : {stats['errors']}")
    print(f"  ✓ = Verified NIL override (annualized_value from nil_overrides)")
    print("=" * len(header))


# ─── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    overrides_map      = fetch_nil_overrides()
    multipliers, names = fetch_teams()
    players            = fetch_players()

    if not players:
        print("No players found in Supabase. Exiting.")
        return

    results, stats = run_valuations(players, multipliers, names, overrides_map)
    print_summary(results, stats)


if __name__ == "__main__":
    main()
