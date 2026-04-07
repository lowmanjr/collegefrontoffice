"""
verify_247_bluechips.py
-----------------------
Patches missing star ratings for College Athletes sitting at 0 stars by
scraping the 247Sports national Composite rankings for 2021–2025.

Only targets players where player_tag = 'College Athlete' AND star_rating = 0.

Usage:
    python verify_247_bluechips.py

Requirements:
    pip install supabase python-dotenv requests beautifulsoup4
"""

import os
import time
import difflib
import unicodedata
import re
import requests
from bs4 import BeautifulSoup
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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}

SCRAPE_YEARS  = [2021, 2022, 2023, 2024, 2025]
REQUEST_DELAY = 3  # seconds between year requests

# ---------------------------------------------------------------------------
# 2. NAME NORMALISATION
# ---------------------------------------------------------------------------

def normalise(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-z0-9 ]", "", ascii_name.lower())
    return " ".join(clean.split())

# ---------------------------------------------------------------------------
# 3. FETCH 0-STAR COLLEGE ATHLETES FROM SUPABASE
# ---------------------------------------------------------------------------

print("Fetching 0-star College Athletes from Supabase...")
players_resp = (
    supabase.table("players")
    .select("id, name, star_rating, player_tag")
    .eq("player_tag", "College Athlete")
    .eq("star_rating", 0)
    .limit(5000)
    .execute()
)
players_to_patch = players_resp.data or []
print(f"  {len(players_to_patch)} player(s) need verification.\n")

if not players_to_patch:
    print("Nothing to patch. Exiting.")
    raise SystemExit(0)

# ---------------------------------------------------------------------------
# 4. BUILD BLUE-CHIP DICTIONARY FROM 247SPORTS
# ---------------------------------------------------------------------------

def parse_star_rating(item: BeautifulSoup) -> int:
    """
    Attempt to read the star rating from filled star icons.
    247Sports marks filled stars with a class like 'yellow' or 'icon-starsolid'
    vs empty stars with 'icon-starempty'. Falls back to 4 if unreadable —
    anyone in the top ~400 national rankings is at minimum a 4-star prospect.
    """
    filled = (
        item.select(".icon-starsolid.yellow")
        or item.select(".star-commit-25")
        or item.select(".ratings-stars .filled")
    )
    if filled:
        return min(len(filled), 5)
    return 4  # safe default for top national recruits

blue_chip_dict: dict[str, int] = {}

print("Scraping 247Sports national Composite rankings...")
for year in SCRAPE_YEARS:
    url = f"https://247sports.com/season/{year}-football/RecruitRankings/?InstitutionGroup=HighSchool"
    print(f"  Fetching {year}... ", end="", flush=True)

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 403:
            print(f"[403 Blocked] Skipping {year}.")
            time.sleep(REQUEST_DELAY)
            continue
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[ERROR] {exc}")
        time.sleep(REQUEST_DELAY)
        continue

    soup  = BeautifulSoup(resp.text, "html.parser")
    items = soup.select(".rankings-page__list-item")
    print(f"{len(items)} list items found.")

    year_count = 0
    for item in items:
        # Name is usually inside .meta .name a or .rankings-page__name-link
        name_tag = (
            item.select_one(".meta .name a")
            or item.select_one(".rankings-page__name-link")
            or item.select_one(".name a")
        )
        if not name_tag:
            continue
        raw_name = name_tag.get_text(strip=True)
        if not raw_name:
            continue

        stars = parse_star_rating(item)
        key   = normalise(raw_name)

        # Prefer higher star rating if player appears in multiple years
        if key not in blue_chip_dict or stars > blue_chip_dict[key]:
            blue_chip_dict[key] = stars
        year_count += 1

    print(f"    → {year_count} recruits added  (dict size: {blue_chip_dict.__len__()})")
    time.sleep(REQUEST_DELAY)

print(f"\nTotal unique recruits in 247Sports dict: {len(blue_chip_dict)}\n")

if not blue_chip_dict:
    print("No data scraped from 247Sports (possible bot block). Exiting.")
    raise SystemExit(1)

# ---------------------------------------------------------------------------
# 5. MATCH & PATCH
# ---------------------------------------------------------------------------

dict_keys     = list(blue_chip_dict.keys())
patched_count = 0
unmatched:    list[str] = []

print("Matching and patching players...")
for player in players_to_patch:
    key   = normalise(player["name"])
    stars = blue_chip_dict.get(key)
    match_type = "exact"

    # Fuzzy fallback
    if stars is None:
        fuzzy = difflib.get_close_matches(key, dict_keys, n=1, cutoff=0.85)
        if fuzzy:
            matched_key = fuzzy[0]
            stars       = blue_chip_dict[matched_key]
            match_type  = f"fuzzy → \"{matched_key}\""

    if stars is not None:
        print(f"  [PATCHED] {player['name']} found on 247Sports ({match_type}). Updating to {stars} stars.")
        supabase.table("players").update(
            {"star_rating": stars}
        ).eq("id", player["id"]).execute()
        patched_count += 1
        time.sleep(0.1)
    else:
        unmatched.append(player["name"])

# ---------------------------------------------------------------------------
# 6. SUMMARY
# ---------------------------------------------------------------------------

print(f"\n{'=' * 60}")
print(f"Verification complete.  Patched: {patched_count}  |  Still unmatched: {len(unmatched)}")

if unmatched:
    print(f"\nPlayers with no 247Sports match ({len(unmatched)}):")
    for name in sorted(unmatched):
        print(f"  — {name}")
