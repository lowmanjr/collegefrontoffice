"""
fix_bball_headshots.py
-----------------------
Verifies and repairs headshot_url for basketball players.
Constructs canonical URLs from ESPN athlete ID, tests each URL,
and updates the DB with working URLs. Players where ESPN has no
headshot get NULL (PlayerAvatar component handles initials fallback).

ESPN CDN pattern:
  https://a.espncdn.com/i/headshots/mens-college-basketball/players/full/{id}.png

Usage:
    python fix_bball_headshots.py              # all teams
    python fix_bball_headshots.py --team duke   # one team
    python fix_bball_headshots.py --dry-run     # check only
"""

import sys
import time

import requests
from supabase_client import supabase

sys.stdout.reconfigure(encoding="utf-8")

CDN_BASE = "https://a.espncdn.com/i/headshots/mens-college-basketball/players/full"
RATE_LIMIT = 0.3  # seconds between HEAD requests


def canonical_url(espn_id: str) -> str:
    return f"{CDN_BASE}/{espn_id}.png"


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    team_filter = None
    for i, arg in enumerate(sys.argv):
        if arg == "--team" and i + 1 < len(sys.argv):
            team_filter = sys.argv[i + 1]

    # Load teams
    query = supabase.table("basketball_teams").select("id, university_name, slug")
    if team_filter:
        query = query.eq("slug", team_filter)
    teams = query.order("university_name").execute().data or []

    total_verified = 0
    total_updated = 0
    total_nulled = 0
    total_already_ok = 0

    for team in teams:
        team_name = team["university_name"]
        players = (
            supabase.table("basketball_players")
            .select("id, name, espn_athlete_id, headshot_url")
            .eq("team_id", team["id"])
            .eq("roster_status", "active")
            .not_.is_("espn_athlete_id", "null")
            .execute()
        ).data or []

        print(f"{team_name} ({len(players)} players)")

        for p in sorted(players, key=lambda x: x["name"]):
            espn_id = p["espn_athlete_id"]
            name = p["name"]
            stored = p.get("headshot_url")
            expected = canonical_url(espn_id)

            # HEAD request to verify
            try:
                resp = requests.head(expected, timeout=5, allow_redirects=True)
                status = resp.status_code
            except Exception:
                status = 0

            total_verified += 1

            if status == 200:
                if stored == expected:
                    total_already_ok += 1
                else:
                    tag = "(dry run)" if dry_run else "-> updated"
                    old_desc = "NULL" if not stored else "wrong URL"
                    print(f"  + {name:28s} | {old_desc} -> canonical URL {tag}")
                    if not dry_run:
                        supabase.table("basketball_players").update(
                            {"headshot_url": expected}
                        ).eq("id", p["id"]).execute()
                    total_updated += 1
            else:
                if stored is not None:
                    tag = "(dry run)" if dry_run else "-> NULL"
                    print(f"  - {name:28s} | {status} — no ESPN headshot {tag}")
                    if not dry_run:
                        supabase.table("basketball_players").update(
                            {"headshot_url": None}
                        ).eq("id", p["id"]).execute()
                    total_nulled += 1
                else:
                    total_already_ok += 1

            time.sleep(RATE_LIMIT)

        print()

    print("=" * 50)
    print(f"Summary:")
    print(f"  {total_verified} players checked")
    print(f"  {total_already_ok} already correct")
    print(f"  {total_updated} URLs updated")
    print(f"  {total_nulled} set to NULL (no ESPN headshot)")
    if dry_run:
        print("  (Dry run -- no changes written)")
    print("=" * 50)


if __name__ == "__main__":
    main()
