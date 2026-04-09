"""
Scrape 247Sports composite rankings for current commitment data.
Cross-references against our DB and fixes mismatches.

Usage: python scrape_247_commitments.py [--dry-run] [--year 2026]
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

# 247 school names -> our university_name
SCHOOL_ALIASES = {
    "ole miss": "Ole Miss",
    "miami": "Miami",
    "usc": "USC",
    "ucf": "UCF",
    "lsu": "LSU",
    "byu": "BYU",
    "smu": "SMU",
    "nc state": "NC State",
    "pitt": "Pittsburgh",
    "cal": "Cal",
    "california": "Cal",
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
            name_el = item.select_one("a.rankings-page__name-link")
            if not name_el:
                continue
            name = name_el.get_text(strip=True)

            # Get commitment from non-player img alt text
            committed_to = None
            imgs = item.select("img")
            for img in imgs:
                alt = img.get("alt", "")
                if alt and alt != name and not alt.startswith("http"):
                    committed_to = alt
                    break

            recruits.append({
                "name": name,
                "normalized": normalize(name),
                "committed_to": committed_to,
            })
        except Exception as e:
            log.warning(f"Error parsing item: {e}")
            continue

    return recruits


def main():
    dry_run = "--dry-run" in sys.argv

    year = 2026
    for i, arg in enumerate(sys.argv):
        if arg == "--year" and i + 1 < len(sys.argv):
            year = int(sys.argv[i + 1])

    # Fetch our teams
    teams_resp = supabase.table("teams").select("id, university_name").execute()
    teams = {t["university_name"]: t["id"] for t in (teams_resp.data or [])}
    teams_lower = {name.lower(): tid for name, tid in teams.items()}
    team_id_to_name = {t["id"]: t["university_name"] for t in (teams_resp.data or [])}
    log.info(f"Loaded {len(teams)} teams")

    def resolve_team_id(school_name: str):
        if not school_name:
            return None
        tid = teams.get(school_name)
        if tid:
            return tid
        tid = teams_lower.get(school_name.lower())
        if tid:
            return tid
        alias = SCHOOL_ALIASES.get(school_name.lower())
        if alias:
            return teams.get(alias)
        for name, team_id in teams.items():
            if name.lower() in school_name.lower() or school_name.lower() in name.lower():
                return team_id
        return None

    # Fetch all HS recruits for this year from DB
    log.info(f"Fetching {year} recruits from DB...")
    all_players = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, team_id, hs_grad_year")
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
    log.info(f"Found {len(all_players)} recruits in DB for {year}")

    name_lookup = {}
    for p in all_players:
        norm = normalize(p["name"])
        name_lookup[norm] = p

    # Scrape 247
    log.info(f"Scraping 247Sports {year} composite rankings...")
    all_recruits = []
    for page_num in range(1, 10):
        url = f"https://247sports.com/season/{year}-football/compositerecruitrankings/?page={page_num}"
        log.info(f"  Fetching page {page_num}")
        try:
            page_recruits = scrape_page(url)
            if not page_recruits:
                break
            all_recruits.extend(page_recruits)
            log.info(f"  Got {len(page_recruits)} recruits (total: {len(all_recruits)})")
            time.sleep(1.5)
        except Exception as e:
            log.warning(f"  Error on page {page_num}: {e}")
            break

    log.info(f"Scraped {len(all_recruits)} recruits from 247")

    updated = 0
    fixed_mismatch = 0
    newly_committed = 0
    no_match = 0
    no_team = 0
    already_correct = 0

    for recruit in all_recruits:
        db_player = name_lookup.get(recruit["normalized"])
        if not db_player:
            no_match += 1
            continue

        school_247 = recruit["committed_to"]
        if not school_247:
            continue

        new_team_id = resolve_team_id(school_247)
        if not new_team_id:
            no_team += 1
            continue

        current_team_id = db_player.get("team_id")

        if current_team_id == new_team_id:
            already_correct += 1
            continue

        current_name = team_id_to_name.get(current_team_id, "UNCOMMITTED") if current_team_id else "UNCOMMITTED"
        new_name = team_id_to_name.get(new_team_id, school_247)

        if current_team_id:
            fixed_mismatch += 1
            label = "FLIP"
        else:
            newly_committed += 1
            label = "NEW"

        if dry_run:
            if updated < 30:
                log.info(f"  [{label}] {db_player['name']}: {current_name} -> {new_name}")
        else:
            supabase.table("players").update({
                "team_id": new_team_id
            }).eq("id", db_player["id"]).execute()

        updated += 1

    log.info(f"Done. Updated: {updated} (flips: {fixed_mismatch}, new commits: {newly_committed})")
    log.info(f"  Already correct: {already_correct}, No DB match: {no_match}, No team in DB: {no_team}")
    if dry_run:
        log.info("(Dry run -- no changes written)")


if __name__ == "__main__":
    main()
