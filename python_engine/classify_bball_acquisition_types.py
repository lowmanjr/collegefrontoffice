"""
Classifies basketball players by acquisition type:
  'portal'   — arrived via transfer portal this cycle
  'recruit'  — high school recruit (hs_grad_year 2026+)
  'retained' — returning player, did not transfer in

Mirrors the acquisition_type field used in football players table.
Run after roster ingest and portal sync.

Usage:
    python classify_bball_acquisition_types.py
    python classify_bball_acquisition_types.py --dry-run
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
from supabase_client import supabase


def main(dry_run: bool = False) -> None:
    print("Classifying basketball player acquisition types...")

    players = (
        supabase.table("basketball_players")
        .select("id, name, team_id, player_tag, hs_grad_year, acquisition_type, usage_rate, class_year")
        .eq("roster_status", "active")
        .execute()
    ).data

    portal_entries = (
        supabase.table("basketball_portal_entries")
        .select("player_name, destination_team_id, status")
        .eq("status", "committed")
        .not_.is_("destination_team_id", "null")
        .execute()
    ).data

    portal_lookup: set[tuple[str, str]] = set()
    for e in portal_entries:
        normalized = e["player_name"].lower().strip()
        portal_lookup.add((normalized, e["destination_team_id"]))

    updates: dict[str, list[str]] = {"portal": [], "recruit": [], "retained": []}

    for p in players:
        normalized_name = p["name"].lower().strip()
        team_id = p["team_id"]

        if (normalized_name, team_id) in portal_lookup:
            acq_type = "portal"
        elif p.get("player_tag") == "High School Recruit" or (
            p.get("hs_grad_year") and p["hs_grad_year"] >= 2026
        ):
            acq_type = "recruit"
        else:
            acq_type = "retained"

        updates[acq_type].append(p["id"])

    print(f"  Portal arrivals:  {len(updates['portal'])}")
    print(f"  Recruits:         {len(updates['recruit'])}")
    print(f"  Retained:         {len(updates['retained'])}")
    print()

    for acq_type in ["portal", "recruit"]:
        if updates[acq_type]:
            print(f"  [{acq_type.upper()}]")
            detail = (
                supabase.table("basketball_players")
                .select("name, basketball_teams(university_name)")
                .in_("id", updates[acq_type])
                .execute()
            ).data
            for p in sorted(detail, key=lambda x: x["name"]):
                team = p["basketball_teams"]["university_name"] if p["basketball_teams"] else "?"
                print(f"    {p['name']:28s} | {team}")
            print()

    if dry_run:
        print("DRY RUN — no DB writes")
        return

    for acq_type, ids in updates.items():
        if ids:
            for i in range(0, len(ids), 50):
                batch = ids[i : i + 50]
                supabase.table("basketball_players").update(
                    {"acquisition_type": acq_type}
                ).in_("id", batch).execute()
            print(f"  Updated {len(ids)} players -> {acq_type}")

    print("Done.")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
