"""
enrich_star_ratings.py
----------------------
Enriches College Athlete players in Supabase with historical 247Sports
Composite star ratings pulled from the CFBD (College Football Data) API.

Only targets players where player_tag = 'College Athlete' AND star_rating = 0.

Usage:
    python enrich_star_ratings.py

Requirements:
    pip install supabase python-dotenv requests
"""

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

RECRUITING_YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]

# Hardcoded overrides for anomalies CFBD misses or mislabels
MANUAL_OVERRIDES: dict[str, int] = {
    "gunner stockton": 4,
}

# ---------------------------------------------------------------------------
# 2. NAME NORMALISATION
# ---------------------------------------------------------------------------

def normalise(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-z0-9 ]", "", ascii_name.lower())
    return " ".join(clean.split())

# ---------------------------------------------------------------------------
# 3. FETCH DB PLAYERS
# ---------------------------------------------------------------------------

print("Fetching unrated College Athletes from Supabase...")
players_resp = (
    supabase.table("players")
    .select("id, name, player_tag, star_rating")
    .eq("player_tag", "College Athlete")
    .eq("star_rating", 0)
    .limit(3000)
    .execute()
)
players_to_enrich = players_resp.data or []
print(f"  {len(players_to_enrich)} player(s) need star ratings.\n")

# ---------------------------------------------------------------------------
# 4. BUILD RECRUIT DICTIONARY FROM CFBD
# ---------------------------------------------------------------------------

print("Fetching historical recruiting data from CFBD API...")
recruit_dict: dict[str, int] = {}

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
            stars = recruit.get("stars") or 3  # default to 3 for unrated D1 athletes
            key = normalise(raw_name)
            # Prefer higher star rating if a player appears in multiple years
            if key not in recruit_dict or stars > recruit_dict[key]:
                recruit_dict[key] = stars
            year_count += 1
        print(f"  {year}: {year_count} recruits loaded  (dict size: {len(recruit_dict)})")
    except requests.RequestException as exc:
        print(f"  {year}: [ERROR] Request failed — {exc}")

print(f"\nTotal unique recruits in lookup dict: {len(recruit_dict)}\n")

# ---------------------------------------------------------------------------
# 5. MATCH & UPDATE
# ---------------------------------------------------------------------------

print("Matching players and writing star ratings to Supabase...")
enriched_count = 0
unmatched: list[str] = []

dict_keys = list(recruit_dict.keys())

for player in players_to_enrich:
    key   = normalise(player["name"])

    # 1. Manual override — checked first, highest priority
    stars = MANUAL_OVERRIDES.get(key)

    # 2. Exact CFBD match
    if stars is None:
        stars = recruit_dict.get(key)

    # 3. Fuzzy fallback when exact match fails
    if stars is None:
        fuzzy = difflib.get_close_matches(key, dict_keys, n=1, cutoff=0.85)
        if fuzzy:
            matched_key = fuzzy[0]
            stars = recruit_dict[matched_key]
            print(f"  [Fuzzy Match] Mapped ESPN \"{player['name']}\" to CFBD \"{matched_key}\"")

    if stars is not None:
        supabase.table("players").update(
            {"star_rating": stars}
        ).eq("id", player["id"]).execute()
        enriched_count += 1
        time.sleep(0.1)
    else:
        unmatched.append(player["name"])

# ---------------------------------------------------------------------------
# 6. SUMMARY
# ---------------------------------------------------------------------------

print(f"\n{'=' * 55}")
print(f"Successfully enriched {enriched_count} player(s) with historical star ratings.")

if unmatched:
    print(f"\nNo CFBD match found for {len(unmatched)} player(s):")
    for name in sorted(unmatched):
        print(f"  — {name}")
