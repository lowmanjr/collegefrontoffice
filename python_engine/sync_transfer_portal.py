"""
Scrape On3 transfer portal (committed players) to update roster assignments.
Runs AFTER sync_espn_rosters_by_id.py to catch transfers ESPN hasn't processed yet.

For each committed transfer:
- Finds the player in our DB (by name at their old team, or by name globally)
- Moves them to their new team
- Updates roster_status to active

Usage: python sync_transfer_portal.py [--dry-run] [--max-pages 20]
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
from collections import defaultdict
from name_utils import normalize_name, normalize_name_stripped

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def normalize(name: str) -> str:
    """Delegates to shared name_utils. Strips suffixes like the old version did."""
    return normalize_name_stripped(name)


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-")


def scrape_portal_page(page_num: int) -> list[dict]:
    """Scrape one page of On3 committed transfers."""
    url = f"https://www.on3.com/transfer-portal/wire/football/?status=committed&page={page_num}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        script = soup.find("script", {"id": "__NEXT_DATA__"})
        if not script:
            return []
        data = json.loads(script.string)
        items = data["props"]["pageProps"]["playerData"]["list"]
    except Exception as e:
        log.warning(f"  Failed to scrape page {page_num}: {e}")
        return []

    transfers = []
    for item in items:
        name = item.get("name", "")
        position = item.get("positionAbbreviation", "")

        last_team = item.get("lastTeam", {})
        origin = last_team.get("fullName", "") if last_team else ""

        commit_status = item.get("commitStatus", {})
        committed_org = commit_status.get("committedOrganization", {}) if commit_status else {}
        destination = committed_org.get("fullName", "") if committed_org else ""

        if name and origin and destination:
            transfers.append({
                "name": name,
                "normalized": normalize(name),
                "position": position,
                "origin": origin,
                "destination": destination,
            })

    return transfers


def main():
    dry_run = "--dry-run" in sys.argv

    max_pages = 110  # default: all pages
    for i, arg in enumerate(sys.argv):
        if arg == "--max-pages" and i + 1 < len(sys.argv):
            max_pages = int(sys.argv[i + 1])

    # Fetch our teams
    teams_resp = supabase.table("teams").select("id, university_name").execute()
    teams = {t["university_name"]: t["id"] for t in (teams_resp.data or [])}
    team_id_to_name = {t["id"]: t["university_name"] for t in (teams_resp.data or [])}
    log.info(f"Loaded {len(teams)} teams")

    teams_lower = {name.lower(): tid for name, tid in teams.items()}

    SCHOOL_ALIASES = {
        "ole miss rebels": "Ole Miss",
        "miami hurricanes": "Miami",
        "usc trojans": "USC",
        "ucf knights": "UCF",
        "lsu tigers": "LSU",
        "byu cougars": "BYU",
        "smu mustangs": "SMU",
        "nc state wolfpack": "NC State",
        "pittsburgh panthers": "Pittsburgh",
        "california golden bears": "Cal",
    }

    def resolve_team_id(school_full_name: str):
        if not school_full_name:
            return None
        tid = teams.get(school_full_name)
        if tid:
            return tid
        tid = teams_lower.get(school_full_name.lower())
        if tid:
            return tid
        alias = SCHOOL_ALIASES.get(school_full_name.lower())
        if alias:
            return teams.get(alias)
        for our_name, our_id in teams.items():
            if our_name.lower() in school_full_name.lower():
                return our_id
        return None

    # Fetch all college athletes from DB (paginated)
    log.info("Fetching all college athletes from DB...")
    all_db_players = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, team_id, is_override, roster_status, espn_athlete_id")
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

    # Build lookups: both normalized and suffix-stripped for broader matching
    name_team_lookup: dict[tuple, dict] = {}
    name_global_lookup: dict[str, list[dict]] = defaultdict(list)
    # Additional stripped lookups for suffix mismatches (Jr/III etc.)
    name_team_stripped: dict[tuple, dict] = {}
    name_global_stripped: dict[str, list[dict]] = defaultdict(list)
    for p in all_db_players:
        norm = normalize(p["name"])
        stripped = normalize_name_stripped(p["name"])
        key = (norm, p.get("team_id"))
        name_team_lookup[key] = p
        name_global_lookup[norm].append(p)
        skey = (stripped, p.get("team_id"))
        if skey not in name_team_stripped:
            name_team_stripped[skey] = p
        name_global_stripped[stripped].append(p)

    # Scrape On3 portal
    log.info(f"Scraping On3 transfer portal (committed, up to {max_pages} pages)...")
    all_transfers = []
    for page_num in range(1, max_pages + 1):
        page_transfers = scrape_portal_page(page_num)
        if not page_transfers:
            log.info(f"  Page {page_num}: 0 results, stopping.")
            break
        all_transfers.extend(page_transfers)
        if page_num % 10 == 0:
            log.info(f"  Scraped {page_num} pages ({len(all_transfers)} transfers so far)")
        time.sleep(1.0)

    log.info(f"Scraped {len(all_transfers)} committed transfers from On3")

    moved = 0
    created = 0
    skipped_not_our_team = 0
    skipped_already_correct = 0
    skipped_override = 0

    for transfer in all_transfers:
        dest_team_id = resolve_team_id(transfer["destination"])
        if not dest_team_id:
            skipped_not_our_team += 1
            continue

        origin_team_id = resolve_team_id(transfer["origin"])
        norm = transfer["normalized"]

        db_player = None
        norm_stripped = normalize_name_stripped(transfer.get("name", ""))

        # Level 1: Team-scoped exact match (then stripped fallback)
        if origin_team_id:
            db_player = name_team_lookup.get((norm, origin_team_id))
            if not db_player:
                db_player = name_team_stripped.get((norm_stripped, origin_team_id))

        # Level 2: Global fallback (then stripped fallback)
        if not db_player:
            candidates = name_global_lookup.get(norm, [])
            if not candidates:
                candidates = name_global_stripped.get(norm_stripped, [])
            for c in candidates:
                if c.get("team_id") != dest_team_id:
                    db_player = c
                    break

        if db_player:
            if db_player.get("is_override"):
                skipped_override += 1
                continue

            if db_player.get("team_id") == dest_team_id:
                skipped_already_correct += 1
                continue

            old_team = team_id_to_name.get(db_player.get("team_id"), "UNKNOWN")
            new_team = team_id_to_name.get(dest_team_id, transfer["destination"])

            if dry_run:
                if moved < 50:
                    log.info(f"  [MOVE] {transfer['name']}: {old_team} -> {new_team}")
            else:
                supabase.table("players").update({
                    "team_id": dest_team_id,
                    "roster_status": "active",
                }).eq("id", db_player["id"]).execute()

            moved += 1
        else:
            dest_name = team_id_to_name.get(dest_team_id, transfer["destination"])
            slug = slugify(transfer["name"])
            team_slug = slugify(dest_name)

            if dry_run:
                if created < 30:
                    log.info(f"  [NEW] {transfer['name']} ({transfer['position']}): {transfer['origin']} -> {dest_name}")
            else:
                try:
                    supabase.table("players").insert({
                        "name": transfer["name"],
                        "position": transfer["position"] if transfer["position"] else None,
                        "team_id": dest_team_id,
                        "player_tag": "College Athlete",
                        "roster_status": "active",
                        "is_public": True,
                        "is_override": False,
                        "slug": slug,
                    }).execute()
                except Exception:
                    try:
                        supabase.table("players").insert({
                            "name": transfer["name"],
                            "position": transfer["position"] if transfer["position"] else None,
                            "team_id": dest_team_id,
                            "player_tag": "College Athlete",
                            "roster_status": "active",
                            "is_public": True,
                            "is_override": False,
                            "slug": f"{slug}-{team_slug}",
                        }).execute()
                    except Exception as e:
                        log.warning(f"  Failed to create {transfer['name']}: {e}")
                        continue

            created += 1

    log.info(f"Done.")
    log.info(f"  Moved to new team: {moved}")
    log.info(f"  Created (new to DB): {created}")
    log.info(f"  Already correct: {skipped_already_correct}")
    log.info(f"  Override (skipped): {skipped_override}")
    log.info(f"  Destination not in our teams: {skipped_not_our_team}")
    if dry_run:
        log.info("(Dry run -- no changes written)")


if __name__ == "__main__":
    main()
