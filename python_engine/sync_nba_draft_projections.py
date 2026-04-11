"""
sync_nba_draft_projections.py
------------------------------
Syncs NBA draft projections from ESPN's draft prospects API.
Updates basketball_players.nba_draft_projection and writes
a reference CSV to data/nba_draft_projections_2025.csv.

ESPN draft prospects API returns college players with their
ESPN athlete IDs — enabling zero-ambiguity matching against
basketball_players.espn_athlete_id.

Usage:
    python sync_nba_draft_projections.py              # sync + recalculate
    python sync_nba_draft_projections.py --dry-run    # preview only
    python sync_nba_draft_projections.py --season 2025  # different draft year
"""

import csv
import os
import subprocess
import sys
import time

import requests
from supabase_client import supabase

sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"
RATE_LIMIT = 0.3  # seconds between ESPN requests
PAGE_SIZE = 25


def fetch_all_prospects(season: int) -> list[dict]:
    """Fetch all draft prospects from ESPN, resolving $ref links."""
    prospects_url = f"{BASE_URL}/seasons/{season}/draft/athletes?limit={PAGE_SIZE}"
    all_prospects: list[dict] = []
    page = 1

    while prospects_url:
        resp = requests.get(prospects_url, timeout=15)
        if resp.status_code != 200:
            print(f"  [ERROR] {resp.status_code} fetching page {page}")
            break

        data = resp.json()
        items = data.get("items", [])
        total = data.get("count", 0)
        print(f"  Page {page}: {len(items)} items (total: {total})")

        for item in items:
            ref = item.get("$ref")
            if not ref:
                continue
            time.sleep(RATE_LIMIT)
            try:
                detail = requests.get(ref, timeout=15).json()
            except Exception as exc:
                print(f"  [WARN] Failed to fetch prospect ref: {exc}")
                continue

            name = detail.get("displayName", "?")

            # Extract college athlete ID from athlete.$ref
            athlete_ref = detail.get("athlete", {})
            college_athlete_id = None
            if isinstance(athlete_ref, dict) and "$ref" in athlete_ref:
                college_athlete_id = athlete_ref["$ref"].split("/")[-1].split("?")[0]

            # Extract overall rank from attributes
            overall_rank = None
            for attr in detail.get("attributes", []):
                if attr.get("name") == "overall":
                    overall_rank = int(float(attr.get("value", 0)))
                    break

            # Extract college ID
            college_ref = detail.get("college", {})
            college_id = None
            if isinstance(college_ref, dict) and "$ref" in college_ref:
                college_id = college_ref["$ref"].split("/")[-1].split("?")[0]

            all_prospects.append({
                "name": name,
                "college_athlete_id": college_athlete_id,
                "college_id": college_id,
                "overall_rank": overall_rank,
            })

        # Next page
        next_link = None
        for link in data.get("items", []):
            pass  # items are prospects, not pagination links
        # Check for pageIndex in response
        page_index = data.get("pageIndex", page)
        page_count = data.get("pageCount", 1)
        if page_index < page_count:
            prospects_url = f"{BASE_URL}/seasons/{season}/draft/athletes?limit={PAGE_SIZE}&page={page_index + 1}"
            page += 1
        else:
            break

    return all_prospects


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    season = 2026  # current draft year
    for i, arg in enumerate(sys.argv):
        if arg == "--season" and i + 1 < len(sys.argv):
            season = int(sys.argv[i + 1])

    print(f"Fetching ESPN NBA draft prospects ({season} season)...")
    prospects = fetch_all_prospects(season)
    print(f"\nFound {len(prospects)} prospects total\n")

    # Load our basketball players for matching
    players_resp = supabase.table("basketball_players") \
        .select("id, name, espn_athlete_id, nba_draft_projection, basketball_teams(university_name)") \
        .eq("roster_status", "active") \
        .not_.is_("espn_athlete_id", "null") \
        .execute()

    db_by_espn_id: dict[str, dict] = {}
    for p in (players_resp.data or []):
        db_by_espn_id[p["espn_athlete_id"]] = p

    # Match prospects to our DB
    matched: list[dict] = []
    unmatched = 0

    print("Matching against basketball_players...")
    for prospect in sorted(prospects, key=lambda x: x.get("overall_rank") or 999):
        cid = prospect.get("college_athlete_id")
        name = prospect["name"]
        rank = prospect.get("overall_rank")

        if not cid or not rank:
            continue

        db_player = db_by_espn_id.get(cid)
        if db_player:
            team = db_player.get("basketball_teams", {})
            team_name = team.get("university_name", "?") if team else "?"
            old_pick = db_player.get("nba_draft_projection")
            change = ""
            if old_pick and old_pick != rank:
                change = f" (was pick {old_pick})"
            elif not old_pick:
                change = " (NEW)"
            print(f"  + {name:28s} ({team_name:10s}) | ESPN: {cid} | rank: {rank}{change}")
            matched.append({
                "espn_athlete_id": cid,
                "player_name": name,
                "projected_pick": rank,
                "db_id": db_player["id"],
            })
        else:
            unmatched += 1

    print(f"\nMatched: {len(matched)} of {len(prospects)} prospects are in our DB")
    print(f"Unmatched: {unmatched} prospects not in our DB (other schools)\n")

    if not matched:
        print("No matches found — nothing to update.")
        return

    # Write CSV reference file
    csv_path = os.path.join(os.path.dirname(__file__), "data", "nba_draft_projections_2025.csv")
    if not dry_run:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["espn_athlete_id", "player_name", "projected_pick"])
            writer.writeheader()
            for m in sorted(matched, key=lambda x: x["projected_pick"]):
                writer.writerow({
                    "espn_athlete_id": m["espn_athlete_id"],
                    "player_name": m["player_name"],
                    "projected_pick": m["projected_pick"],
                })
        print(f"Updated: {csv_path} ({len(matched)} rows)")

    # Update DB
    if not dry_run:
        for m in matched:
            try:
                supabase.table("basketball_players").update({
                    "nba_draft_projection": m["projected_pick"],
                }).eq("id", m["db_id"]).execute()
            except Exception as exc:
                print(f"  [ERROR] {m['player_name']}: {exc}")
        print(f"Updated: {len(matched)} players in basketball_players.nba_draft_projection")
    else:
        print("(Dry run -- no changes written)")

    # Re-run valuations
    if not dry_run:
        print("\nRecalculating valuations...")
        script_dir = os.path.dirname(__file__)
        subprocess.run(
            [sys.executable, os.path.join(script_dir, "calculate_bball_valuations.py")],
            cwd=script_dir,
        )


if __name__ == "__main__":
    main()
