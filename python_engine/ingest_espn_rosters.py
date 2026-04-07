"""
ingest_espn_rosters.py
----------------------
ELT pipeline: fetches every player from ESPN college football roster endpoints
and upserts them into our Supabase `players` table.

  - Existing players (matched by name + team_id): player_tag set to 'College Athlete'
  - New players: inserted with baseline values and player_tag 'College Athlete'

Usage:
    python ingest_espn_rosters.py

Requirements:
    pip install supabase python-dotenv requests
"""

import os
import time
import uuid
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

ESPN_ROSTER_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/{espn_id}/roster?limit=500"

REQUEST_DELAY = 1.0  # seconds between ESPN API calls

# ---------------------------------------------------------------------------
# 2. ESPN TEAM ID MAP
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
# ---------------------------------------------------------------------------

def normalise(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-z0-9 ]", "", ascii_name.lower())
    return " ".join(clean.split())

# ---------------------------------------------------------------------------
# 4. ESPN ROSTER FETCH
# ---------------------------------------------------------------------------

def fetch_espn_roster(espn_id: int) -> list[dict]:
    """
    Returns a list of dicts with 'raw_name' and 'position' for every player
    on the ESPN roster. Returns an empty list on any error.
    """
    url = ESPN_ROSTER_URL.format(espn_id=espn_id)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"    [ERROR] ESPN API request failed: {exc}")
        return []

    data = resp.json()

    players = []
    for group in data.get("athletes", []):
        for athlete in group.get("items", []):
            raw_name = athlete.get("fullName", "").strip()
            if not raw_name:
                continue
            position = (
                athlete.get("position", {}).get("abbreviation", "").strip().upper()
                or "ATH"
            )
            players.append({"raw_name": raw_name, "position": position})

    return players

# ---------------------------------------------------------------------------
# 5. MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    # ── Fetch teams ──────────────────────────────────────────────────────────
    print("Fetching teams from Supabase...")
    teams_resp = supabase.table("teams").select("id, university_name").execute()
    teams = teams_resp.data or []
    print(f"  {len(teams)} team(s) found: {[t['university_name'] for t in teams]}\n")

    # ── Fetch all existing players once (avoid per-player round-trips) ───────
    print("Fetching existing players from Supabase...")
    players_resp = supabase.table("players").select("id, name, team_id").execute()
    all_db_players = players_resp.data or []
    print(f"  {len(all_db_players)} existing player(s) in database.\n")

    # Build a fast lookup: (normalised_name, team_id) -> player_id
    existing: dict[tuple[str, str], str] = {
        (normalise(p["name"]), p["team_id"]): p["id"]
        for p in all_db_players
        if p.get("name") and p.get("team_id")
    }

    # ── Iterate teams ────────────────────────────────────────────────────────
    total_updated  = 0
    total_inserted = 0

    print("=" * 65)
    for team in teams:
        team_id   = team["id"]
        team_name = team["university_name"]
        espn_id   = ESPN_TEAM_MAP.get(team_name.lower())

        if not espn_id:
            print(f"\n[SKIP] '{team_name}' — no ESPN ID mapping found.")
            continue

        print(f"\n[{team_name}]  ESPN ID: {espn_id}")

        espn_players = fetch_espn_roster(espn_id)
        print(f"  ESPN returned {len(espn_players)} player(s).")

        if not espn_players:
            time.sleep(REQUEST_DELAY)
            continue

        team_updated  = 0
        team_inserted = 0

        for player in espn_players:
            raw_name = player["raw_name"]
            position = player["position"]
            key      = (normalise(raw_name), team_id)

            if key in existing:
                # Player exists — promote their tag, leave valuation untouched
                player_id = existing[key]
                supabase.table("players").update(
                    {"player_tag": "College Athlete"}
                ).eq("id", player_id).execute()
                team_updated += 1
            else:
                # New player — insert baseline record
                new_id = str(uuid.uuid4())
                supabase.table("players").insert({
                    "id":               new_id,
                    "name":             raw_name,
                    "team_id":          team_id,
                    "position":         position,
                    "player_tag":       "College Athlete",
                    "star_rating":      0,
                    "cfo_valuation":    0,
                    "experience_level": "College Veteran",
                }).execute()
                # Register in local lookup to catch duplicates within the same run
                existing[key] = new_id
                team_inserted += 1

        print(f"  Updated : {team_updated}   Inserted: {team_inserted}")
        total_updated  += team_updated
        total_inserted += team_inserted

        time.sleep(REQUEST_DELAY)

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print(f"Ingest complete.")
    print(f"  Total updated  (tag → 'College Athlete') : {total_updated}")
    print(f"  Total inserted (new baseline records)    : {total_inserted}")
    print(f"  Grand total players processed            : {total_updated + total_inserted}")


if __name__ == "__main__":
    main()
