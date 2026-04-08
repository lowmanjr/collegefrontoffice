"""
Scrape On3 NIL rankings per team to populate social follower counts.
Uses On3's team-key parameter to fetch up to 100 players per team.

Usage: python scrape_on3_team_socials.py [--dry-run]
"""

import logging
import sys
import re
import time
import json
import unicodedata
import requests
from bs4 import BeautifulSoup
from supabase_client import supabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# On3 orgKey for all 68 Power 4 teams (extracted from On3 filter data April 2026)
ON3_TEAM_KEYS = {
    # SEC
    "Alabama": 1867, "Arkansas": 3248, "Auburn": 1894, "Florida": 19488,
    "Georgia": 17954, "Kentucky": 12013, "LSU": 14458, "Mississippi State": 16253,
    "Missouri": 17525, "Oklahoma": 10166, "Ole Miss": 9150,
    "South Carolina": 16266, "Tennessee": 24635, "Texas": 23628,
    "Texas A&M": 23590, "Vanderbilt": 21058,
    # Big Ten
    "Illinois": 7862, "Indiana": 8776, "Iowa": 8296, "Maryland": 14710,
    "Michigan": 15421, "Michigan State": 15453, "Minnesota": 15505,
    "Nebraska": 16674, "Northwestern": 9661, "Ohio State": 9533,
    "Oregon": 10273, "Penn State": 7226, "Purdue": 8786, "Rutgers": 8024,
    "UCLA": 24078, "USC": 20559, "Washington": 20319, "Wisconsin": 5667,
    # Big 12
    "Arizona": 3376, "Arizona State": 3357, "Baylor": 2122, "BYU": 21364,
    "Cincinnati": 23814, "Colorado": 24749, "Houston": 7493,
    "Iowa State": 8288, "Kansas": 7567, "Kansas State": 7576,
    "Oklahoma State": 10179, "TCU": 23534, "Texas Tech": 23643,
    "UCF": 24860, "Utah": 21359, "West Virginia": 6900,
    # ACC
    "Boston College": 20485, "Cal": 20676, "Clemson": 23426,
    "Duke": 13002, "Florida State": 19484, "Georgia Tech": 17948,
    "Louisville": 12005, "Miami": 15977, "NC State": 16527,
    "North Carolina": 9486, "Pittsburgh": 7145, "SMU": 16357,
    "Stanford": 15221, "Syracuse": 15347, "Virginia": 20418,
    "Virginia Tech": 20439, "Wake Forest": 20147,
    # Independent
    "Notre Dame": 10511,
}


def normalize(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower().strip()
    name = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", name)
    name = re.sub(r"[^a-z\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def scrape_team(team_name: str, org_key: int) -> list[dict]:
    """Scrape On3 NIL rankings for a specific team."""
    url = f"https://www.on3.com/nil/rankings/player/college/football/?team-key={org_key}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        log.warning(f"  Failed to fetch {team_name}: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    script = soup.find("script", {"id": "__NEXT_DATA__"})
    if not script or not script.string:
        log.warning(f"  No __NEXT_DATA__ for {team_name}")
        return []

    try:
        data = json.loads(script.string)
        items = data["props"]["pageProps"]["nilRankings"]["list"]
    except (KeyError, json.JSONDecodeError) as e:
        log.warning(f"  Failed to parse data for {team_name}: {e}")
        return []

    players = []
    for item in items:
        person = item.get("person", {})
        val = item.get("valuation", {})
        name = (person.get("name") or "").strip()
        total_followers = int(val.get("followers") or 0)

        ig = 0
        x = 0
        tiktok = 0
        for sv in val.get("socialValuations", []):
            st = (sv.get("socialType") or "").lower()
            followers = int(sv.get("followers") or 0)
            if st == "instagram":
                ig = followers
            elif st == "twitter":
                x = followers
            elif st == "tiktok":
                tiktok = followers

        if name and total_followers > 0:
            players.append({
                "name": name,
                "normalized": normalize(name),
                "total_followers": total_followers,
                "ig_followers": ig,
                "x_followers": x,
                "tiktok_followers": tiktok,
            })

    return players


def main():
    dry_run = "--dry-run" in sys.argv

    # Fetch all teams from DB
    teams_resp = supabase.table("teams").select("id, university_name").execute()
    db_teams = {t["university_name"]: t["id"] for t in (teams_resp.data or [])}

    # Fetch all College Athlete players (paginated)
    log.info("Fetching all players from DB...")
    all_players = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, team_id, total_followers")
            .eq("player_tag", "College Athlete")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    log.info(f"Found {len(all_players)} College Athletes in DB")

    # Group by team_id
    players_by_team: dict[str, list[dict]] = {}
    for p in all_players:
        tid = p.get("team_id")
        if tid:
            players_by_team.setdefault(tid, []).append(p)

    total_updated = 0
    total_skipped = 0
    total_no_match = 0
    teams_processed = 0

    for team_name, org_key in ON3_TEAM_KEYS.items():
        team_id = db_teams.get(team_name)
        if not team_id:
            continue

        team_players = players_by_team.get(team_id, [])
        if not team_players:
            continue

        # Build name lookup
        name_lookup: dict[str, dict] = {}
        for p in team_players:
            norm = normalize(p["name"])
            name_lookup[norm] = p

        # Scrape On3
        on3_players = scrape_team(team_name, org_key)
        if not on3_players:
            log.info(f"  {team_name}: no data from On3")
            time.sleep(1.5)
            continue

        team_updated = 0
        for op in on3_players:
            db_player = name_lookup.get(op["normalized"])
            if not db_player:
                total_no_match += 1
                continue

            # Skip if already has equal or higher social data
            existing = db_player.get("total_followers") or 0
            if existing >= op["total_followers"]:
                total_skipped += 1
                continue

            if not dry_run:
                supabase.table("players").update({
                    "total_followers": op["total_followers"],
                    "ig_followers": op["ig_followers"] or None,
                    "x_followers": op["x_followers"] or None,
                    "tiktok_followers": op["tiktok_followers"] or None,
                }).eq("id", db_player["id"]).execute()

            team_updated += 1
            total_updated += 1

        teams_processed += 1
        log.info(f"  {team_name}: scraped {len(on3_players)}, updated {team_updated}")
        time.sleep(1.5)

    log.info(f"Done. Teams: {teams_processed}, Updated: {total_updated}, Skipped: {total_skipped}, No match: {total_no_match}")
    if dry_run:
        log.info("(Dry run -- no changes written)")


if __name__ == "__main__":
    main()
