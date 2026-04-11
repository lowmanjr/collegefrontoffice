"""
apply_bball_social_manual.py
----------------------------
Applies manually collected social follower counts from CSV to
basketball_players. Use for players not covered by On3 scraping.

Source: python_engine/data/basketball_social_manual.csv

Usage:
    python apply_bball_social_manual.py              # apply
    python apply_bball_social_manual.py --dry-run    # preview only
"""

import csv
import os
import sys
from supabase_client import supabase

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    csv_path = os.path.join(os.path.dirname(__file__), "data", "basketball_social_manual.csv")

    if not os.path.exists(csv_path):
        print(f"No file at {csv_path}")
        return

    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r.get("espn_athlete_id", "").strip()]

    print(f"Read {len(rows)} entries from basketball_social_manual.csv\n")

    updated = 0
    for row in rows:
        espn_id = row["espn_athlete_id"].strip()
        name = row.get("player_name", "?").strip()
        ig = int(row.get("ig_followers", 0) or 0)
        x = int(row.get("x_followers", 0) or 0)
        tiktok = int(row.get("tiktok_followers", 0) or 0)
        total = ig + x + tiktok

        # Compute premium for display
        weighted = ig + int(x * 0.7) + int(tiktok * 1.2)
        if weighted >= 1_000_000:   premium = 150_000
        elif weighted >= 500_000:   premium = 75_000
        elif weighted >= 100_000:   premium = 25_000
        elif weighted >= 50_000:    premium = 10_000
        elif weighted >= 10_000:    premium = 3_000
        else:                       premium = 0

        tag = "(dry run)" if dry_run else "-> updated"
        print(f"  {name:28s} | IG: {ig:>8,} | X: {x:>6,} | TikTok: {tiktok:>8,} | total: {total:>8,} | +${premium:,} {tag}")

        if not dry_run:
            supabase.table("basketball_players").update({
                "ig_followers": ig or None,
                "x_followers": x or None,
                "tiktok_followers": tiktok or None,
                "total_followers": total,
            }).eq("espn_athlete_id", espn_id).execute()

        updated += 1

    print(f"\n{updated} players {'would be ' if dry_run else ''}updated")
    if dry_run:
        print("(Dry run -- no changes written)")


if __name__ == "__main__":
    main()
