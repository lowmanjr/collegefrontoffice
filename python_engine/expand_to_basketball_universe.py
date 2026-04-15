"""
Expand basketball_teams from 14 tracked teams to the full 82-team universe.
Reads from data/basketball_expansion_teams.csv and inserts new teams only.

Usage:
    python expand_to_basketball_universe.py --dry-run   # preview inserts
    python expand_to_basketball_universe.py             # apply inserts
"""

import csv
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from supabase_client import supabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "basketball_expansion_teams.csv")


def main():
    dry_run = "--dry-run" in sys.argv

    # Load CSV
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    log.info(f"Loaded {len(rows)} rows from CSV")

    # Load existing teams from DB
    resp = supabase.table("basketball_teams").select("university_name, slug").execute()
    existing_slugs = {t["slug"] for t in (resp.data or [])}
    log.info(f"Existing teams in DB: {len(existing_slugs)}")

    # Sort by conference then name for readable output
    rows.sort(key=lambda r: (r["conference"], r["university_name"]))

    inserted = 0
    skipped = 0
    errors = 0

    for row in rows:
        name = row["university_name"]
        slug = row["slug"]
        conference = row["conference"]
        espn_id = row["espn_id"]
        market_mult = float(row["market_multiplier"])
        is_existing = row["is_existing"].strip().lower() == "true"
        logo_url = f"https://a.espncdn.com/i/teamlogos/ncaa/500/{espn_id}.png"

        if is_existing or slug in existing_slugs:
            if slug in existing_slugs:
                log.info(f"  SKIP (exists): {name:<25} {conference}")
                skipped += 1
            else:
                log.warning(f"  SKIP (marked existing but not in DB): {name}")
                skipped += 1
            continue

        if dry_run:
            log.info(f"  [DRY RUN] INSERT: {name:<25} {conference:<12} mm={market_mult}  ESPN:{espn_id}  slug={slug}")
            inserted += 1
            continue

        try:
            supabase.table("basketball_teams").insert({
                "university_name": name,
                "slug": slug,
                "conference": conference,
                "market_multiplier": market_mult,
                "logo_url": logo_url,
            }).execute()
            log.info(f"  INSERT: {name:<25} {conference:<12} mm={market_mult}  ESPN:{espn_id}")
            inserted += 1
        except Exception as e:
            log.error(f"  FAIL: {name} -- {e}")
            errors += 1

    print()
    log.info(f"Done. Inserted: {inserted}, Skipped (existing): {skipped}, Errors: {errors}")
    if dry_run:
        log.info("(Dry run -- no changes written)")


if __name__ == "__main__":
    main()
