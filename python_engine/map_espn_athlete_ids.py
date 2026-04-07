"""
Map ESPN athlete IDs to players by name + team matching.
Uses the same ESPN roster API as ingest_espn_rosters.py.

Usage: python map_espn_athlete_ids.py [--dry-run]
"""

import logging
import sys
import unicodedata
import re
from supabase_client import supabase
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Same team map as ingest_espn_rosters.py — maps team_id (UUID) to ESPN team ID
# Copy the ESPN_TEAM_MAP from ingest_espn_rosters.py here, or import it.
# For now, read it from ingest_espn_rosters to avoid duplication:
try:
    from ingest_espn_rosters import ESPN_TEAM_MAP
except ImportError:
    log.error("Could not import ESPN_TEAM_MAP from ingest_espn_rosters.py")
    sys.exit(1)


def normalize(name: str) -> str:
    """Normalize a name for matching: lowercase, strip accents, remove suffixes."""
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower().strip()
    name = re.sub(r"\s+(jr|sr|ii|iii|iv|v)\.?$", "", name)
    name = re.sub(r"[^a-z\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


ESPN_HEADSHOT_TEMPLATE = "https://a.espncdn.com/combiner/i?img=/i/headshots/college-football/players/full/{espn_id}.png&w=200&h=146"


def main():
    dry_run = "--dry-run" in sys.argv

    # Fetch teams to map university_name -> team UUID
    log.info("Fetching teams from Supabase...")
    teams_resp = supabase.table("teams").select("id, university_name").execute()
    teams = teams_resp.data or []
    # Build lowercase name -> UUID lookup
    name_to_uuid = {t["university_name"].lower(): t["id"] for t in teams}
    log.info(f"Found {len(teams)} teams")

    # Fetch all players grouped by team
    log.info("Fetching players from Supabase...")
    resp = supabase.table("players").select("id, name, team_id, espn_athlete_id").execute()
    all_players = resp.data or []
    log.info(f"Found {len(all_players)} total players")

    # Group players by team_id (UUID)
    players_by_team = {}
    for p in all_players:
        tid = p.get("team_id")
        if tid:
            players_by_team.setdefault(tid, []).append(p)

    total_mapped = 0
    total_skipped = 0
    total_errors = 0

    # ESPN_TEAM_MAP keys are lowercase team names; resolve to UUIDs
    for team_name_lower, espn_team_id in ESPN_TEAM_MAP.items():
        team_id = name_to_uuid.get(team_name_lower)
        if not team_id:
            log.warning(f"No UUID found for team '{team_name_lower}', skipping")
            continue
        team_players = players_by_team.get(team_id, [])
        if not team_players:
            continue

        # Build lookup of normalized name -> player
        name_lookup = {}
        for p in team_players:
            norm = normalize(p["name"])
            name_lookup[norm] = p

        # Fetch ESPN roster
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/{espn_team_id}/roster"
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            log.warning(f"Failed to fetch ESPN roster for team {espn_team_id}: {e}")
            total_errors += 1
            continue

        # Parse athletes from all position groups
        athletes = []
        for group in data.get("athletes", []):
            for item in group.get("items", []):
                athletes.append(item)

        log.info(f"Team {espn_team_id}: {len(athletes)} ESPN athletes, {len(team_players)} DB players")

        for athlete in athletes:
            espn_id = int(athlete.get("id", 0))
            espn_name = athlete.get("displayName") or athlete.get("fullName") or ""
            if not espn_id or not espn_name:
                continue

            norm_espn = normalize(espn_name)
            match = name_lookup.get(norm_espn)

            if match:
                if match.get("espn_athlete_id") == espn_id:
                    total_skipped += 1
                    continue

                headshot_url = ESPN_HEADSHOT_TEMPLATE.format(espn_id=espn_id)

                if dry_run:
                    log.info(f"  [DRY RUN] {match['name']} -> ESPN {espn_id}")
                else:
                    supabase.table("players").update({
                        "espn_athlete_id": espn_id,
                        "headshot_url": headshot_url,
                    }).eq("id", match["id"]).execute()

                total_mapped += 1

    log.info(f"Done. Mapped: {total_mapped}, Skipped (already mapped): {total_skipped}, Errors: {total_errors}")
    if dry_run:
        log.info("(Dry run — no changes written)")


if __name__ == "__main__":
    main()
