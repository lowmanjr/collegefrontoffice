"""
Backfill team_id for HS recruits using CFBD's committedTo field.
Matches recruit commitment school names to our teams table.

Usage: python backfill_recruit_commitments.py [--dry-run] [--year 2026]
"""

import logging
import sys
import os
import unicodedata
import re
import requests
from supabase_client import supabase
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env.local'))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

CFBD_API_KEY = os.getenv("CFBD_API_KEY")
CFBD_HEADERS = {"Authorization": f"Bearer {CFBD_API_KEY}"}


def normalize(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower().strip()
    name = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", name)
    name = re.sub(r"[^a-z\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


# Common name variations between CFBD school names and our university_name
SCHOOL_ALIASES = {
    "ole miss": "Ole Miss",
    "miami (fl)": "Miami",
    "miami": "Miami",
    "usc": "USC",
    "ucf": "UCF",
    "lsu": "LSU",
    "byu": "BYU",
    "smu": "SMU",
    "nc state": "NC State",
    "north carolina state": "NC State",
    "pitt": "Pittsburgh",
    "cal": "Cal",
    "california": "Cal",
}


def main():
    dry_run = "--dry-run" in sys.argv

    year = 2026
    for i, arg in enumerate(sys.argv):
        if arg == "--year" and i + 1 < len(sys.argv):
            year = int(sys.argv[i + 1])

    if not CFBD_API_KEY:
        log.error("CFBD_API_KEY not found in environment")
        sys.exit(1)

    # Fetch our teams
    teams_resp = supabase.table("teams").select("id, university_name").execute()
    teams = {t["university_name"]: t["id"] for t in (teams_resp.data or [])}
    # Build lowercase lookup
    teams_lower = {name.lower(): tid for name, tid in teams.items()}
    log.info(f"Loaded {len(teams)} teams from DB")

    # Fetch uncommitted HS recruits for this year
    log.info(f"Fetching uncommitted {year} recruits from DB...")
    all_uncommitted = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, hs_grad_year")
            .eq("player_tag", "High School Recruit")
            .eq("hs_grad_year", year)
            .is_("team_id", "null")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        all_uncommitted.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    log.info(f"Found {len(all_uncommitted)} uncommitted {year} recruits in DB")

    if not all_uncommitted:
        log.info("Nothing to backfill.")
        return

    # Build name lookup
    name_lookup = {}
    for p in all_uncommitted:
        norm = normalize(p["name"])
        name_lookup[norm] = p

    # Fetch CFBD recruit data
    log.info(f"Fetching {year} recruits from CFBD...")
    r = requests.get(
        f"https://api.collegefootballdata.com/recruiting/players?year={year}&classification=HighSchool",
        headers=CFBD_HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    cfbd_recruits = r.json()
    log.info(f"CFBD returned {len(cfbd_recruits)} recruits")

    def resolve_team_id(school_name: str):
        """Try to match a CFBD school name to our teams table."""
        if not school_name:
            return None
        # Direct match
        tid = teams.get(school_name)
        if tid:
            return tid
        # Lowercase match
        tid = teams_lower.get(school_name.lower())
        if tid:
            return tid
        # Alias match
        alias = SCHOOL_ALIASES.get(school_name.lower())
        if alias:
            return teams.get(alias)
        # Partial match — check if school name contains a team name
        for name, team_id in teams.items():
            if name.lower() in school_name.lower() or school_name.lower() in name.lower():
                return team_id
        return None

    matched = 0
    no_db_player = 0
    no_team = 0
    not_committed = 0

    for rec in cfbd_recruits:
        cfbd_name = rec.get("name", "")
        school = rec.get("committedTo")

        if not school:
            not_committed += 1
            continue

        norm = normalize(cfbd_name)
        db_player = name_lookup.get(norm)
        if not db_player:
            no_db_player += 1
            continue

        team_id = resolve_team_id(school)
        if not team_id:
            no_team += 1
            if no_team <= 5:
                log.info(f"  No team match for school: \"{school}\" (player: {cfbd_name})")
            continue

        if dry_run:
            if matched < 20:
                log.info(f"  [DRY RUN] {db_player['name']} -> {school}")
        else:
            supabase.table("players").update({
                "team_id": team_id
            }).eq("id", db_player["id"]).execute()

        matched += 1

    log.info(f"Done. Matched: {matched}, Not committed (CFBD): {not_committed}, No DB player: {no_db_player}, No team in DB: {no_team}")
    if dry_run:
        log.info("(Dry run -- no changes written)")


if __name__ == "__main__":
    main()
