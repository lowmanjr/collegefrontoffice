"""
sync_active_rosters.py
----------------------
Fetches each team's roster from the ESPN College Football API and promotes
matched players in our Supabase database to player_tag = 'College Athlete'.

Usage:
    python sync_active_rosters.py

Requirements:
    pip install supabase python-dotenv requests
"""

import os
import time
import unicodedata
import re
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# 1. SETUP
# ---------------------------------------------------------------------------

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))

SUPABASE_URL      = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise EnvironmentError(
        "Missing Supabase credentials. "
        "Ensure NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY are set in .env.local"
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

ESPN_ROSTER_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/{espn_id}/roster"

REQUEST_DELAY = 1.0  # seconds between ESPN API calls

# ---------------------------------------------------------------------------
# 2. ESPN TEAM ID MAP
#    Key : university_name (lowercase) as stored in our `teams` table
#    Value: ESPN team ID
# ---------------------------------------------------------------------------

ESPN_TEAM_MAP: dict[str, int] = {
    "ohio state":    194,
    "georgia":        61,
    "alabama":       333,
    "texas":         251,
    "oregon":       2483,
    "michigan":      130,
    "usc":            30,
    "washington":    264,
    "lsu":            99,
    "tennessee":    2633,
    "oklahoma":      201,
    "florida":        57,
    "south carolina":2579,
    "miami":        2390,
    "clemson":       228,
    "notre dame":     87,
}

# ---------------------------------------------------------------------------
# 3. NAME NORMALISATION
#    Strips accents, punctuation, and lowercases so "Bryce Underwood" and
#    "bryce underwood" hash to the same key.
# ---------------------------------------------------------------------------

def normalise(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-z0-9 ]", "", ascii_name.lower())
    return " ".join(clean.split())

# ---------------------------------------------------------------------------
# 4. ESPN ROSTER FETCH
# ---------------------------------------------------------------------------

def fetch_espn_raw_names(espn_id: int) -> list[str]:
    """Returns raw (un-normalised) fullName strings from ESPN for debug inspection."""
    url = ESPN_ROSTER_URL.format(espn_id=espn_id)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        return []
    data = resp.json()
    return [
        athlete.get("fullName", "")
        for group in data.get("athletes", [])
        for athlete in group.get("items", [])
        if athlete.get("fullName")
    ]


def fetch_espn_roster(espn_id: int) -> set[str]:
    """
    Calls the ESPN roster endpoint and returns a set of normalised player names.
    ESPN groups players by unit (Offense, Defense, Special Teams) under 'athletes'.
    Returns an empty set on any error.
    """
    url = ESPN_ROSTER_URL.format(espn_id=espn_id)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"    [ERROR] ESPN API request failed: {exc}")
        return set()

    data = resp.json()

    scraped_names = [
        athlete.get("fullName")
        for group in data.get("athletes", [])
        for athlete in group.get("items", [])
    ]

    return {normalise(n) for n in scraped_names if n}

# ---------------------------------------------------------------------------
# 5. MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    # ── Fetch teams from Supabase ────────────────────────────────────────────
    print("Fetching teams from Supabase...")
    teams_resp = supabase.table("teams").select("id, university_name").execute()
    teams = teams_resp.data or []
    print(f"  {len(teams)} team(s) found: {[t['university_name'] for t in teams]}\n")

    # ── Fetch all players from Supabase ──────────────────────────────────────
    print("Fetching players from Supabase...")
    players_resp = supabase.table("players").select("id, name, team_id, player_tag").execute()
    all_players = players_resp.data or []
    print(f"  {len(all_players)} player(s) found.\n")

    # Group players by team_id for O(1) lookup
    players_by_team: dict[str, list[dict]] = {}
    for p in all_players:
        players_by_team.setdefault(p["team_id"], []).append(p)

    # ── Iterate teams ────────────────────────────────────────────────────────
    total_promoted = 0

    print("=" * 65)
    for team in teams:
        team_id   = team["id"]
        team_name = team["university_name"]
        espn_id   = ESPN_TEAM_MAP.get(team_name.lower())

        if not espn_id:
            print(f"\n[SKIP] '{team_name}' — no ESPN ID mapping found.")
            continue

        print(f"\n[{team_name}]  ESPN ID: {espn_id}")

        # Fetch live roster from ESPN
        roster_names = fetch_espn_roster(espn_id)
        print(f"  ESPN returned {len(roster_names)} player(s) on roster.")

        # ── DEBUG: Michigan name inspection ─────────────────────────────────
        if team_name.lower() == "michigan":
            print("\n  [DEBUG] Raw ESPN names for Michigan:")
            raw_names = fetch_espn_raw_names(espn_id)
            for n in sorted(raw_names):
                print(f"    ESPN  → '{n}'")
            print("\n  [DEBUG] Supabase player names assigned to Michigan:")
            for p in players_by_team.get(team_id, []):
                print(f"    DB    → '{p['name']}'  (normalised: '{normalise(p['name'])}')")
            print()

        if not roster_names:
            print("  No roster data — skipping update for this team.")
            time.sleep(REQUEST_DELAY)
            continue

        # Match our DB players against the ESPN roster
        team_players   = players_by_team.get(team_id, [])
        promoted_names: list[str] = []

        for player in team_players:
            if normalise(player["name"]) in roster_names:
                supabase.table("players").update(
                    {"player_tag": "College Athlete"}
                ).eq("id", player["id"]).execute()
                promoted_names.append(player["name"])

        if promoted_names:
            print(f"  Promoted to 'College Athlete' ({len(promoted_names)}):")
            for name in promoted_names:
                print(f"    ✓ {name}")
        else:
            print("  No matching players found for promotion.")

        total_promoted += len(promoted_names)
        time.sleep(REQUEST_DELAY)

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print(f"Sync complete.  Total players promoted to 'College Athlete': {total_promoted}")


if __name__ == "__main__":
    main()
