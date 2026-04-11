"""
calculate_bball_valuations.py  —  Basketball V1
-------------------------------------------------
Valuation engine for College Front Office basketball.

Formula:
    basketball_value = position_base
                     × nba_draft_premium
                     × role_tier_multiplier
                     × talent_modifier
                     × market_multiplier
                     × experience_multiplier

    cfo_valuation = max(basketball_value + social_premium, 5000)

Usage:
    python calculate_bball_valuations.py              # all teams
    python calculate_bball_valuations.py --dry-run    # preview only
    python calculate_bball_valuations.py --team byu   # single team
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

from supabase_client import supabase

# ─── Position base values ────────────────────────────────────────────────────
# Position bases calibrated to Power 4 market floor (2025-26).
# Mid-major and lower programs are scaled via market_multiplier (0.30-0.75).
# Blue blood programs (Duke, Kentucky, Kansas) use 1.25-1.35x.

POSITION_BASES: dict[str, int] = {
    "PG": 700_000,
    "SG": 600_000,
    "SF": 550_000,
    "PF": 500_000,
    "C":  450_000,
}

POSITION_BASE_FALLBACKS: dict[str, int] = {
    "G":  600_000,
    "F":  550_000,
}

DEFAULT_POSITION_BASE = 550_000  # default to SF-equivalent


def get_position_base(position: str | None) -> int:
    if position is None:
        return DEFAULT_POSITION_BASE
    pos = position.upper().strip()
    return (
        POSITION_BASES.get(pos)
        or POSITION_BASE_FALLBACKS.get(pos)
        or DEFAULT_POSITION_BASE
    )


# ─── NBA draft premium ──────────────────────────────────────────────────────

def get_nba_draft_premium(projected_pick: int | None) -> float:
    if projected_pick is None:
        return 1.00
    if projected_pick <= 5:     return 3.50
    if projected_pick <= 14:    return 2.60
    if projected_pick <= 30:    return 1.80
    if projected_pick <= 60:    return 1.25
    return 1.00


# ─── Role tier multiplier ───────────────────────────────────────────────────

ROLE_MULTIPLIERS: dict[str, float] = {
    "franchise": 2.20,
    "star":      1.65,
    "starter":   1.20,
    "rotation":  0.75,
    "bench":     0.30,
}

INCOMING_ROLE_MULTIPLIER = 0.60  # players with no college stats


def get_role_tier_multiplier(role_tier: str | None, has_stats: bool) -> float:
    if not has_stats:
        return INCOMING_ROLE_MULTIPLIER
    return ROLE_MULTIPLIERS.get(role_tier or "bench", 0.30)


# ─── Talent modifier ────────────────────────────────────────────────────────

def get_talent_modifier(
    star_rating: int | None,
    composite_score: float | None,
    per: float | None,
    has_stats: bool,
) -> float:
    # Players WITH stats: PER is the primary signal
    if has_stats and per is not None and float(per) > 0:
        p = float(per)
        if p >= 25:   return 1.30
        if p >= 20:   return 1.20
        if p >= 15:   return 1.10
        if p >= 10:   return 1.00
        return 0.90

    # Players WITHOUT stats (incoming): recruiting composite
    if composite_score is not None and float(composite_score) >= 0.9900:
        return 1.30  # 5-star
    if composite_score is not None and float(composite_score) >= 0.8900:
        return 1.15  # 4-star
    if star_rating is not None and int(star_rating) >= 3:
        return 1.00  # 3-star
    return 0.85      # 2-star or unranked


# ─── Experience multiplier ──────────────────────────────────────────────────

EXPERIENCE_MULTIPLIERS: dict[str, float] = {
    "Freshman":  0.85,
    "Sophomore": 0.95,
    "Junior":    1.05,
    "Senior":    1.10,
    "Graduate":  1.15,
}


def get_experience_multiplier(class_year: str | None) -> float:
    if class_year is None:
        return 0.90  # default near-freshman
    return EXPERIENCE_MULTIPLIERS.get(class_year.strip(), 0.90)


# ─── Market multiplier ──────────────────────────────────────────────────────

def get_market_multiplier(team_data: dict | None) -> float:
    if team_data is None:
        return 1.000
    mm = team_data.get("market_multiplier")
    if mm is None:
        return 1.000
    return max(0.80, min(1.30, float(mm)))


# ─── Social premium ─────────────────────────────────────────────────────────

def calculate_social_premium(
    ig: int | None, x: int | None, tiktok: int | None,
) -> int:
    ig_val = ig or 0
    x_val  = x or 0
    tk_val = tiktok or 0
    total  = ig_val + int(x_val * 0.7) + int(tk_val * 1.2)

    if total >= 1_000_000:  return 150_000
    if total >= 500_000:    return 75_000
    if total >= 100_000:    return 25_000
    if total >= 50_000:     return 10_000
    if total >= 10_000:     return 3_000
    return 0


# ─── Draft projections ─────────────────────────────────────────────────────
# Draft projections are read directly from basketball_players.nba_draft_projection.
# Updated by sync_nba_draft_projections.py (ESPN draft API).


# ─── Eligibility gate ──────────────────────────────────────────────────────

def is_eligible_for_valuation(player: dict) -> bool:
    """
    Determines whether a player participates in the NIL market.

    Eligible if ANY of the following:
    - MPG >= 8 (rotation player or higher — confirmed minutes in the program)
    - Incoming (no stats) AND star_rating >= 4 (blue-chip recruit)

    Ineligible:
    - Walk-ons and deep bench with minimal minutes
    - Low-ranked incoming players with no college track record
    """
    usage_rate = player.get("usage_rate") or 0
    has_stats = usage_rate > 0
    mpg = usage_rate * 40
    star_rating = player.get("star_rating") or 0

    if has_stats:
        return mpg >= 8.0
    else:
        return star_rating >= 4


# ─── Core valuation ─────────────────────────────────────────────────────────

VALUATION_FLOOR = 5_000


def compute_valuation(
    player: dict,
    team_data: dict | None,
    draft_pick: int | None,
) -> dict:
    """
    Compute cfo_valuation and return a breakdown dict.
    """
    has_stats = (player.get("usage_rate") or 0) > 0

    pos_base    = get_position_base(player.get("position"))
    draft_prem  = get_nba_draft_premium(draft_pick)
    role_mult   = get_role_tier_multiplier(player.get("role_tier"), has_stats)
    talent_mod  = get_talent_modifier(
        player.get("star_rating"),
        player.get("composite_score"),
        player.get("per"),
        has_stats,
    )
    market_mult = get_market_multiplier(team_data)
    exp_mult    = get_experience_multiplier(player.get("class_year"))
    social_prem = calculate_social_premium(
        player.get("ig_followers"),
        player.get("x_followers"),
        player.get("tiktok_followers"),
    )

    # If a draft projection exists (premium > 1.0), use the stronger
    # of draft signal vs role signal. If no draft data, role tier alone.
    # The neutral 1.00× draft baseline is absence of data, not a signal.
    if draft_prem > 1.0:
        combined_prem = max(draft_prem, role_mult)
    else:
        combined_prem = role_mult

    basketball_value = pos_base * combined_prem * talent_mod * market_mult * exp_mult
    valuation = max(int(basketball_value + social_prem), VALUATION_FLOOR)

    # Label for display
    if not has_stats:
        role_label = "incoming"
        talent_label = f"{player.get('star_rating') or '?'}-star" if player.get("star_rating") else "unranked"
    else:
        role_label = player.get("role_tier") or "bench"
        talent_label = f"PER {float(player.get('per') or 0):.1f}"

    draft_label = f"pick {draft_pick}" if draft_pick else "no draft"

    return {
        "valuation": valuation,
        "pos_base": pos_base,
        "draft_prem": draft_prem,
        "role_mult": role_mult,
        "combined_prem": combined_prem,
        "talent_mod": talent_mod,
        "market_mult": market_mult,
        "exp_mult": exp_mult,
        "social_prem": social_prem,
        "basketball_value": int(basketball_value),
        "role_label": role_label,
        "draft_label": draft_label,
        "talent_label": talent_label,
        "has_stats": has_stats,
    }


# ─── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    dry_run = "--dry-run" in sys.argv

    team_filter = None
    for i, arg in enumerate(sys.argv):
        if arg == "--team" and i + 1 < len(sys.argv):
            team_filter = sys.argv[i + 1].lower()

    print("Computing basketball valuations...\n")

    # Load teams
    teams_resp = supabase.table("basketball_teams").select("id, university_name, market_multiplier, slug").execute()
    teams_by_id: dict[str, dict] = {}
    for t in (teams_resp.data or []):
        teams_by_id[t["id"]] = t
    if team_filter:
        teams_by_id = {tid: t for tid, t in teams_by_id.items() if t.get("slug") == team_filter}

    print(f"Loading {len(teams_by_id)} team(s)...\n")

    # Load players
    query = (
        supabase.table("basketball_players")
        .select(
            "id, name, position, role_tier, usage_rate, ppg, rpg, apg, per, "
            "star_rating, composite_score, class_year, experience_level, "
            "is_override, roster_status, team_id, espn_athlete_id, "
            "nba_draft_projection, "
            "ig_followers, x_followers, tiktok_followers, total_followers"
        )
        .eq("roster_status", "active")
    )
    if team_filter:
        team_ids = list(teams_by_id.keys())
        if team_ids:
            query = query.in_("team_id", team_ids)

    players_resp = query.execute()
    players = players_resp.data or []

    # Process by team
    total_valued = 0
    total_ineligible = 0
    total_overrides = 0
    highest = {"name": "", "valuation": 0}
    lowest = {"name": "", "valuation": float("inf")}
    team_total = 0
    ineligible_log: list[str] = []

    for team_id, team_data in teams_by_id.items():
        team_name = team_data["university_name"]
        mm = team_data.get("market_multiplier", 1.0)
        print(f"{team_name} (market_multiplier: {mm})")

        team_players = [p for p in players if p.get("team_id") == team_id]
        if not team_players:
            print("  No active players\n")
            continue

        updates: list[dict] = []
        team_ineligible: list[str] = []

        for player in sorted(team_players, key=lambda p: p.get("name", "")):
            pid = player["id"]
            name = player.get("name", "?")

            # Skip overrides — handled in second pass
            if player.get("is_override"):
                continue

            # Eligibility gate
            if not is_eligible_for_valuation(player):
                usage_rate = player.get("usage_rate") or 0
                mpg = usage_rate * 40
                stars = f"{player.get('star_rating')}*" if player.get("star_rating") else "unranked"
                reason = f"MPG: {mpg:.1f}" if usage_rate > 0 else stars
                print(f"  {name:25s} | {str(player.get('position') or '?'):<4s} | {reason:12s} -> NULL (below gate)")
                team_ineligible.append(pid)
                ineligible_log.append(f"  {name:25s} | {team_name:<10s} | {reason}")
                total_ineligible += 1
                continue

            # Draft projection from DB column
            draft_pick = player.get("nba_draft_projection")

            breakdown = compute_valuation(player, team_data, draft_pick)
            val = breakdown["valuation"]

            print(
                f"  {name:25s} | {str(player.get('position') or '?'):<4s} | "
                f"{breakdown['role_label']:10s} | {breakdown['draft_label']:10s} | "
                f"{breakdown['talent_label']:12s} -> ${val:>9,}"
            )

            updates.append({"id": pid, "cfo_valuation": val})
            total_valued += 1
            team_total += val

            if val > highest["valuation"]:
                highest = {"name": name, "valuation": val}
            if val < lowest["valuation"]:
                lowest = {"name": name, "valuation": val}

        # Batch write
        if not dry_run and updates:
            for row in updates:
                try:
                    supabase.table("basketball_players").update(
                        {"cfo_valuation": row["cfo_valuation"]}
                    ).eq("id", row["id"]).execute()
                except Exception as exc:
                    print(f"  [ERROR] {row['id']}: {exc}")

        # NULL out ineligible players
        if not dry_run and team_ineligible:
            for pid in team_ineligible:
                try:
                    supabase.table("basketball_players").update(
                        {"cfo_valuation": None}
                    ).eq("id", pid).execute()
                except Exception as exc:
                    print(f"  [ERROR NULL] {pid}: {exc}")

        print()

    # Second pass: overrides
    overrides_resp = supabase.table("basketball_nil_overrides").select("player_id, annualized_value").execute()
    overrides = overrides_resp.data or []
    for override in overrides:
        pid = override["player_id"]
        annualized = int(float(override["annualized_value"]))
        if not dry_run:
            supabase.table("basketball_players").update({
                "cfo_valuation": annualized,
                "is_override": True,
            }).eq("id", pid).execute()
        total_overrides += 1
        team_total += annualized
        total_valued += 1

    # Summary
    print("=" * 60)
    print(f"Summary:")
    print(f"  {total_valued} players valued")
    print(f"  {total_ineligible} players below eligibility gate -> NULL")
    if highest["name"]:
        print(f"  Highest: {highest['name']} ${highest['valuation']:,}")
    if lowest["name"] and lowest["valuation"] != float("inf"):
        print(f"  Lowest:  {lowest['name']} ${lowest['valuation']:,}")
    print(f"  Team total: ${team_total:,}")
    print(f"  Overrides applied: {total_overrides}")
    if ineligible_log:
        print(f"\nIneligible (below gate):")
        for line in ineligible_log:
            print(line)
    if dry_run:
        print("\n  (Dry run -- no changes written)")
    print("=" * 60)


if __name__ == "__main__":
    main()
