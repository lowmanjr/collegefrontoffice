"""
apply_bball_overrides.py
-------------------------
Reads basketball overrides from data/basketball_approved_overrides.csv and
applies them to basketball_nil_overrides + basketball_players.

CSV format:
    espn_athlete_id,player_name,total_value,years,source_name,source_url

Usage:
    python apply_bball_overrides.py              # apply overrides
    python apply_bball_overrides.py --dry-run    # preview only
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import csv
from supabase_client import supabase

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "basketball_approved_overrides.csv")


def main():
    dry_run = "--dry-run" in sys.argv

    if not os.path.exists(CSV_PATH):
        print(f"No CSV found at {CSV_PATH}")
        return

    # Read CSV, skipping comment lines
    rows = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        lines = [line for line in f if not line.startswith("#")]
        reader = csv.DictReader(lines)
        for r in reader:
            if r.get("espn_athlete_id", "").strip():
                rows.append(r)

    print(f"Read {len(rows)} override(s) from CSV.\n")
    if not rows:
        return

    created = 0
    updated = 0
    skipped = 0
    errors = 0

    for row in rows:
        espn_id = row["espn_athlete_id"].strip()
        name = row.get("player_name", "?").strip()
        total_value = int(row.get("total_value", 0) or 0)
        years = int(row.get("years", 1) or 1)
        annualized = total_value // years if years > 0 else total_value
        source_name = row.get("source_name", "").strip() or None
        source_url = row.get("source_url", "").strip() or None

        # Find player by espn_athlete_id
        resp = (
            supabase.table("basketball_players")
            .select("id, name, is_override")
            .eq("espn_athlete_id", espn_id)
            .execute()
        )
        matches = resp.data or []
        if not matches:
            print(f"  [SKIP] {name}: ESPN ID {espn_id} not found in basketball_players")
            errors += 1
            continue

        player = matches[0]
        pid = player["id"]
        print(f"  {name} (ESPN {espn_id}): ${annualized:,}/yr ({years}yr, ${total_value:,} total)")

        if dry_run:
            print(f"    [DRY RUN] Would create override and set is_override=True")
            created += 1
            continue

        # Check existing overrides
        existing = (
            supabase.table("basketball_nil_overrides")
            .select("id, annualized_value")
            .eq("player_id", pid)
            .execute()
        )
        existing_rows = existing.data or []

        if existing_rows:
            old_val = existing_rows[0].get("annualized_value")
            if old_val and int(float(old_val)) == annualized:
                print(f"    [SKIP] Already has override at ${annualized:,}")
                skipped += 1
            else:
                supabase.table("basketball_nil_overrides").update({
                    "total_value": total_value,
                    "years": years,
                    "source_name": source_name,
                    "source_url": source_url,
                }).eq("player_id", pid).execute()
                print(f"    [UPDATED] override: ${old_val or 0:,} -> ${annualized:,}")
                updated += 1
        else:
            supabase.table("basketball_nil_overrides").insert({
                "player_id": pid,
                "total_value": total_value,
                "years": years,
                "source_name": source_name,
                "source_url": source_url,
            }).execute()
            print(f"    [CREATED] override: ${annualized:,}")
            created += 1

        # Set is_override = true and cfo_valuation = annualized
        supabase.table("basketball_players").update({
            "is_override": True,
            "cfo_valuation": annualized,
        }).eq("id", pid).execute()
        print(f"    [SET] is_override=True, cfo_valuation=${annualized:,}")

    print(f"\nSummary: {created} created, {updated} updated, {skipped} skipped, {errors} errors")
    if dry_run:
        print("(Dry run -- no changes written)")


if __name__ == "__main__":
    main()
