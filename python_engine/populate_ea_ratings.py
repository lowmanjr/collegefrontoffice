"""
populate_ea_ratings.py
-----------------------
Reads EA ratings from python_engine/data/ea_ratings.csv and updates
players.ea_rating for matched players.

Usage:
    python populate_ea_ratings.py              # dry-run (default)
    python populate_ea_ratings.py --apply      # write to DB
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import argparse
import csv
import datetime
import os
from collections import Counter

from supabase_client import supabase

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "ea_ratings.csv")
MIN_CONFIDENCE = 0.80


def main():
    parser = argparse.ArgumentParser(description="Populate ea_rating from EA CSV")
    parser.add_argument("--apply", action="store_true", help="Write to DB (default is dry-run)")
    args = parser.parse_args()

    dry_run = not args.apply
    mode = "DRY RUN" if dry_run else "LIVE"

    print("=" * 70)
    print(f"  POPULATE EA RATINGS ({mode})")
    print("=" * 70)

    if not os.path.exists(CSV_PATH):
        print(f"\n  [ERROR] CSV not found: {CSV_PATH}")
        print(f"  Run scrape_ea_ratings.py first.")
        return

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"\n  CSV rows: {len(rows)}")

    # Filter to high-confidence matches
    updates: list[dict] = []
    skipped = 0
    for row in rows:
        conf = float(row.get("match_confidence", 0))
        ovr = row.get("ea_ovr", "")
        pid = row.get("matched_player_id", "")
        if conf < MIN_CONFIDENCE or not ovr or not pid:
            skipped += 1
            continue
        updates.append({
            "player_id": pid,
            "player_name": row.get("matched_player_name", "?"),
            "ea_name": row.get("ea_name", "?"),
            "ea_team": row.get("ea_team", "?"),
            "ea_position": row.get("ea_position", "?"),
            "ea_ovr": int(ovr),
            "confidence": conf,
            "cfo_position": row.get("cfo_position", "?"),
        })

    print(f"  Eligible updates (conf >= {MIN_CONFIDENCE}): {len(updates)}")
    print(f"  Skipped (low confidence): {skipped}")

    # Position breakdown
    pos_counts = Counter(u["cfo_position"] for u in updates)
    print(f"\n  By CFO position:")
    for pos, cnt in sorted(pos_counts.items(), key=lambda x: -x[1]):
        print(f"    {pos:<6} {cnt}")

    # OVR distribution
    ovr_tiers = Counter()
    for u in updates:
        ovr = u["ea_ovr"]
        if ovr >= 90:
            ovr_tiers["90+ (Elite)"] += 1
        elif ovr >= 82:
            ovr_tiers["82-89 (Strong)"] += 1
        elif ovr >= 75:
            ovr_tiers["75-81 (Average)"] += 1
        elif ovr >= 68:
            ovr_tiers["68-74 (Below Avg)"] += 1
        else:
            ovr_tiers["<68 (Low)"] += 1

    print(f"\n  OVR distribution:")
    for tier in ["90+ (Elite)", "82-89 (Strong)", "75-81 (Average)", "68-74 (Below Avg)", "<68 (Low)"]:
        print(f"    {tier:<20} {ovr_tiers.get(tier, 0)}")

    if dry_run:
        # Show sample
        print(f"\n  Sample updates (top 15 by OVR):")
        header = f"{'EA NAME':<28} {'TEAM':<18} {'EA POS':<7} {'OVR':>4} {'CFO NAME':<28} {'CFO POS':<7}"
        print(f"  {header}")
        print(f"  {'─' * len(header)}")
        for u in sorted(updates, key=lambda x: -x["ea_ovr"])[:15]:
            print(
                f"  {u['ea_name']:<28} {u['ea_team']:<18} {u['ea_position']:<7} "
                f"{u['ea_ovr']:>4} {u['player_name']:<28} {u['cfo_position']:<7}"
            )

        print(f"\n  DRY RUN — no changes applied.")
        print(f"  To apply: python populate_ea_ratings.py --apply")
    else:
        # Check column exists
        try:
            supabase.table("players").select("ea_rating").limit(1).execute()
        except Exception:
            print(f"\n  [ERROR] ea_rating column does not exist!")
            print(f"  Run migration: supabase/migrations/00007_ea_rating_column.sql")
            return

        now = datetime.datetime.utcnow().isoformat()
        applied = 0
        errors = 0

        for u in updates:
            try:
                supabase.table("players").update({
                    "ea_rating": u["ea_ovr"],
                    "last_updated": now,
                }).eq("id", u["player_id"]).execute()
                applied += 1
            except Exception as exc:
                print(f"    [ERROR] {u['player_name']}: {exc}")
                errors += 1

        print(f"\n  Applied: {applied}, Errors: {errors}")

    print(f"\n{'=' * 70}")


if __name__ == "__main__":
    main()
