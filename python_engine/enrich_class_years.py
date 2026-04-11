"""
enrich_class_years.py
---------------------
Enriches all players (College Athletes and High School Recruits) in Supabase
with their recruiting class_year, pulled from the CFBD API.

Only targets players where class_year IS NULL.

Usage:
    python enrich_class_years.py

Requirements:
    pip install supabase python-dotenv requests
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import time
import difflib
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
CFBD_API_KEY      = os.getenv("CFBD_API_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise EnvironmentError("Missing Supabase credentials in .env.local")
if not CFBD_API_KEY:
    raise EnvironmentError("Missing CFBD_API_KEY in .env.local")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

CFBD_HEADERS = {"Authorization": f"Bearer {CFBD_API_KEY}"}
CFBD_URL     = "https://api.collegefootballdata.com/recruiting/players?year={year}"

RECRUITING_YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027]

# ---------------------------------------------------------------------------
# 2. NAME NORMALISATION
# ---------------------------------------------------------------------------

def normalise(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-z0-9 ]", "", ascii_name.lower())
    return " ".join(clean.split())

# ---------------------------------------------------------------------------
# 3. FETCH DB PLAYERS (paginated)
# ---------------------------------------------------------------------------

def fetch_players_without_class_year() -> list[dict]:
    """Fetches all players where class_year IS NULL via pagination."""
    PAGE_SIZE = 1000
    all_players: list[dict] = []
    offset = 0

    print("Fetching players with no class_year from Supabase...")
    while True:
        resp = (
            supabase.table("players")
            .select("id, name")
            .is_("class_year", "null")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        print(f"  Fetched {len(all_players)} players so far...")

        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    print(f"  Done. {len(all_players)} total players need a class year.\n")
    return all_players

# ---------------------------------------------------------------------------
# 4. BUILD RECRUIT YEAR DICTIONARY FROM CFBD
# ---------------------------------------------------------------------------

def build_recruit_year_dict() -> dict[str, int]:
    """
    Calls the CFBD recruiting endpoint for each year and builds a lookup dict.
    Key:   normalise(recruit name)
    Value: recruiting class year (int)

    If a player appears in multiple years (e.g. reclassifications), the most
    recent year wins so we store the true enrollment class year.
    """
    recruit_year_dict: dict[str, int] = {}

    print("Fetching recruiting class data from CFBD API...")
    for year in RECRUITING_YEARS:
        url = CFBD_URL.format(year=year)
        try:
            resp = requests.get(url, headers=CFBD_HEADERS, timeout=20)
            resp.raise_for_status()
            recruits = resp.json()
            year_count = 0
            for recruit in recruits:
                raw_name = recruit.get("name", "").strip()
                if not raw_name:
                    continue
                key = normalise(raw_name)
                # Prefer the most recent year if player appears in multiple classes
                recruit_year_dict[key] = year
                year_count += 1
            print(f"  {year}: {year_count} recruits loaded  (dict size: {len(recruit_year_dict)})")
        except requests.RequestException as exc:
            print(f"  {year}: [ERROR] Request failed — {exc}")

    print(f"\nTotal unique recruits in lookup dict: {len(recruit_year_dict)}\n")
    return recruit_year_dict

# ---------------------------------------------------------------------------
# 5. MATCH & UPDATE
# ---------------------------------------------------------------------------

def match_and_update(players: list[dict], recruit_year_dict: dict[str, int]) -> None:
    dict_keys     = list(recruit_year_dict.keys())
    enriched      = 0
    unmatched: list[str] = []

    print("Matching players and writing class years to Supabase...")

    for player in players:
        key        = normalise(player["name"])
        class_year = None

        # 1. Exact match
        class_year = recruit_year_dict.get(key)

        # 2. Fuzzy fallback
        if class_year is None:
            fuzzy = difflib.get_close_matches(key, dict_keys, n=1, cutoff=0.85)
            if fuzzy:
                matched_key = fuzzy[0]
                class_year  = recruit_year_dict[matched_key]
                print(f"  [Fuzzy] \"{player['name']}\"  →  \"{matched_key}\"  ({class_year})")

        if class_year is not None:
            supabase.table("players").update(
                {"class_year": class_year}
            ).eq("id", player["id"]).execute()
            enriched += 1
            time.sleep(0.05)
        else:
            unmatched.append(player["name"])

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'=' * 55}")
    print(f"Successfully enriched {enriched} players with their class year.")

    if unmatched:
        print(f"\nNo CFBD match found for {len(unmatched)} player(s):")
        for name in sorted(unmatched):
            print(f"  — {name}")

# ---------------------------------------------------------------------------
# 6. MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    players          = fetch_players_without_class_year()
    recruit_year_dict = build_recruit_year_dict()

    if not players:
        print("All players already have a class year. Nothing to do.")
        return

    match_and_update(players, recruit_year_dict)


if __name__ == "__main__":
    main()
