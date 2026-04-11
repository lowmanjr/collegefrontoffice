"""
map_cfbd_ids.py
---------------
One-off bridge script that permanently maps CFBD integer IDs into our
Supabase players.cfbd_id column using a team-scoped fuzzy name match.

Strategy:
  1. Fetch each team's 2025 roster from the CFBD Roster API.
  2. For every College Athlete in Supabase, restrict the fuzzy search to
     only the CFBD players on the same team — this makes difflib matches
     effectively unambiguous even at a 0.85 cutoff.
  3. Write the matched CFBD integer id into players.cfbd_id.

Run this once after adding the blank cfbd_id column to Supabase.

Usage:
    python map_cfbd_ids.py

Requirements:
    pip install supabase python-dotenv requests
"""

import os
import re
import time
import unicodedata
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from name_utils import normalize_name, normalize_name_stripped

# ---------------------------------------------------------------------------
# 1. SETUP
# ---------------------------------------------------------------------------

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))

SUPABASE_URL      = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise EnvironmentError("Missing Supabase credentials in .env.local")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

CFBD_API_KEY = os.getenv("CFBD_API_KEY")

if not CFBD_API_KEY:
    raise EnvironmentError("Missing CFBD_API_KEY in .env.local")

CFBD_HEADERS = {
    "Authorization": f"Bearer {CFBD_API_KEY}",
    "Accept": "application/json",
}

CFBD_ROSTER_URL = "https://api.collegefootballdata.com/roster"
CFBD_YEAR       = 2025
TEAM_DELAY      = 1  # seconds between CFBD requests

# ---------------------------------------------------------------------------
# 2. HELPERS
# ---------------------------------------------------------------------------

def normalise(name: str) -> str:
    """Lowercase, strip accents and punctuation — delegates to shared name_utils."""
    return normalize_name(name)


# ---------------------------------------------------------------------------
# 3. PASS 1 — FETCH CFBD ROSTERS (one request per team)
#
# team_rosters: university_name → list of {"cfbd_id": int, "name": str,
#                                           "name_normalised": str}
# ---------------------------------------------------------------------------

def fetch_teams() -> list[dict]:
    """Return id + university_name rows from our Supabase teams table."""
    print("Fetching teams from Supabase...")
    resp = supabase.table("teams").select("id, university_name").execute()
    teams = resp.data or []
    print(f"  {len(teams)} team(s): {[t['university_name'] for t in teams]}\n")
    return teams


def build_team_rosters(teams: list[dict]) -> dict[str, list[dict]]:
    """
    Hit CFBD /roster once per team and return a dict:
      university_name → [{"cfbd_id": int, "name": str, "name_normalised": str}, ...]
    """
    rosters: dict[str, list[dict]] = {}
    api_errors = 0

    print("=" * 65)
    print(f"Fetching CFBD rosters (year={CFBD_YEAR})...")
    print("=" * 65)

    for team in teams:
        team_name = team["university_name"]
        print(f"  [{team_name}]... ", end="", flush=True)

        try:
            r = requests.get(
                CFBD_ROSTER_URL,
                headers=CFBD_HEADERS,
                params={"year": CFBD_YEAR, "team": team_name},
                timeout=20,
            )
            if r.status_code == 401:
                print("\n[ERROR] 401 Unauthorized — check CFBD_API_KEY in .env.local.")
                raise SystemExit(1)
            r.raise_for_status()
            players: list[dict] = r.json()
        except requests.RequestException as exc:
            print(f"[ERROR] {exc}")
            api_errors += 1
            time.sleep(TEAM_DELAY)
            continue

        roster_entries = []
        for p in players:
            cfbd_id = p.get("id")
            # CFBD uses first_name / last_name; fall back to a combined field if present
            first = (p.get("first_name") or p.get("firstName") or "").strip()
            last  = (p.get("last_name")  or p.get("lastName")  or "").strip()
            full_name = f"{first} {last}".strip() if (first or last) else (p.get("name") or "").strip()

            if not full_name or cfbd_id is None:
                continue

            roster_entries.append({
                "cfbd_id":          int(cfbd_id),
                "name":             full_name,
                "name_normalised":  normalise(full_name),
            })

        rosters[team_name] = roster_entries
        print(f"{len(roster_entries)} players on roster")
        time.sleep(TEAM_DELAY)

    print(f"\nRoster fetch complete. {sum(len(v) for v in rosters.values())} total CFBD players.")
    if api_errors:
        print(f"  ({api_errors} team request(s) failed)")
    print()
    return rosters


# ---------------------------------------------------------------------------
# 4. PASS 2 — FETCH SUPABASE PLAYERS & FUZZY MATCH WITHIN TEAM
# ---------------------------------------------------------------------------

