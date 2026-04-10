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

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def resolve_csv_paths(team_filter: str | None) -> list[str]:
    """Find recruit CSV files. If --team is given, use that team's CSV only.
    Otherwise, glob all *_basketball_recruits_*.csv files."""
    import glob
    if team_filter:
        path = os.path.join(DATA_DIR, f"{team_filter}_basketball_recruits_2025.csv")
        return [path] if os.path.exists(path) else []
    return sorted(glob.glob(os.path.join(DATA_DIR, "*_basketball_recruits_*.csv")))


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    team_filter = None
    for i, arg in enumerate(sys.argv):
        if arg == "--team" and i + 1 < len(sys.argv):
            team_filter = sys.argv[i + 1].lower()

    csv_paths = resolve_csv_paths(team_filter)
    if not csv_paths:
        log.error(f"No recruit CSV files found{f' for team {team_filter}' if team_filter else ''}")
        return

    log.info(f"Found {len(csv_paths)} recruit CSV(s) to process")

    # Read all CSVs
    recruits: list[dict] = []
    for csv_path in csv_paths:
        log.info(f"  Reading {os.path.basename(csv_path)}...")
        with open(csv_path, "r") as f:
            lines = [line for line in f if not line.startswith("#")]
            reader = csv.DictReader(lines)
            for row in reader:
                recruits.append(row)

    log.info(f"  {len(recruits)} total recruits across {len(csv_paths)} file(s)")

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
