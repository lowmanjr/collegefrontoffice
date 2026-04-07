"""
Scrape 247Sports composite recruit rankings for headshot URLs.
Matches recruits by name + position and writes headshot_url to players table.

Usage: python scrape_247_headshots.py [--dry-run] [--year 2027]
"""

import logging
import sys
import unicodedata
import re
import time
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
    """Scrape one page of 247 composite rankings."""
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    recruits = []
    items = soup.select(".rankings-page__list-item")
    for item in items:
        try:
            # Name
            name_el = item.select_one(".recruit .rankings-page__name-link")
            if not name_el:
                name_el = item.select_one("a.rankings-page__name-link")
            if not name_el:
                continue
            name = name_el.get_text(strip=True)

            # Position
            pos_el = item.select_one(".position")
            position = pos_el.get_text(strip=True) if pos_el else None

            # Headshot URL — try data-src first, then src
            img_el = item.select_one(".recruit-image img, .circle-image-block img, img")
            headshot = None
            if img_el:
                headshot = img_el.get("data-src") or img_el.get("src")
                # Skip placeholder/default images
                if headshot and ("default" in headshot.lower() or "placeholder" in headshot.lower()):
                    headshot = None

            if name and headshot:
                recruits.append({
                    "name": name,
                    "normalized": normalize(name),
                    "position": position,
                    "headshot_url": headshot,
                })
        except Exception as e:
            log.warning(f"Error parsing item: {e}")
            continue

    return recruits


def main():
    dry_run = "--dry-run" in sys.argv

    # Parse year arg
    year = 2027  # default
    for i, arg in enumerate(sys.argv):
        if arg == "--year" and i + 1 < len(sys.argv):
            year = int(sys.argv[i + 1])

    log.info(f"Scraping 247Sports {year} composite rankings...")

    # Scrape multiple pages to get as many recruits as possible
    all_recruits = []
    for page_num in range(1, 10):  # Up to 9 pages (about 450 recruits)
        url = f"https://247sports.com/season/{year}-football/compositerecruitrankings/?page={page_num}"
        log.info(f"  Fetching page {page_num}: {url}")
        try:
            page_recruits = scrape_page(url)
            if not page_recruits:
                log.info(f"  Page {page_num} returned 0 recruits — stopping.")
                break
            all_recruits.extend(page_recruits)
            log.info(f"  Got {len(page_recruits)} recruits (total: {len(all_recruits)})")
            time.sleep(1.5)  # Be polite
        except Exception as e:
            log.warning(f"  Error on page {page_num}: {e}")
            break

    log.info(f"Scraped {len(all_recruits)} total recruits from 247Sports")

    if not all_recruits:
        log.info("Nothing scraped. Exiting.")
        return

    # Fetch our HS recruits from DB
    log.info("Fetching HS recruits from Supabase...")
    all_players = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, position, headshot_url, hs_grad_year")
            .eq("player_tag", "High School Recruit")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    log.info(f"Found {len(all_players)} HS recruits in DB")

    # Filter to target year if applicable
    year_players = [p for p in all_players if p.get("hs_grad_year") == year]
    log.info(f"  {len(year_players)} are class of {year}")

    # Build lookup: normalized name -> player
    name_lookup = {}
    for p in year_players:
        norm = normalize(p["name"])
        name_lookup[norm] = p

    # Match and update
    matched = 0
    skipped_has_headshot = 0
    skipped_no_match = 0

    for recruit in all_recruits:
        db_player = name_lookup.get(recruit["normalized"])
        if not db_player:
            skipped_no_match += 1
            continue

        # Skip if already has a headshot (e.g. from ESPN)
        if db_player.get("headshot_url"):
            skipped_has_headshot += 1
            continue

        if dry_run:
            log.info(f"  [DRY RUN] {db_player['name']} -> {recruit['headshot_url'][:60]}...")
        else:
            supabase.table("players").update({
                "headshot_url": recruit["headshot_url"]
            }).eq("id", db_player["id"]).execute()

        matched += 1

    log.info(f"Done. Matched: {matched}, Already had headshot: {skipped_has_headshot}, No DB match: {skipped_no_match}")
    if dry_run:
        log.info("(Dry run — no changes written)")


if __name__ == "__main__":
    main()
