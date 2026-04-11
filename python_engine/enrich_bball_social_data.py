"""
enrich_bball_social_data.py
----------------------------
Scrapes On3 NIL rankings per team to populate social follower counts
for basketball players. Mirrors scrape_on3_team_socials.py (football).

Source: https://www.on3.com/nil/rankings/player/college/basketball/?team-key={key}

After enriching, re-runs calculate_bball_valuations.py so social premiums
take effect immediately.

Usage:
    python enrich_bball_social_data.py              # all teams
    python enrich_bball_social_data.py --dry-run    # preview only
    python enrich_bball_social_data.py --team byu   # single team
"""

import logging
import os
import re
import subprocess
import sys
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

# On3 org keys — maps university_name → On3 organization ID.
# This is the only dict that needs updating when adding a new team.
ON3_ORG_KEYS: dict[str, int] = {
    "BYU": 21364,
    "Kentucky": 12013,
    "UConn": 24966,
    "Georgia": 17954,
    "Michigan": 15421,
}

REQUEST_DELAY = 2.0  # seconds between On3 requests

# On3 sometimes uses shortened names that don't match ESPN roster names.
# Map normalized On3 name → normalized DB name.
NAME_ALIASES: dict[str, str] = {
    "rob wright": "robert wright",
    # add others here as discovered
}


def normalize(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower().strip()
    name = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", name)
    name = re.sub(r"[^a-z\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def scrape_team_socials(team_name: str, org_key: int) -> list[dict]:
    """Scrape On3 basketball NIL rankings for a specific team."""
    url = f"https://www.on3.com/nil/rankings/player/college/basketball/?team-key={org_key}"
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

        norm = normalize(name)
        norm = NAME_ALIASES.get(norm, norm)

        players.append({
            "name": name,
            "normalized": norm,
            "total_followers": total_followers,
            "ig_followers": ig,
            "x_followers": x,
            "tiktok_followers": tiktok,
        })

    return players


def compute_social_premium(ig: int, x: int, tiktok: int) -> int:
    """Basketball-weighted social premium (for display in output only)."""
    weighted = ig + int(x * 0.7) + int(tiktok * 1.2)
    if weighted >= 1_000_000: return 150_000
    if weighted >= 500_000:   return 75_000
    if weighted >= 100_000:   return 25_000
    if weighted >= 50_000:    return 10_000
    if weighted >= 10_000:    return 3_000
    return 0


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    team_filter = None
    for i, arg in enumerate(sys.argv):
        if arg == "--team" and i + 1 < len(sys.argv):
            team_filter = sys.argv[i + 1]

    # Fetch basketball teams from DB
    teams_resp = supabase.table("basketball_teams").select("id, university_name, slug").execute()
    db_teams = {t["university_name"]: t for t in (teams_resp.data or [])}

    if team_filter:
        db_teams = {name: t for name, t in db_teams.items() if t["slug"] == team_filter}

    # Fetch all basketball players
    log.info("Fetching all basketball players from DB...")
    all_players = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            supabase.table("basketball_players")
            .select("id, name, team_id, total_followers")
            .eq("roster_status", "active")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    log.info(f"Found {len(all_players)} active basketball players")

    # Group by team_id
    players_by_team: dict[str, list[dict]] = {}
    for p in all_players:
        tid = p.get("team_id")
        if tid:
            players_by_team.setdefault(tid, []).append(p)

    total_updated = 0
    total_skipped = 0
    total_no_match = 0
    total_premium = 0

    for team_name, team_data in db_teams.items():
        org_key = ON3_ORG_KEYS.get(team_name)
        if not org_key:
            log.info(f"  {team_name}: no On3 org key, skipping")
            continue

        team_id = team_data["id"]
        team_players = players_by_team.get(team_id, [])
        if not team_players:
            continue

        # Build name lookup
        name_lookup: dict[str, dict] = {}
        for p in team_players:
            norm = normalize(p["name"])
            name_lookup[norm] = p

        log.info(f"\nEnriching social data for {team_name} basketball...")
        on3_players = scrape_team_socials(team_name, org_key)
        if not on3_players:
            log.info(f"  No data from On3")
            time.sleep(REQUEST_DELAY)
            continue

        log.info(f"  On3 returned {len(on3_players)} players")
        team_updated = 0

        for op in on3_players:
            db_player = name_lookup.get(op["normalized"])
            if not db_player:
                total_no_match += 1
                continue

            # Skip if already has equal or higher social data
            existing = db_player.get("total_followers") or 0
            if existing >= op["total_followers"] and op["total_followers"] == 0:
                total_skipped += 1
                continue

            premium = compute_social_premium(op["ig_followers"], op["x_followers"], op["tiktok_followers"])

            log.info(
                f"  {op['name']:28s} | IG: {op['ig_followers']:>8,} | "
                f"X: {op['x_followers']:>6,} | TikTok: {op['tiktok_followers']:>8,} "
                f"-> +${premium:,} premium"
            )

            if not dry_run:
                supabase.table("basketball_players").update({
                    "total_followers": op["total_followers"],
                    "ig_followers": op["ig_followers"] or None,
                    "x_followers": op["x_followers"] or None,
                    "tiktok_followers": op["tiktok_followers"] or None,
                }).eq("id", db_player["id"]).execute()

            team_updated += 1
            total_updated += 1
            total_premium += premium

        log.info(f"  {team_name}: {team_updated} players updated")
        time.sleep(REQUEST_DELAY)

    log.info(f"\nSummary: {total_updated} updated, {total_skipped} skipped, {total_no_match} no match in DB")
    log.info(f"Total social premium across all teams: +${total_premium:,}")

    if dry_run:
        log.info("(Dry run -- no changes written)")
    elif total_updated > 0:
        log.info("\nRecalculating valuations...")
        script_dir = os.path.dirname(__file__)
        subprocess.run(
            [sys.executable, os.path.join(script_dir, "calculate_bball_valuations.py")],
            cwd=script_dir,
        )


if __name__ == "__main__":
    main()
