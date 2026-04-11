"""
enrich_bball_class_years.py
----------------------------
Pulls class year / experience level from ESPN roster API and writes
class_year + experience_level to basketball_players.

Source: ESPN roster endpoint's experience.displayValue field
(Freshman, Sophomore, Junior, Senior)

After enriching, re-runs calculate_bball_valuations.py so experience
multipliers take effect.

Usage:
    python enrich_bball_class_years.py              # enrich + recalculate
    python enrich_bball_class_years.py --dry-run    # preview only
"""

import logging
import os
import subprocess
import sys
import time
import requests
from supabase_client import supabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BASKETBALL_TEAMS = [
    {"slug": "byu", "espn_id": "252"},
    {"slug": "kentucky", "espn_id": "96"},
    {"slug": "uconn", "espn_id": "41"},
]

SPORT_PATH = "basketball/mens-college-basketball"
BASE_URL = "https://site.api.espn.com/apis/site/v2/sports"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

# ESPN uses these experience.displayValue strings
VALID_CLASS_YEARS = {"Freshman", "Sophomore", "Junior", "Senior", "Graduate"}


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    # Fetch all basketball players with ESPN IDs
    players_resp = (
        supabase.table("basketball_players")
        .select("id, name, espn_athlete_id, class_year, experience_level")
        .eq("roster_status", "active")
        .not_.is_("espn_athlete_id", "null")
        .execute()
    )
    db_players = {p["espn_athlete_id"]: p for p in (players_resp.data or [])}
    log.info(f"Found {len(db_players)} active players with ESPN IDs")

    updated = 0
    skipped = 0

    for team_cfg in BASKETBALL_TEAMS:
        slug = team_cfg["slug"]
        espn_id = team_cfg["espn_id"]

        log.info(f"Fetching {slug} roster from ESPN (ID {espn_id})...")
        url = f"{BASE_URL}/{SPORT_PATH}/teams/{espn_id}/roster"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            log.error(f"  ESPN request failed: {exc}")
            continue

        roster = resp.json()
        athletes = roster.get("athletes", [])
        log.info(f"  {len(athletes)} athletes in ESPN response")

        for athlete in athletes:
            athlete_id = str(athlete.get("id", ""))
            name = athlete.get("fullName", "?")

            if athlete_id not in db_players:
                continue

            player = db_players[athlete_id]

            # Extract experience
            exp = athlete.get("experience", {})
            if isinstance(exp, dict):
                display_value = exp.get("displayValue", "")
            else:
                display_value = ""

            if display_value not in VALID_CLASS_YEARS:
                log.info(f"  {name:<26} | experience='{display_value}' (not recognized, skipping)")
                skipped += 1
                continue

            # Skip if already set to the same value
            if player.get("class_year") == display_value and player.get("experience_level") == display_value:
                skipped += 1
                continue

            log.info(
                f"  {name:<26} | {display_value:<12} "
                f"{'(dry run)' if dry_run else '-> updated'}"
            )

            if not dry_run:
                supabase.table("basketball_players").update({
                    "class_year": display_value,
                    "experience_level": display_value,
                }).eq("id", player["id"]).execute()

            updated += 1

        time.sleep(1.0)

    log.info(f"\n{updated} players {'would be ' if dry_run else ''}updated, {skipped} skipped")

    # Re-run valuations so experience multipliers take effect
    if not dry_run and updated > 0:
        log.info("\nRecalculating valuations...")
        script_dir = os.path.dirname(__file__)
        subprocess.run(
            [sys.executable, os.path.join(script_dir, "calculate_bball_valuations.py")],
            cwd=script_dir,
        )


if __name__ == "__main__":
    main()
