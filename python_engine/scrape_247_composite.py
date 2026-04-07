"""
scrape_247_composite.py
-----------------------
Scrapes the 247Sports Composite recruit rankings for 2026 and 2027 and
enriches our High School Recruits with national_rank and composite_score.

Strategy:
  - Fetches pages 1-8 for each year from the Composite rankings endpoint.
  - Matches scraped names against Supabase players using exact lookup first,
    then difflib fuzzy matching (cutoff=0.85) as a fallback.
  - Writes national_rank (int) and composite_score (float) to the players table.

Usage:
    python scrape_247_composite.py

Requirements:
    pip install supabase python-dotenv requests beautifulsoup4
"""

import os
import re
import time
import difflib
import unicodedata
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

# Robust browser-like headers to reduce bot-block risk (mirrors verify_247_bluechips.py)
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

SCRAPE_YEARS  = [2026, 2027]
PAGES_PER_YEAR = 8
PAGE_DELAY    = 2  # seconds between page requests

# ---------------------------------------------------------------------------
# 2. NAME NORMALISATION
# ---------------------------------------------------------------------------

def normalise(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-z0-9 ]", "", ascii_name.lower())
    return " ".join(clean.split())

# ---------------------------------------------------------------------------
# 3. FETCH HIGH SCHOOL RECRUITS FROM SUPABASE
# ---------------------------------------------------------------------------

print("Fetching High School Recruits from Supabase...")
recruits_resp = (
    supabase.table("players")
    .select("id, name")
    .eq("player_tag", "High School Recruit")
    .limit(5000)
    .execute()
)
recruits = recruits_resp.data or []
print(f"  {len(recruits)} recruit(s) found.\n")

if not recruits:
    print("No High School Recruits in database. Exiting.")
    raise SystemExit(0)

# ---------------------------------------------------------------------------
# 4. SCRAPE 247SPORTS COMPOSITE RANKINGS
# ---------------------------------------------------------------------------

def parse_rank(item: BeautifulSoup) -> int | None:
    """
    Extract the national rank integer from a ranking list item.
    247Sports renders it in .primary or .rank elements.
    """
    # Preferred: explicit .primary rank block
    for selector in [".primary", ".rank-column .rank", ".rankings-page__item--rank"]:
        tag = item.select_one(selector)
        if tag:
            text = tag.get_text(strip=True)
            # Strip any non-digit prefix/suffix (e.g. "NR", "#12", ordinals)
            digits = re.sub(r"[^\d]", "", text)
            if digits:
                return int(digits)
    return None


def parse_score(item: BeautifulSoup) -> float | None:
    """
    Extract the composite score decimal (e.g. 0.9998) from a ranking list item.
    247Sports typically places it in a .score, .rankings-page__item--score, or
    .ranking-score element.
    """
    for selector in [
        ".score",
        ".rankings-page__item--score",
        ".ranking-score",
        ".composite-score",
    ]:
        tag = item.select_one(selector)
        if tag:
            text = tag.get_text(strip=True)
            # Match a decimal like "0.9998" or "1.0000"
            match = re.search(r"0\.\d{3,}", text)
            if match:
                return float(match.group())
    return None


def parse_name(item: BeautifulSoup) -> str | None:
    """
    Extract the recruit's display name from a ranking list item.
    """
    name_tag = (
        item.select_one(".meta .name a")
        or item.select_one(".rankings-page__name-link")
        or item.select_one(".name a")
        or item.select_one("a[href*='/Player/']")
    )
    if not name_tag:
        return None
    return name_tag.get_text(strip=True) or None


# composite_dict maps normalised_name -> {"rank": int, "score": float}
composite_dict: dict[str, dict] = {}

print("Scraping 247Sports Composite rankings...")
for year in SCRAPE_YEARS:
    print(f"\n  [{year}]")
    year_count = 0

    for page_num in range(1, PAGES_PER_YEAR + 1):
        url = (
            f"https://247sports.com/season/{year}-football/"
            f"CompositeRecruitRankings/?InstitutionGroup=HighSchool&Page={page_num}"
        )
        print(f"    Page {page_num}... ", end="", flush=True)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 403:
                print("[403 Blocked] Skipping page.")
                time.sleep(PAGE_DELAY)
                continue
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[ERROR] {exc}")
            time.sleep(PAGE_DELAY)
            continue

        soup  = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(".rankings-page__list-item")

        if not items:
            # Alternate container used in some years
            items = soup.select("li.recruit")

        page_count = 0
        for item in items:
            name = parse_name(item)
            if not name:
                continue

            rank  = parse_rank(item)
            score = parse_score(item)

            # Need at least one useful field to be worth storing
            if rank is None and score is None:
                continue

            key = normalise(name)

            # Keep first occurrence (page 1 is authoritative for rank order)
            if key not in composite_dict:
                composite_dict[key] = {"rank": rank, "score": score}
                page_count += 1
            else:
                # Fill in missing fields if a later page has them
                existing = composite_dict[key]
                if existing["rank"] is None and rank is not None:
                    existing["rank"] = rank
                if existing["score"] is None and score is not None:
                    existing["score"] = score

        print(f"{page_count} new recruit(s) parsed.  (dict total: {len(composite_dict)})")
        time.sleep(PAGE_DELAY)

print(f"\nScrape complete. Total unique recruits in composite_dict: {len(composite_dict)}\n")

if not composite_dict:
    print("No data scraped from 247Sports (possible bot block). Exiting.")
    raise SystemExit(1)

# ---------------------------------------------------------------------------
# 5. MATCH & UPDATE
# ---------------------------------------------------------------------------

dict_keys     = list(composite_dict.keys())
enriched      = 0
unmatched:    list[str] = []

print("=" * 65)
print("Matching recruits and writing to Supabase...")
print("=" * 65)

for player in recruits:
    key   = normalise(player["name"])
    entry = composite_dict.get(key)
    match_type = "exact"

    # Fuzzy fallback
    if entry is None:
        fuzzy = difflib.get_close_matches(key, dict_keys, n=1, cutoff=0.85)
        if fuzzy:
            matched_key = fuzzy[0]
            entry       = composite_dict[matched_key]
            match_type  = f'fuzzy → "{matched_key}"'

    if entry is not None:
        update_payload: dict = {}
        if entry["rank"] is not None:
            update_payload["national_rank"] = entry["rank"]
        if entry["score"] is not None:
            update_payload["composite_score"] = entry["score"]

        if update_payload:
            print(
                f"  [ENRICHED] {player['name']} ({match_type})  "
                f"rank={entry['rank']}  score={entry['score']}"
            )
            supabase.table("players").update(update_payload).eq("id", player["id"]).execute()
            enriched += 1
            time.sleep(0.1)
        else:
            # Entry existed but had no usable data
            unmatched.append(player["name"])
    else:
        unmatched.append(player["name"])

# ---------------------------------------------------------------------------
# 6. SUMMARY
# ---------------------------------------------------------------------------

print(f"\n{'=' * 65}")
print(f"Enrichment complete.")
print(f"  Recruits enriched    : {enriched}")
print(f"  Recruits unmatched   : {len(unmatched)}")
print(f"  Total recruits       : {len(recruits)}")

if unmatched:
    print(f"\nUnmatched players ({len(unmatched)}):")
    for name in sorted(unmatched):
        print(f"  — {name}")
