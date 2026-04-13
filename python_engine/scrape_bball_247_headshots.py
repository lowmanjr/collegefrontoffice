"""
Scrape 247Sports basketball composite recruit rankings for headshot URLs.
Matches recruits by normalized name + hs_grad_year, writes headshot_url
to basketball_players where currently NULL.

Usage:
  python scrape_bball_247_headshots.py --dry-run
  python scrape_bball_247_headshots.py
  python scrape_bball_247_headshots.py --year 2027
"""

import logging
import re
import sys
import time
import unicodedata

import requests
from bs4 import BeautifulSoup
from supabase_client import supabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

YEARS = [2026, 2027, 2028]
MAX_PAGES = 10  # ~50 recruits per page → up to 500 per class


def normalize(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower().strip()
    name = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", name)
    name = re.sub(r"[^a-z\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def scrape_page(url: str) -> list[dict]:
    """Scrape one page of 247 basketball composite rankings."""
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    recruits = []
    items = soup.select(".rankings-page__list-item")
    for item in items:
        try:
            name_el = item.select_one(
                ".recruit .rankings-page__name-link"
            ) or item.select_one("a.rankings-page__name-link")
            if not name_el:
                continue
            name = name_el.get_text(strip=True)

            img_el = item.select_one(
                ".recruit-image img, .circle-image-block img, img"
            )
            headshot = None
            if img_el:
                headshot = img_el.get("data-src") or img_el.get("src")
                if headshot and (
                    "default" in headshot.lower()
                    or "placeholder" in headshot.lower()
                ):
                    headshot = None

            if name and headshot:
                recruits.append({
                    "name": name,
                    "normalized": normalize(name),
                    "headshot_url": headshot,
                })
        except Exception as e:
            log.warning(f"Error parsing item: {e}")
            continue

    return recruits


def main():
    dry_run = "--dry-run" in sys.argv

    # Parse --year flag (default: all years)
    target_years = YEARS
    for i, arg in enumerate(sys.argv):
        if arg == "--year" and i + 1 < len(sys.argv):
            target_years = [int(sys.argv[i + 1])]

    # ── Scrape 247Sports ──────────────────────────────────────────────
    all_scraped: dict[int, list[dict]] = {}
    for year in target_years:
        year_recruits: list[dict] = []
        for page_num in range(1, MAX_PAGES + 1):
            url = (
                f"https://247sports.com/Season/{year}-Basketball/"
                f"CompositeRecruitRankings/?InstitutionGroup=HighSchool"
                f"&Page={page_num}"
            )
            log.info(f"  [{year}] page {page_num}: {url}")
            try:
                page_recruits = scrape_page(url)
                if not page_recruits:
                    log.info(f"  [{year}] page {page_num} empty — stopping.")
                    break
                year_recruits.extend(page_recruits)
                log.info(
                    f"  [{year}] got {len(page_recruits)} "
                    f"(total: {len(year_recruits)})"
                )
                time.sleep(2.0)
            except Exception as e:
                log.warning(f"  [{year}] error on page {page_num}: {e}")
                break

        all_scraped[year] = year_recruits
        log.info(f"  [{year}] scraped {len(year_recruits)} recruits total")

    total_scraped = sum(len(v) for v in all_scraped.values())
    log.info(f"Scraped {total_scraped} recruits across {len(target_years)} class(es)")

    if total_scraped == 0:
        log.info("Nothing scraped. Exiting.")
        return

    # ── Load DB recruits ──────────────────────────────────────────────
    log.info("Fetching basketball recruits from DB...")
    all_players: list[dict] = []
    offset = 0
    page_size = 1000
    while True:
        resp = (
            supabase.table("basketball_players")
            .select("id, name, headshot_url, hs_grad_year, star_rating")
            .eq("player_tag", "High School Recruit")
            .gte("star_rating", 4)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    log.info(f"Found {len(all_players)} basketball recruits (4-star+) in DB")

    # Build lookup: (normalized_name, grad_year) → player
    name_year_lookup: dict[tuple[str, int], dict] = {}
    # Also a name-only lookup for fallback
    name_only_lookup: dict[str, dict] = {}
    for p in all_players:
        norm = normalize(p["name"])
        yr = p.get("hs_grad_year")
        if yr:
            name_year_lookup[(norm, yr)] = p
        name_only_lookup[norm] = p

    # ── Match and update ──────────────────────────────────────────────
    matched = 0
    skipped_has_headshot = 0
    skipped_no_match = 0

    for year, recruits in all_scraped.items():
        for recruit in recruits:
            # Try year-scoped match first, then name-only fallback
            db_player = name_year_lookup.get(
                (recruit["normalized"], year)
            ) or name_only_lookup.get(recruit["normalized"])

            if not db_player:
                skipped_no_match += 1
                continue

            if db_player.get("headshot_url"):
                skipped_has_headshot += 1
                continue

            if dry_run:
                log.info(
                    f"  [DRY RUN] {db_player['name']:30s} -> "
                    f"{recruit['headshot_url'][:70]}..."
                )
            else:
                supabase.table("basketball_players").update({
                    "headshot_url": recruit["headshot_url"]
                }).eq("id", db_player["id"]).execute()

            matched += 1

    log.info(
        f"Done. Matched: {matched}, "
        f"Already had headshot: {skipped_has_headshot}, "
        f"No DB match: {skipped_no_match}"
    )
    if dry_run:
        log.info("(Dry run — no changes written)")


if __name__ == "__main__":
    main()
