"""
enrich_star_ratings_247.py
---------------------------
Fallback star_rating enrichment using 247Sports composite rankings.
Runs AFTER enrich_star_ratings.py (which uses CFBD as primary source).

Scrapes recruiting classes 2022-2026 to cover all current college athletes
(a current senior was recruited in 2022).

For each class year:
  1. Scrapes 247Sports composite rankings pages (9 pages per year)
  2. Extracts: name, star_rating, composite_score, position
  3. Matches against unrated DB players using fuzzy_match_player (team-aware)
  4. Populates star_rating and composite_score for matched players

Usage:
    python enrich_star_ratings_247.py [--dry-run]
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import logging
import re
import time
import unicodedata
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from supabase_client import supabase
from name_utils import normalize_name, normalize_name_stripped, fuzzy_match_player

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

RECRUITING_YEARS = [2022, 2023, 2024, 2025, 2026]
PAGES_PER_YEAR = 9
PAGE_DELAY = 1.5  # seconds between requests
BASE_URL = "https://247sports.com/season/{year}-football/compositerecruitrankings/?page={page}"


def scrape_page(url: str) -> list[dict]:
    """Scrape one page of 247Sports composite rankings."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except requests.RequestException as exc:
        log.warning(f"  Request failed: {exc}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    recruits = []
    items = soup.select(".rankings-page__list-item")

    for item in items:
        try:
            # Name
            name_el = item.select_one("a.rankings-page__name-link")
            if not name_el:
                continue
            name = name_el.get_text(strip=True)
            if not name:
                continue

            # Position
            pos_el = item.select_one(".position")
            position = pos_el.get_text(strip=True) if pos_el else None

            # Star rating — count star icons or parse from rating class
            star_rating = 0
            star_els = item.select(".rankings-page__star-and-score .yellow")
            if star_els:
                star_rating = len(star_els)
            if star_rating == 0:
                # Fallback: look for star count in text/class
                rating_el = item.select_one(".star-commits-list")
                if rating_el:
                    stars_text = rating_el.get_text(strip=True)
                    if stars_text.isdigit():
                        star_rating = int(stars_text)

            # Composite score
            composite_score = None
            score_el = item.select_one(".score")
            if not score_el:
                score_el = item.select_one(".rankings-page__star-and-score .score")
            if score_el:
                score_text = score_el.get_text(strip=True)
                try:
                    composite_score = float(score_text)
                except (ValueError, TypeError):
                    pass

            # Committed school (for team matching)
            school = None
            school_el = item.select_one(".img-link img")
            if school_el:
                school = school_el.get("alt", "").strip()
            if not school:
                school_el = item.select_one(".rankings-page__school")
                if school_el:
                    school = school_el.get_text(strip=True)

            recruits.append({
                "name": name,
                "position": position,
                "star_rating": star_rating,
                "composite_score": composite_score,
                "school": school,
            })
        except Exception as e:
            log.warning(f"  Error parsing item: {e}")
            continue

    return recruits


def fetch_unrated_players() -> list[dict]:
    """Fetch all active College Athletes with star_rating = 0 or NULL."""
    all_p = []
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, position, team_id, star_rating, composite_score")
            .eq("player_tag", "College Athlete")
            .eq("roster_status", "active")
            .range(offset, offset + 999)
            .execute()
        )
        batch = resp.data or []
        all_p.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    # Filter to unrated
    return [p for p in all_p if not p.get("star_rating") or p["star_rating"] == 0]


def fetch_teams() -> dict[str, str]:
    resp = supabase.table("teams").select("id, university_name").execute()
    return {t["university_name"]: t["id"] for t in (resp.data or [])}


def main():
    dry_run = "--dry-run" in sys.argv

    log.info("=" * 70)
    log.info("  ENRICH STAR RATINGS — 247Sports Fallback")
    log.info("=" * 70)

    # Step 1: Fetch unrated players
    unrated = fetch_unrated_players()
    log.info(f"  {len(unrated):,} unrated active College Athletes")

    if not unrated:
        log.info("  No unrated players. Exiting.")
        return

    # Step 2: Fetch teams for school → team_id mapping
    teams = fetch_teams()

    # Step 3: Scrape all recruiting classes
    all_recruits: list[dict] = []
    for year in RECRUITING_YEARS:
        year_count = 0
        for page in range(1, PAGES_PER_YEAR + 1):
            url = BASE_URL.format(year=year, page=page)
            log.info(f"  Scraping {year} page {page}...")
            recruits = scrape_page(url)
            if not recruits:
                log.info(f"    No results, stopping year {year}.")
                break
            for r in recruits:
                r["class_year"] = year
            all_recruits.extend(recruits)
            year_count += len(recruits)
            time.sleep(PAGE_DELAY)
        log.info(f"  {year}: {year_count} recruits scraped")

    log.info(f"\n  Total recruits scraped: {len(all_recruits):,}")

    # Step 4: Match and update
    enriched = 0
    by_method = defaultdict(int)
    by_year = defaultdict(int)

    for recruit in all_recruits:
        star = recruit.get("star_rating") or 0
        comp = recruit.get("composite_score")
        if star < 1 and not comp:
            continue  # no useful data to enrich with

        # Try to match against unrated players
        result = fuzzy_match_player(
            recruit["name"],
            unrated,
            threshold=0.85,
        )

        if result is None:
            continue

        player = result.player
        pid = player["id"]

        # Only update if the player is actually unrated
        if player.get("star_rating") and player["star_rating"] > 0:
            continue  # already enriched by a previous match in this run

        update = {}
        if star > 0:
            update["star_rating"] = star
        if comp and comp > 0:
            # 247Sports returns composites on 0-1 scale; DB uses 0-100
            update["composite_score"] = round(comp * 100, 2) if comp < 1.0 else comp

        if not update:
            continue

        if dry_run:
            log.info(f"  [DRY RUN] {recruit['name']} -> {player['name']} "
                     f"({result.method}): star={star}, comp={comp}")
        else:
            try:
                supabase.table("players").update(update).eq("id", pid).execute()
            except Exception as exc:
                log.warning(f"  [ERROR] {player['name']}: {exc}")
                continue

        # Mark as enriched in-memory so we don't re-match
        player["star_rating"] = star
        if comp:
            player["composite_score"] = comp

        enriched += 1
        by_method[result.method] += 1
        by_year[recruit.get("class_year", "?")] += 1

    # Summary
    log.info(f"\n{'=' * 70}")
    log.info(f"  247Sports ENRICHMENT COMPLETE")
    log.info(f"{'=' * 70}")
    log.info(f"  Total unrated players:    {len(unrated):,}")
    log.info(f"  Recruits scraped:         {len(all_recruits):,}")
    log.info(f"  Players enriched:         {enriched}")
    if by_method:
        log.info(f"\n  By match method:")
        for m, c in sorted(by_method.items()):
            log.info(f"    {m:<20} {c:>6}")
    if by_year:
        log.info(f"\n  By recruiting class:")
        for y, c in sorted(by_year.items()):
            log.info(f"    {y}:  {c}")
    if dry_run:
        log.info(f"\n  DRY RUN — no changes written.")
    log.info(f"{'=' * 70}")


if __name__ == "__main__":
    main()