def fetch_players() -> list[dict]:
    """Return all College Athletes (paginated), including their team_id."""
    PAGE_SIZE   = 1000
    all_players: list[dict] = []
    offset      = 0

    print("Fetching College Athletes from Supabase...")
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, team_id")
            .eq("player_tag", "College Athlete")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    print(f"  {len(all_players)} player(s) fetched.\n")
    return all_players


def match_and_update(
    players:  list[dict],
    teams:    list[dict],
    rosters:  dict[str, list[dict]],
) -> None:
    # Build a team_id → university_name lookup for O(1) resolution
    team_id_to_name: dict[str, str] = {t["id"]: t["university_name"] for t in teams}

    # Summary counters per team
    per_team_matched:   dict[str, int] = {}
    per_team_total:     dict[str, int] = {}

    total_matched   = 0
    total_unmatched = 0
    total_no_roster = 0

    print("=" * 65)
    print("Fuzzy-matching players to CFBD IDs within team...")
    print("=" * 65)

    for player in players:
        team_id   = player.get("team_id")
        team_name = team_id_to_name.get(team_id) if team_id else None

        per_team_total[team_name or "Unknown"] = (
            per_team_total.get(team_name or "Unknown", 0) + 1
        )

        if not team_name or team_name not in rosters:
            total_no_roster += 1
            continue

        roster = rosters[team_name]
        if not roster:
            total_no_roster += 1
            continue

        # Build normalised name → cfbd_id map for this team's roster
        norm_to_entry: dict[str, dict] = {e["name_normalised"]: e for e in roster}
        # Also build stripped-name lookup for suffix mismatches
        stripped_to_entry: dict[str, dict] = {}
        for e in roster:
            skey = normalize_name_stripped(e["name"])
            if skey not in stripped_to_entry:
                stripped_to_entry[skey] = e
        candidate_keys = list(norm_to_entry.keys())
        stripped_keys = list(stripped_to_entry.keys())

        db_norm = normalise(player["name"])
        db_stripped = normalize_name_stripped(player["name"])

        # 4-pass matching: exact → exact-stripped → fuzzy → fuzzy-stripped
        matched_entry = norm_to_entry.get(db_norm)
        match_type    = "exact"

        if matched_entry is None:
            matched_entry = stripped_to_entry.get(db_stripped)
            if matched_entry:
                match_type = f'exact-stripped -> "{matched_entry["name"]}"'

        if matched_entry is None:
            from difflib import get_close_matches
            fuzzy = get_close_matches(db_norm, candidate_keys, n=1, cutoff=0.85)
            if fuzzy:
                matched_entry = norm_to_entry[fuzzy[0]]
                match_type    = f'fuzzy -> "{matched_entry["name"]}"'

        if matched_entry is None:
            from difflib import get_close_matches
            fuzzy = get_close_matches(db_stripped, stripped_keys, n=1, cutoff=0.85)
            if fuzzy:
                matched_entry = stripped_to_entry[fuzzy[0]]
                match_type    = f'fuzzy-stripped -> "{matched_entry["name"]}"'

        if matched_entry is None:
            total_unmatched += 1
            continue

        supabase.table("players").update(
            {"cfbd_id": matched_entry["cfbd_id"]}
        ).eq("id", player["id"]).execute()

        per_team_matched[team_name] = per_team_matched.get(team_name, 0) + 1
        total_matched += 1

        print(
            f"  [MAPPED] {player['name']:<28}  ({match_type})  "
            f"cfbd_id={matched_entry['cfbd_id']}"
        )

    # ── Per-team summary ─────────────────────────────────────────────────────
    print(f"\n{'=' * 65}")
    print(f"Bridge complete.\n")
    print(f"  {'Team':<24}  {'Matched':>7}  {'Total':>6}")
    print(f"  {'-'*24}  {'-'*7}  {'-'*6}")

    all_team_names = sorted(per_team_total.keys())
    for name in all_team_names:
        matched = per_team_matched.get(name, 0)
        total   = per_team_total[name]
        print(f"  {name:<24}  {matched:>7}  {total:>6}")

    print(f"\n  Players mapped        : {total_matched}")
    print(f"  Players unmatched     : {total_unmatched}")
    print(f"  Players no roster     : {total_no_roster}")
    print(f"  Total processed       : {len(players)}")


# ---------------------------------------------------------------------------
# 5. MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    teams = fetch_teams()
    if not teams:
        print("No teams found in Supabase. Exiting.")
        return

    rosters = build_team_rosters(teams)
    if not rosters:
        print("No roster data collected from CFBD. Exiting.")
        return

    players = fetch_players()
    if not players:
        print("No College Athletes found in Supabase. Exiting.")
        return

    match_and_update(players, teams, rosters)


if __name__ == "__main__":
    main()
