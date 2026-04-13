"""
Syncs basketball rosters to reflect current transfer portal activity.
Reads from basketball_portal_entries (populated by sync_bball_portal_display.py)
and updates basketball_players.

Three operations:
A) Move committed players between our tracked schools
B) Mark players committed to non-tracked schools as departed
C) Flag evaluating players with portal_evaluating acquisition_type

Run after sync_bball_portal_display.py, before calculate_bball_valuations.py.

Usage:
    python sync_bball_roster_from_portal.py
    python sync_bball_roster_from_portal.py --dry-run
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
from supabase_client import supabase

# Portal names sometimes differ from roster names.
# Map normalized portal name → normalized DB name.
NAME_ALIASES: dict[str, str] = {
    "somto cyril": "somtochukwu cyril",
    # add others as discovered
}


def find_player(name: str, team_id: str) -> dict | None:
    """Find player in basketball_players by name and team."""
    normalized = NAME_ALIASES.get(name.lower().strip(), name.lower().strip())
    result = (
        supabase.table("basketball_players")
        .select("id, name, team_id, cfo_valuation, is_override, acquisition_type, roster_status")
        .eq("team_id", team_id)
        .eq("roster_status", "active")
        .execute()
    )
    for p in result.data:
        if p["name"].lower().strip() == normalized:
            return p
    return None


def main(dry_run: bool = False) -> None:
    print("Syncing rosters from portal data...\n")

    entries = (
        supabase.table("basketball_portal_entries")
        .select("player_name, status, origin_team_id, destination_team_id, origin_school, destination_school")
        .execute()
    ).data

    teams = (
        supabase.table("basketball_teams")
        .select("id, university_name, market_multiplier")
        .execute()
    ).data
    team_name = {t["id"]: t["university_name"] for t in teams}

    moved = departed = flagged = not_found = 0

    # ── A: Move committed players between our tracked schools ──
    print("=== A: Committed moves between our schools ===")
    moves = [
        e for e in entries
        if e["status"] == "committed"
        and e["origin_team_id"]
        and e["destination_team_id"]
    ]
    for e in moves:
        player = find_player(e["player_name"], e["origin_team_id"])
        if not player:
            print(f"  NOT FOUND: {e['player_name']} at {team_name.get(e['origin_team_id'], '?')}")
            not_found += 1
            continue

        if player.get("is_override"):
            print(f"  SKIP (override): {e['player_name']}")
            continue

        origin = team_name.get(e["origin_team_id"], "?")
        dest = team_name.get(e["destination_team_id"], "?")
        print(f"  MOVE: {e['player_name']:28s} | {origin} -> {dest}")

        if not dry_run:
            supabase.table("basketball_players").update({
                "team_id": e["destination_team_id"],
                "acquisition_type": "portal",
            }).eq("id", player["id"]).execute()
        moved += 1

    # ── B: Mark departed to non-tracked schools ──
    print()
    print("=== B: Departed to non-tracked schools ===")
    departed_entries = [
        e for e in entries
        if e["status"] == "committed"
        and e["origin_team_id"]
        and not e["destination_team_id"]
    ]
    for e in departed_entries:
        player = find_player(e["player_name"], e["origin_team_id"])
        if not player:
            print(f"  NOT FOUND: {e['player_name']}")
            not_found += 1
            continue

        origin = team_name.get(e["origin_team_id"], "?")
        dest_school = e["destination_school"] or "unknown"
        print(f"  DEPART: {e['player_name']:28s} | {origin} -> {dest_school}")

        if not dry_run:
            supabase.table("basketball_players").update({
                "roster_status": "departed_transfer",
            }).eq("id", player["id"]).execute()
        departed += 1

    # ── C: Flag evaluating players ──
    print()
    print("=== C: Flagging evaluating players ===")
    evaluating = [
        e for e in entries
        if e["status"] == "evaluating"
        and e["origin_team_id"]
    ]
    for e in evaluating:
        player = find_player(e["player_name"], e["origin_team_id"])
        if not player:
            not_found += 1
            continue

        origin = team_name.get(e["origin_team_id"], "?")
        print(f"  PORTAL: {e['player_name']:28s} | {origin}")

        if not dry_run:
            supabase.table("basketball_players").update({
                "acquisition_type": "portal_evaluating",
            }).eq("id", player["id"]).execute()
        flagged += 1

    print()
    print(f"Summary: {moved} moved, {departed} departed, {flagged} flagged, {not_found} not found")
    if dry_run:
        print("DRY RUN — no changes written")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
