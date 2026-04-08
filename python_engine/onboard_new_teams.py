"""
Master onboarding script for new teams.
Runs the full pipeline: roster ingest -> depth charts -> production scores -> headshots -> valuations -> slugs.

Usage: python onboard_new_teams.py [--dry-run]
"""

import logging
import subprocess
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def run(cmd: str, dry_run: bool = False):
    """Run a pipeline step."""
    if dry_run:
        log.info(f"  [DRY RUN] Would run: {cmd}")
        return
    log.info(f"  Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        log.error(f"  FAILED: {result.stderr[:500]}")
    else:
        lines = result.stdout.strip().split("\n")
        for line in lines[-3:]:
            log.info(f"    {line}")


def main():
    dry_run = "--dry-run" in sys.argv

    steps = [
        ("1. Expand teams to Power 4", "python expand_to_power4.py"),
        ("2. Ingest ESPN rosters", "python ingest_espn_rosters.py"),
        ("3. Map CFBD IDs", "python map_cfbd_ids.py"),
        ("4. Enrich star ratings", "python enrich_star_ratings.py"),
        ("5. Enrich class years", "python enrich_class_years.py"),
        ("6. Map ESPN athlete IDs + headshots", "python map_espn_athlete_ids.py"),
        ("7. Calculate production scores", "python calculate_production_scores.py"),
        ("8. Calculate valuations", "python calculate_cfo_valuations.py"),
        ("9. Generate slugs", "python generate_slugs.py"),
    ]

    for label, cmd in steps:
        log.info(label)
        run(cmd, dry_run)
        log.info("")

    log.info("Onboarding complete.")
    if dry_run:
        log.info("(Dry run — no commands were executed)")


if __name__ == "__main__":
    main()
