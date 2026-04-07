"""
sync_transfer_portal.py
------------------------
Event-driven transfer portal sync. Reads the CFBD /player/portal transaction
log for 2024 and 2025 and reconciles our Supabase players table against every
incoming transfer to one of our 16 tracked teams.

For each transfer whose destination matches a tracked team:
  - If the player already exists in our DB  → update their team_id (move)
  - If they don't exist                     → insert them from scratch

This catches portal arrivals from non-tracked schools (e.g. a QB who
transferred from Arizona State to LSU) without waiting for a roster re-ingest.

Confirmed CFBD /player/portal fields (inspected 2026-04-01):
  firstName, lastName, position, origin, destination,
  transferDate, rating, stars, eligibility, season

Usage:
    python sync_transfer_portal.py

Requirements:
    pip install supabase python-dotenv requests
"""

import os
import re
import time
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
    raise EnvironmentError("Missing Supabase credentials in .env.local")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

CFBD_API_KEY = os.getenv("CFBD_API_KEY")
if not CFBD_API_KEY:
    raise EnvironmentError("Missing CFBD_API_KEY in .env.local")

CFBD_HEADERS  = {"Authorization": f"Bearer {CFBD_API_KEY}", "Accept": "application/json"}
PORTAL_URL    = "https://api.collegefootballdata.com/player/portal"
PORTAL_YEARS  = [2024, 2025]

# ---------------------------------------------------------------------------
# 2. NAME NORMALIZATION
# ---------------------------------------------------------------------------

_SUFFIXES = re.compile(r"\b(jr\.?|sr\.?|ii|iii|iv|v)\b", re.IGNORECASE)
_PUNCT    = re.compile(r"[^\w\s]")


def normalize_name(name: str) -> str:
    name = name.lower()
    name = _SUFFIXES.sub("", name)
    name = _PUNCT.sub("", name)
    return " ".join(name.split())


# ---------------------------------------------------------------------------
# 3. FETCH DATABASE STATE
# ---------------------------------------------------------------------------

def fetch_team_map() -> dict[str, str]:
    """
    Returns team_map: university_name (str) -> team_id (UUID str).
    Also builds a normalized-name variant so slightly different API spellings
    still match (e.g. 'LSU' vs 'Lsu' edge cases).
    """
    print("Fetching teams from Supabase...")
    resp = supabase.table("teams").select("id, university_name").execute()
    team_map: dict[str, str] = {}
    for row in (resp.data or []):
        name = row["university_name"]
        tid  = row["id"]
        team_map[name]                   = tid   # exact
        team_map[normalize_name(name)]   = tid   # normalized fallback
    team_count = len(resp.data or [])
    print(f"  {team_count} team(s) loaded  ({team_count * 2} lookup keys with normalized variants).\n")
    return team_map


def fetch_player_map() -> dict[str, str]:
    """
    Returns player_map: normalize_name(name) -> Supabase UUID id.
    Covers all College Athletes (paginated).
    """
    PAGE_SIZE   = 1000
    all_players: list[dict] = []
    offset      = 0

    print("Fetching College Athletes from Supabase...")
    while True:
        resp = (
            supabase.table("players")
            .select("id, name")
            .eq("player_tag", "College Athlete")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = resp.data or []
        if not batch:
            break
        all_players.extend(batch)
        offset += PAGE_SIZE

    player_map: dict[str, str] = {
        normalize_name(p["name"]): p["id"]
        for p in all_players
        if p.get("name")
    }
    print(f"  {len(player_map)} player(s) indexed.\n")
    return player_map


# ---------------------------------------------------------------------------
# 4. FETCH MASTER TRANSFER LIST
# ---------------------------------------------------------------------------

def fetch_portal_entries() -> list[dict]:
    """
    Fetch /player/portal for each year in PORTAL_YEARS and return the
    combined, deduplicated list of transfer records.
    """
    combined: list[dict] = []

    for year in PORTAL_YEARS:
        print(f"  Fetching portal entries for {year}... ", end="", flush=True)
        try:
            r = requests.get(
                PORTAL_URL,
                headers=CFBD_HEADERS,
                params={"year": year},
                timeout=30,
            )
            if r.status_code == 401:
                raise SystemExit("[ERROR] 401 Unauthorized — check CFBD_API_KEY.")
            r.raise_for_status()
            entries = r.json()
        except requests.RequestException as exc:
            print(f"[ERROR] {exc}")
            continue

        print(f"{len(entries)} records.")
        combined.extend(entries)
        time.sleep(1)

    print(f"  Combined portal list: {len(combined)} total entries.\n")
    return combined


# ---------------------------------------------------------------------------
# 5. MATCH & UPSERT
# ---------------------------------------------------------------------------

def sync_transfers(
    portal_entries: list[dict],
    team_map: dict[str, str],
    player_map: dict[str, str],
) -> None:
    """
    Loop through portal entries filtered to our tracked teams.
    Update team_id for known players; insert new rows for unknowns.
    """
    moved    = 0
    inserted = 0
    skipped  = 0

    move_log:   list[str] = []
    insert_log: list[str] = []

    print("=" * 65)
    print("Processing transfer portal entries...")
    print("=" * 65)

    for entry in portal_entries:
        destination = (entry.get("destination") or "").strip()

        # Resolve destination to a team_id (exact, then normalized)
        team_id = team_map.get(destination) or team_map.get(normalize_name(destination))
        if not team_id:
            skipped += 1
            continue  # destination not one of our 16 teams

        first = (entry.get("firstName") or "").strip()
        last  = (entry.get("lastName")  or "").strip()
        name  = f"{first} {last}".strip()
        if not name:
            skipped += 1
            continue

        position  = (entry.get("position") or "ATH").strip().upper()
        norm_name = normalize_name(name)

        if norm_name in player_map:
            # Player exists — update their team to the destination
            player_uuid = player_map[norm_name]
            supabase.table("players").update(
                {"team_id": team_id}
            ).eq("id", player_uuid).execute()

            origin = entry.get("origin") or "Unknown"
            move_log.append(f"  [MOVED]  {name:<28}  {position:<6}  {origin} -> {destination}")
            player_map[norm_name] = player_uuid  # no change needed but keeps map current
            moved += 1

        else:
            # Player not in our DB — insert from scratch
            supabase.table("players").insert({
                "name":       name,
                "team_id":    team_id,
                "position":   position,
                "player_tag": "College Athlete",
                "class_year": 3,  # default Junior per spec
            }).execute()

            insert_log.append(f"  [NEW]    {name:<28}  {position:<6}  -> {destination}")
            player_map[norm_name] = "__inserted__"  # prevent duplicate inserts this run
            inserted += 1

    # Print logs
    if move_log:
        print("\nPlayers moved to new team:")
        for line in move_log:
            print(line)

    if insert_log:
        print("\nNew players inserted:")
        for line in insert_log:
            print(line)

    print(f"\n{'=' * 65}")
    print(f"Transfer portal sync complete.")
    print(f"  Existing players moved  : {moved}")
    print(f"  New players inserted    : {inserted}")
    print(f"  Non-tracked destination : {skipped}")
    print(f"  Total entries processed : {len(portal_entries)}")
    print("=" * 65)


# ---------------------------------------------------------------------------
# 6. MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    team_map   = fetch_team_map()
    player_map = fetch_player_map()

    print("Fetching CFBD transfer portal log...")
    portal_entries = fetch_portal_entries()

    if not portal_entries:
        print("No portal entries returned. Exiting.")
        return

    sync_transfers(portal_entries, team_map, player_map)


if __name__ == "__main__":
    main()
