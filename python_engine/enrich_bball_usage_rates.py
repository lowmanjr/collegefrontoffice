"""
enrich_bball_usage_rates.py
----------------------------
Pulls season stats from ESPN's core API for each basketball player,
computes a usage proxy from minutes per game, assigns role_tier and
rotation_rank, and writes ppg/rpg/apg/per back to basketball_players.

Source: https://sports.core.api.espn.com/v2/sports/basketball/leagues/
        mens-college-basketball/seasons/{year}/types/2/athletes/{id}/statistics

Usage:
    python enrich_bball_usage_rates.py              # all teams
    python enrich_bball_usage_rates.py --dry-run    # preview, no DB writes
    python enrich_bball_usage_rates.py --team byu   # single team
"""

import logging
import sys
import time
import requests
from supabase_client import supabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STATS_BASE = (
    "https://sports.core.api.espn.com/v2/sports/basketball/leagues/"
    "mens-college-basketball/seasons/{season}/types/2/athletes/{espn_id}/statistics"
)
CURRENT_SEASON = 2026  # 2025-26 season — update each year after season ends
RATE_LIMIT_SECONDS = 0.6

# ---------------------------------------------------------------------------
# Role tier assignment (MPG thresholds)
# ---------------------------------------------------------------------------

def assign_role_tier(mpg: float) -> str:
    if mpg >= 30:   return "franchise"
    if mpg >= 24:   return "star"
    if mpg >= 16:   return "starter"
    if mpg >= 8:    return "rotation"
    return "bench"


def assign_rotation_status(rank: int) -> str:
    if rank <= 5:   return "starter"
    if rank <= 10:  return "rotation"
    return "bench"


# ---------------------------------------------------------------------------
# ESPN stats fetch
# ---------------------------------------------------------------------------

def fetch_player_stats(espn_id: str) -> dict | None:
    """
    Fetch season averages from ESPN core API.
    Returns dict with mpg, ppg, rpg, apg, per, gp or None on 404/error.
    """
    url = STATS_BASE.format(season=CURRENT_SEASON, espn_id=espn_id)
    try:
        r = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
        if r.status_code == 404:
            return None
        r.raise_for_status()
    except requests.RequestException as exc:
        log.warning(f"    ESPN stats request failed for {espn_id}: {exc}")
        return None

    data = r.json()
    cats = data.get("splits", {}).get("categories", [])

    raw: dict[str, float] = {}
    for cat in cats:
        for s in cat.get("stats", []):
            raw[s["name"]] = s.get("value", 0.0)

    return {
        "mpg": round(raw.get("avgMinutes", 0.0), 1),
        "ppg": round(raw.get("avgPoints", 0.0), 1),
        "rpg": round(raw.get("avgRebounds", 0.0), 1),
        "apg": round(raw.get("avgAssists", 0.0), 1),
        "per": round(raw.get("PER", 0.0), 1),
        "gp":  int(raw.get("gamesPlayed", 0)),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    dry_run = "--dry-run" in sys.argv

    # Parse --team filter
    team_filter = None
    for i, arg in enumerate(sys.argv):
        if arg == "--team" and i + 1 < len(sys.argv):
            team_filter = sys.argv[i + 1].lower()

    # Fetch teams
    teams_resp = supabase.table("basketball_teams").select("id, university_name, slug").execute()
    db_teams = teams_resp.data or []
    if team_filter:
        db_teams = [t for t in db_teams if t["slug"] == team_filter]
        if not db_teams:
            log.error(f"No team with slug '{team_filter}' in basketball_teams")
            return

    total_updated = 0
    total_no_stats = 0
    total_errors = 0
    tier_counts: dict[str, int] = {}

    for team in db_teams:
        team_id = team["id"]
        team_name = team["university_name"]

        log.info(f"Enriching {team_name} basketball players with season stats...")

        # Fetch active players for this team
        players_resp = (
            supabase.table("basketball_players")
            .select("id, name, position, espn_athlete_id")
            .eq("team_id", team_id)
            .eq("roster_status", "active")
            .execute()
        )
        players = players_resp.data or []
        log.info(f"  {len(players)} active players")

        # Collect stats for all players
        enriched: list[dict] = []
        for p in players:
            espn_id = p.get("espn_athlete_id")
            if not espn_id:
                log.warning(f"  {p['name']:25s} | no ESPN ID, skipping")
                enriched.append({"player": p, "stats": None})
                total_no_stats += 1
                continue

            stats = fetch_player_stats(espn_id)
            if stats is None:
                enriched.append({"player": p, "stats": None})
                total_no_stats += 1
            else:
                enriched.append({"player": p, "stats": stats})

            time.sleep(RATE_LIMIT_SECONDS)

        # Sort by MPG descending for rotation_rank assignment
        # Players with no stats get MPG=0 (ranked last)
        enriched.sort(key=lambda x: (x["stats"]["mpg"] if x["stats"] else 0.0), reverse=True)

        # Assign rotation_rank (1-based, ordered by MPG)
        for rank, entry in enumerate(enriched, start=1):
            p = entry["player"]
            stats = entry["stats"]

            if stats is None:
                mpg = 0.0
                ppg = rpg = apg = per = 0.0
            else:
                mpg = stats["mpg"]
                ppg = stats["ppg"]
                rpg = stats["rpg"]
                apg = stats["apg"]
                per = stats["per"]

            usage_rate = round(mpg / 40.0, 4)
            role_tier = assign_role_tier(mpg)
            rotation_status = assign_rotation_status(rank)

            tier_counts[role_tier] = tier_counts.get(role_tier, 0) + 1

            pos = p.get("position") or "?"
            tag = "(no stats)" if stats is None else ""
            log.info(
                f"  {p['name']:25s} | {pos:<4s} | "
                f"MPG:{mpg:>5.1f} | PPG:{ppg:>5.1f} | RPG:{rpg:>4.1f} | APG:{apg:>4.1f} "
                f"-> {role_tier:10s} (rank {rank}) {tag}"
            )

            if not dry_run:
                try:
                    supabase.table("basketball_players").update({
                        "usage_rate": usage_rate,
                        "ppg": ppg,
                        "rpg": rpg,
                        "apg": apg,
                        "per": per,
                        "role_tier": role_tier,
                        "rotation_rank": rank,
                        "rotation_status": rotation_status,
                    }).eq("id", p["id"]).execute()
                    total_updated += 1
                except Exception as exc:
                    log.error(f"  [UPDATE ERROR] {p['name']}: {exc}")
                    total_errors += 1
            else:
                total_updated += 1

    log.info("")
    log.info(
        f"Summary: {len(db_teams)} team(s) processed, "
        f"{total_updated} players updated, "
        f"{total_no_stats} with no ESPN stats, "
        f"{total_errors} errors"
    )
    tier_str = ", ".join(f"{t}={c}" for t, c in sorted(tier_counts.items()))
    log.info(f"Role tier distribution: {tier_str}")
    if dry_run:
        log.info("(Dry run -- no changes written)")


if __name__ == "__main__":
    main()
