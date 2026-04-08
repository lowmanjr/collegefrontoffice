"""
Scrape 247Sports composite rankings to backfill national_rank for HS recruits.

Usage: python scrape_247_ranks.py [--dry-run] [--year 2027]
"""

import logging
import sys
import re
import time
import unicodedata
import requests
from bs4 import BeautifulSoup
from supabase_client import supabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def normalize(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower().strip()
    name = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", name)
    name = re.sub(r"[^a-z\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def scrape_page(url: str) -> list[dict]:
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    recruits = []
    items = soup.select(".rankings-page__list-item")
    for item in items:
        try:
            # Rank — look for the primary rank number
            rank_el = item.select_one(".rank-column .primary")
            if not rank_el:
                rank_el = item.select_one(".rankings-page__rank-number")
            rank = None
            if rank_el:
                rank_text = rank_el.get_text(strip=True)
                if rank_text.isdigit():
                    rank = int(rank_text)

            # Name
            name_el = item.select_one("a.rankings-page__name-link")
            if not name_el:
                continue
            name = name_el.get_text(strip=True)

            if name and rank:
                recruits.append({
                    "name": name,
                    "normalized": normalize(name),
                    "national_rank": rank,
                })
        except Exception as e:
            log.warning(f"Error parsing item: {e}")
            continue

    return recruits


def main():
    dry_run = "--dry-run" in sys.argv

    year = 2027
    for i, arg in enumerate(sys.argv):
        if arg == "--year" and i + 1 < len(sys.argv):
            year = int(sys.argv[i + 1])

    log.info(f"Scraping 247Sports {year} composite rankings for national ranks...")

    all_recruits = []
    for page_num in range(1, 10):
        url = f"https://247sports.com/season/{year}-football/compositerecruitrankings/?page={page_num}"
        log.info(f"  Fetching page {page_num}")
        try:
            page_recruits = scrape_page(url)
            if not page_recruits:
                log.info(f"  Page {page_num} returned 0 — stopping.")
                break
            all_recruits.extend(page_recruits)
            log.info(f"  Got {len(page_recruits)} recruits (total: {len(all_recruits)})")
            time.sleep(1.5)
        except Exception as e:
            log.warning(f"  Error on page {page_num}: {e}")
            break

    log.info(f"Scraped {len(all_recruits)} recruits with ranks")

    if not all_recruits:
        return

    # Fetch DB recruits for this year
    log.info("Fetching DB recruits...")
    all_players = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, national_rank, hs_grad_year")
            .eq("player_tag", "High School Recruit")
            .eq("hs_grad_year", year)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    log.info(f"Found {len(all_players)} DB recruits for {year}")

    name_lookup = {}
    for p in all_players:
        norm = normalize(p["name"])
        name_lookup[norm] = p

    matched = 0
    skipped = 0
    no_match = 0

    for recruit in all_recruits:
        db_player = name_lookup.get(recruit["normalized"])
        if not db_player:
            no_match += 1
            continue

        if db_player.get("national_rank") == recruit["national_rank"]:
            skipped += 1
            continue

        if dry_run:
            if matched < 20:
                log.info(f"  [DRY RUN] {db_player['name']} -> rank #{recruit['national_rank']}")
        else:
            supabase.table("players").update({
                "national_rank": recruit["national_rank"]
            }).eq("id", db_player["id"]).execute()

        matched += 1

    log.info(f"Done. Updated: {matched}, Already correct: {skipped}, No DB match: {no_match}")
    if dry_run:
        log.info("(Dry run — no changes written)")


if __name__ == "__main__":
    main()
