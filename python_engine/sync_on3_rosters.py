"""
Sync rosters using On3's team NIL ranking pages.
Detects transfers (players at wrong team) and creates new player records.

Usage: python sync_on3_rosters.py [--dry-run] [--team Texas]
"""

import logging
import sys
import re
import time
import json
import unicodedata
import difflib
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from supabase_client import supabase
from scrape_on3_team_socials import ON3_TEAM_KEYS

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


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-")


def scrape_on3_team(team_name: str, org_key: int) -> list[dict]:
    """Scrape On3 NIL rankings for a team, return list of player dicts."""
    url = f"https://www.on3.com/nil/rankings/player/college/football/?team-key={org_key}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        script = soup.find("script", {"id": "__NEXT_DATA__"})
        if not script:
            return []
        data = json.loads(script.string)
        items = data["props"]["pageProps"]["nilRankings"]["list"]
    except Exception as e:
        log.warning(f"  Failed to scrape {team_name}: {e}")
        return []

    players = []
    for item in items:
        person = item.get("person", {})
        name = person.get("name", "")
        position = person.get("positionAbbreviation") or item.get("positionAbbreviation", "")
        if name:
            players.append({
                "name": name,
                "normalized": normalize(name),
                "position": position,
            })
    return players


def main():
    dry_run = "--dry-run" in sys.argv

    # Parse --team filter
    target_team = None
    for i, arg in enumerate(sys.argv):
        if arg == "--team" and i + 1 < len(sys.argv):
            target_team = sys.argv[i + 1]

    # Fetch all teams
    teams_resp = supabase.table("teams").select("id, university_name").execute()
    teams = {t["university_name"]: t["id"] for t in (teams_resp.data or [])}
    team_id_to_name = {t["id"]: t["university_name"] for t in (teams_resp.data or [])}

    # Fetch ALL college athletes from DB (paginated)
    log.info("Fetching all college athletes from DB...")
    all_db_players = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, team_id, player_tag, is_override, roster_status, cfo_valuation, espn_athlete_id, headshot_url")
            .eq("player_tag", "College Athlete")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        all_db_players.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    log.info(f"Found {len(all_db_players)} college athletes in DB")

    # Build global name lookup: normalized name -> list of records
    global_name_lookup: dict[str, list[dict]] = defaultdict(list)
    for p in all_db_players:
        norm = normalize(p["name"])
        global_name_lookup[norm].append(p)

    # Track all existing normalized names for slug dedup
    existing_slugs = {normalize(p["name"]) for p in all_db_players}

    total_transferred = 0
    total_created = 0
    total_already_correct = 0

    teams_to_process = list(ON3_TEAM_KEYS.items())
    if target_team:
        teams_to_process = [(k, v) for k, v in ON3_TEAM_KEYS.items() if k.lower() == target_team.lower()]
        if not teams_to_process:
            log.error(f"Team '{target_team}' not found in ON3_TEAM_KEYS")
            sys.exit(1)

    for team_name, org_key in teams_to_process:
        team_id = teams.get(team_name)
        if not team_id:
            continue

        # Get On3 roster for this team
        on3_players = scrape_on3_team(team_name, org_key)
        if not on3_players:
            continue

        # Get our current roster for this team
        our_roster = {normalize(p["name"]): p for p in all_db_players if p.get("team_id") == team_id}

        team_transferred = 0
        team_created = 0

        for op in on3_players:
            # Already on our roster for this team?
            if op["normalized"] in our_roster:
                total_already_correct += 1
                continue

            # Check if player exists at a DIFFERENT team (transfer)
            candidates = global_name_lookup.get(op["normalized"], [])

            # Also try fuzzy match against global DB
            if not candidates:
                all_norms = list(global_name_lookup.keys())
                fuzzy = difflib.get_close_matches(op["normalized"], all_norms, n=1, cutoff=0.88)
                if fuzzy:
                    candidates = global_name_lookup[fuzzy[0]]

            transferred = False
            for candidate in candidates:
                if candidate.get("team_id") == team_id:
                    total_already_correct += 1
                    transferred = True
                    break

                if candidate.get("is_override"):
                    continue

                old_team = team_id_to_name.get(candidate.get("team_id"), "UNKNOWN")

                if dry_run:
                    if total_transferred < 50:
                        log.info(f"  [TRANSFER] {op['name']}: {old_team} -> {team_name}")
                else:
                    updates = {
                        "team_id": team_id,
                        "roster_status": "active",
                        "is_on_depth_chart": None,
                        "depth_chart_rank": None,
                        "cfo_valuation": None,
                    }
                    supabase.table("players").update(updates).eq("id", candidate["id"]).execute()
                    candidate["team_id"] = team_id

                total_transferred += 1
                team_transferred += 1
                transferred = True
                break

            if not transferred and not any(c.get("team_id") == team_id for c in candidates):
                slug = slugify(op["name"])
                team_slug = slugify(team_name)
                final_slug = f"{slug}-{team_slug}" if op["normalized"] in existing_slugs else slug

                if dry_run:
                    if total_created < 50:
                        log.info(f"  [NEW] {op['name']} ({op['position']}) -> {team_name}")
                else:
                    try:
                        supabase.table("players").insert({
                            "name": op["name"],
                            "position": op["position"] if op["position"] else None,
                            "team_id": team_id,
                            "player_tag": "College Athlete",
                            "roster_status": "active",
                            "is_public": True,
                            "is_override": False,
                            "slug": final_slug,
                        }).execute()
                    except Exception as e:
                        log.warning(f"  Failed to create {op['name']}: {e}")
                        continue

                existing_slugs.add(op["normalized"])
                total_created += 1
                team_created += 1

        if team_transferred or team_created:
            log.info(f"  {team_name}: {team_transferred} transfers, {team_created} new players")

        time.sleep(1.5)

    log.info(f"Done.")
    log.info(f"  Transfers moved: {total_transferred}")
    log.info(f"  New players created: {total_created}")
    log.info(f"  Already correct: {total_already_correct}")
    if dry_run:
        log.info("(Dry run -- no changes written)")


if __name__ == "__main__":
    main()
