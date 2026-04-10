"""
enrich_bball_star_ratings.py
----------------------------
Enriches basketball_players with recruiting profile data from CSV.
Updates star_rating, composite_score, and position (247Sports granular
positions replace ESPN's generic G/F/C).

After enriching, re-runs calculate_bball_valuations.py so valuations
reflect the updated talent_modifier.

Usage:
    python enrich_bball_star_ratings.py              # enrich + recalculate
    python enrich_bball_star_ratings.py --dry-run    # preview only
"""

import csv
import logging
import os
import subprocess
import sys
from supabase_client import supabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "byu_basketball_recruits_2025.csv")


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    if not os.path.exists(CSV_PATH):
        log.error(f"CSV not found: {CSV_PATH}")
        return

    log.info(f"Enriching recruiting profiles from {os.path.basename(CSV_PATH)}...")

    # Read CSV
    recruits: list[dict] = []
    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            recruits.append(row)

    log.info(f"  {len(recruits)} recruits in CSV")

    updated = 0
    skipped = 0

    for recruit in recruits:
        espn_id = recruit.get("espn_athlete_id", "").strip()
        name = recruit.get("player_name", "?")
        star_rating = int(recruit.get("star_rating", 0))
        composite = float(recruit.get("composite_score", 0))
        position = recruit.get("position_247", "").strip() or None

        if not espn_id:
            log.warning(f"  [SKIP] Missing espn_athlete_id for {name}")
            skipped += 1
            continue

        # Find player in DB
        resp = (
            supabase.table("basketball_players")
            .select("id, name, star_rating, composite_score, position")
            .eq("espn_athlete_id", espn_id)
            .execute()
        )
        matches = resp.data or []
        if not matches:
            log.warning(f"  [SKIP] No DB match for ESPN ID {espn_id} ({name})")
            skipped += 1
            continue

        player = matches[0]
        update_data: dict = {}

        if star_rating > 0:
            update_data["star_rating"] = star_rating
        if composite > 0:
            update_data["composite_score"] = composite
        if position:
            update_data["position"] = position

        if not update_data:
            skipped += 1
            continue

        log.info(
            f"  {name:25s} | composite: {composite:.4f} | "
            f"stars: {star_rating} | pos: {position or '?'} "
            f"{'-> updated' if not dry_run else '(dry run)'}"
        )

        if not dry_run:
            supabase.table("basketball_players").update(update_data).eq("id", player["id"]).execute()

        updated += 1

    log.info(f"\n{updated} players {'would be ' if dry_run else ''}updated, {skipped} skipped")

    # Re-run valuations to reflect updated talent modifiers
    if not dry_run and updated > 0:
        log.info("\nRecalculating valuations...")
        script_dir = os.path.dirname(__file__)
        subprocess.run(
            [sys.executable, os.path.join(script_dir, "calculate_bball_valuations.py")],
            cwd=script_dir,
        )


if __name__ == "__main__":
    main()
