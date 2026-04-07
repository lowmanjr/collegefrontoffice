"""
build_rosetta_stone.py

MDM (Master Data Management) script to match Supabase players to their
canonical CFBD (College Football Data) IDs using multi-factor weighted
heuristic scoring (name similarity + team bonus + position bonus).
"""

import os
import time
import requests
from difflib import SequenceMatcher
from dotenv import load_dotenv
from supabase import create_client

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv(".env.local")

SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
CFBD_API_KEY = os.environ.get("CFBD_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or not CFBD_API_KEY:
    raise EnvironmentError(
        "Missing required env vars. Ensure .env.local contains "
        "NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, and CFBD_API_KEY."
    )

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CFBD_YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027]
MATCH_THRESHOLD = 1.0
NAME_QUICK_FILTER = 0.5
TEAM_BONUS = 0.25
POS_BONUS = 0.15


def normalise(value: str) -> str:
    """Lowercase, strip whitespace, collapse internal spaces."""
    return " ".join(value.lower().split()) if value else ""


# ---------------------------------------------------------------------------
# 1. Fetch all players from Supabase (paginated, with team join)
# ---------------------------------------------------------------------------

def fetch_all_players() -> list[dict]:
    players = []
    step = 1000
    offset = 0

    while True:
        response = (
            supabase.table("players")
            .select("id, name, position, cfbd_id, known_aliases, teams(university_name)")
            .range(offset, offset + step - 1)
            .execute()
        )
        batch = response.data
        if not batch:
            break
        players.extend(batch)
        print(f"  Fetched {len(players)} players so far...")
        if len(batch) < step:
            break
        offset += step

    print(f"Total players loaded: {len(players)}")
    return players


# ---------------------------------------------------------------------------
# 2. Fetch CFBD recruiting data (source of truth) — flat list
# ---------------------------------------------------------------------------

def fetch_cfbd_recruits() -> list[dict]:
    headers = {"Authorization": f"Bearer {CFBD_API_KEY}"}
    cfbd_recruits: list[dict] = []

    for year in CFBD_YEARS:
        url = f"https://api.collegefootballdata.com/recruiting/players?year={year}"
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            print(f"  [WARN] Year {year} returned HTTP {response.status_code} — skipping")
            continue

        recruits = response.json()
        year_count = 0
        for recruit in recruits:
            raw_name = recruit.get("name") or ""
            cfbd_id = recruit.get("id")
            if raw_name and cfbd_id is not None:
                cfbd_recruits.append({
                    "id": int(cfbd_id),
                    "name": normalise(raw_name),
                    "team": normalise(recruit.get("committedTo", "") or ""),
                    "position": normalise(recruit.get("position", "") or ""),
                })
                year_count += 1

        print(f"  Year {year}: {year_count} recruits loaded (total: {len(cfbd_recruits)})")

    print(f"CFBD recruit list built with {len(cfbd_recruits)} entries.")
    return cfbd_recruits


# ---------------------------------------------------------------------------
# 3. Multi-factor weighted scoring engine
# ---------------------------------------------------------------------------

def match_players(players: list[dict], cfbd_recruits: list[dict]) -> list[dict]:
    """
    Scores each unmatched Supabase player against all CFBD recruits using:
      - SequenceMatcher name similarity  (0.0 – 1.0)
      - Team match bonus                 (+0.25)
      - Position match bonus             (+0.15)

    A total_score >= 1.0 is treated as a verified match.
    """
    # Seed with IDs already committed in the DB so this run can't collide with them
    claimed_cfbd_ids: set[int] = {p["cfbd_id"] for p in players if p.get("cfbd_id") is not None}

    updates = []
    manual_review_count = 0

    for player in players:
        # Skip players already linked
        if player.get("cfbd_id") is not None:
            continue

        supabase_name = normalise(player.get("name") or "")
        supabase_position = normalise(player.get("position") or "")

        # Safely extract team name from the joined teams relation
        teams_data = player.get("teams")
        if isinstance(teams_data, list):
            university = teams_data[0].get("university_name") if teams_data else ""
        elif isinstance(teams_data, dict):
            university = teams_data.get("university_name") or ""
        else:
            university = ""
        supabase_team = normalise(university)

        best_score = 0.0
        best_recruit = None

        for recruit in cfbd_recruits:
            name_score = SequenceMatcher(None, supabase_name, recruit["name"]).ratio()

            # Quick filter — skip obviously poor name matches
            if name_score < NAME_QUICK_FILTER:
                continue

            team_bonus = TEAM_BONUS if supabase_team and supabase_team == recruit["team"] else 0.0
            pos_bonus = POS_BONUS if supabase_position and supabase_position == recruit["position"] else 0.0

            total_score = name_score + team_bonus + pos_bonus

            if total_score > best_score and recruit["id"] not in claimed_cfbd_ids:
                best_score = total_score
                best_recruit = recruit

        if best_score >= MATCH_THRESHOLD and best_recruit is not None:
            # Claim this ID immediately so no later player in this run can take it
            claimed_cfbd_ids.add(best_recruit["id"])
            # Deduplicated alias list
            aliases = list(dict.fromkeys([supabase_name, best_recruit["name"]]))
            updates.append({
                "id": player["id"],
                "cfbd_id": best_recruit["id"],
                "known_aliases": aliases,
            })
        else:
            print(f"[MANUAL REVIEW] Could not confidently match: {player['name']} "
                  f"(best score: {best_score:.3f})")
            manual_review_count += 1

    print(f"\nMatch engine complete — {len(updates)} matches found, "
          f"{manual_review_count} flagged for manual review.")
    return updates


# ---------------------------------------------------------------------------
# 4. Execute Supabase updates
# ---------------------------------------------------------------------------

def execute_updates(updates: list[dict]) -> None:
    locked = 0

    for i, payload in enumerate(updates, start=1):
        supabase.table("players").update(
            {"cfbd_id": payload["cfbd_id"], "known_aliases": payload["known_aliases"]}
        ).eq("id", payload["id"]).execute()

        locked += 1

        if i % 100 == 0:
            print(f"  Progress: {i}/{len(updates)} updates executed...")

        time.sleep(0.05)

    print(f"\nFinal summary: {locked} CFBD IDs locked into Supabase.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Rosetta Stone MDM Builder (Multi-Factor Entity Resolution) ===\n")

    print("[1/4] Fetching all players from Supabase...")
    players = fetch_all_players()

    print("\n[2/4] Fetching CFBD recruiting data...")
    cfbd_recruits = fetch_cfbd_recruits()

    print("\n[3/4] Running weighted scoring engine...")
    updates = match_players(players, cfbd_recruits)

    print("\n[4/4] Executing Supabase updates...")
    execute_updates(updates)

    print("\nDone.")
