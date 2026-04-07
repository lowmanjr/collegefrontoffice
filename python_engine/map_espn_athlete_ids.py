"""
Map ESPN athlete IDs to players by name + team matching.
Uses the ESPN roster API (with limit=500 for full rosters) plus
an ESPN search API fallback for players not found on the roster.

Usage: python map_espn_athlete_ids.py [--dry-run]
"""

import logging
import sys
import time
import unicodedata
import re
from supabase_client import supabase
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

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


def last_name(normalized: str) -> str:
    """Extract the last token from a normalized name."""
    parts = normalized.split()
    return parts[-1] if parts else ""


ESPN_HEADSHOT_TEMPLATE = "https://a.espncdn.com/combiner/i?img=/i/headshots/college-football/players/full/{espn_id}.png&w=200&h=146"

# ESPN roster API supports limit param; default is 100, which truncates large rosters
ESPN_ROSTER_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/{espn_id}/roster?limit=500"

# ESPN search API — used as a fallback for players not found on roster
ESPN_SEARCH_URL = "https://site.api.espn.com/apis/common/v3/search?query={query}&limit=5&type=player"

SEARCH_DELAY = 0.3  # seconds between search API calls to avoid rate limiting


def fetch_espn_roster(espn_team_id: int) -> list[dict]:
    """Fetch the full ESPN roster for a team. Returns list of athlete dicts."""
    url = ESPN_ROSTER_URL.format(espn_id=espn_team_id)
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning(f"Failed to fetch ESPN roster for team {espn_team_id}: {e}")
        return []

    athletes = []
    for group in data.get("athletes", []):
        for item in group.get("items", []):
            athletes.append(item)
    return athletes


def search_espn_player(name: str, team_name_lower: str) -> dict | None:
    """
    Search ESPN for a player by name. Returns the best match dict
    (with 'id' and 'displayName') if found on the expected team, else None.

    Uses the team's nickname (e.g. "South Carolina") for verification instead
    of numeric IDs, since the search API uses a different ID namespace than
    the roster API.
    """
    url = ESPN_SEARCH_URL.format(query=requests.utils.quote(name))
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.debug(f"ESPN search failed for '{name}': {e}")
        return None

    for item in data.get("items", []):
        if item.get("league") != "college-football":
            continue
        for tr in item.get("teamRelationships", []):
            core = tr.get("core", {})
            nickname = (core.get("nickname") or "").lower()
            if nickname == team_name_lower:
                return {
                    "id": int(item["id"]),
                    "displayName": item.get("displayName", ""),
                }
    return None


def apply_mapping(player_id: str, espn_id: int, dry_run: bool) -> None:
    """Write espn_athlete_id and headshot_url to the player row."""
    headshot_url = ESPN_HEADSHOT_TEMPLATE.format(espn_id=espn_id)
    if dry_run:
        return
    supabase.table("players").update({
        "espn_athlete_id": espn_id,
        "headshot_url": headshot_url,
    }).eq("id", player_id).execute()


def main():
    dry_run = "--dry-run" in sys.argv

    # Fetch teams
    log.info("Fetching teams from Supabase...")
    teams_resp = supabase.table("teams").select("id, university_name").execute()
    teams = teams_resp.data or []
    name_to_uuid = {t["university_name"].lower(): t["id"] for t in teams}
    uuid_to_name = {t["id"]: t["university_name"] for t in teams}
    log.info(f"Found {len(teams)} teams")

    # Fetch all players (paginated)
    log.info("Fetching players from Supabase...")
    all_players = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, team_id, espn_athlete_id, position, player_tag, roster_status")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    log.info(f"Found {len(all_players)} total players")

    # Group players by team_id
    players_by_team: dict[str, list[dict]] = {}
    for p in all_players:
        tid = p.get("team_id")
        if tid:
            players_by_team.setdefault(tid, []).append(p)

    total_exact = 0
    total_lastname = 0
    total_search = 0
    total_skipped = 0
    total_errors = 0

    # Build reverse map: team UUID -> ESPN team ID
    uuid_to_espn: dict[str, int] = {}
    for team_name_lower, espn_team_id in ESPN_TEAM_MAP.items():
        team_uuid = name_to_uuid.get(team_name_lower)
        if team_uuid:
            uuid_to_espn[team_uuid] = espn_team_id

    # ── Pass 1 & 2: Roster-based matching ──────────────────────────────────
    for team_name_lower, espn_team_id in ESPN_TEAM_MAP.items():
        team_id = name_to_uuid.get(team_name_lower)
        if not team_id:
            log.warning(f"No UUID found for team '{team_name_lower}', skipping")
            continue
        team_players = players_by_team.get(team_id, [])
        if not team_players:
            continue

        # Build lookups for DB players on this team
        exact_lookup: dict[str, dict] = {}       # normalized full name -> player
        lastname_lookup: dict[str, list[dict]] = {}  # last name -> list of players
        for p in team_players:
            norm = normalize(p["name"])
            exact_lookup[norm] = p
            ln = last_name(norm)
            if ln:
                lastname_lookup.setdefault(ln, []).append(p)

        # Fetch ESPN roster
        athletes = fetch_espn_roster(espn_team_id)
        if not athletes:
            total_errors += 1
            continue

        log.info(f"{team_name_lower.title()} (ESPN {espn_team_id}): {len(athletes)} ESPN athletes, {len(team_players)} DB players")

        # Pass 1: Exact normalized name match
        unmatched_athletes = []
        for athlete in athletes:
            espn_id = int(athlete.get("id", 0))
            espn_name = athlete.get("displayName") or athlete.get("fullName") or ""
            if not espn_id or not espn_name:
                continue

            norm_espn = normalize(espn_name)
            match = exact_lookup.get(norm_espn)

            if match:
                if match.get("espn_athlete_id") == espn_id:
                    total_skipped += 1
                    continue
                if match.get("espn_athlete_id"):
                    # Already mapped to a different ESPN ID — skip to avoid overwriting
                    continue
                log.info(f"  [EXACT] {match['name']} -> ESPN {espn_id}")
                apply_mapping(match["id"], espn_id, dry_run)
                total_exact += 1
            else:
                unmatched_athletes.append(athlete)

        # Pass 2: Last-name + position fallback for unmatched ESPN athletes
        for athlete in unmatched_athletes:
            espn_id = int(athlete.get("id", 0))
            espn_name = athlete.get("displayName") or ""
            espn_pos = athlete.get("position", {}).get("abbreviation", "")
            if not espn_id or not espn_name:
                continue

            norm_espn = normalize(espn_name)
            espn_ln = last_name(norm_espn)
            if not espn_ln:
                continue

            candidates = lastname_lookup.get(espn_ln, [])
            # Filter to unmapped players with matching position
            candidates = [
                c for c in candidates
                if not c.get("espn_athlete_id")
                and c.get("position", "").upper() == espn_pos.upper()
            ]

            if len(candidates) == 1:
                match = candidates[0]
                log.info(f"  [LASTNAME] {match['name']} -> ESPN {espn_id} (ESPN name: \"{espn_name}\", pos: {espn_pos})")
                apply_mapping(match["id"], espn_id, dry_run)
                total_lastname += 1

    # ── Pass 3: ESPN search API for remaining unmatched ────────────────────
    # Re-query to see who's still missing after passes 1 & 2
    log.info("Pass 3: ESPN search API fallback for remaining unmatched players...")
    still_missing = []
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, team_id, espn_athlete_id, position, player_tag, roster_status")
            .is_("espn_athlete_id", "null")
            .eq("player_tag", "College Athlete")
            .eq("roster_status", "active")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        still_missing.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    log.info(f"  {len(still_missing)} active College Athletes still missing ESPN IDs")

    # Build reverse map: team UUID -> lowercase team name (for search API matching)
    uuid_to_team_name: dict[str, str] = {}
    for t in teams:
        uuid_to_team_name[t["id"]] = t["university_name"].lower()

    for p in still_missing:
        team_uuid = p.get("team_id")
        team_name_lower = uuid_to_team_name.get(team_uuid)
        if not team_name_lower or team_uuid not in uuid_to_espn:
            continue

        result = search_espn_player(p["name"], team_name_lower)
        if result:
            log.info(f"  [SEARCH] {p['name']} -> ESPN {result['id']} (ESPN name: \"{result['displayName']}\")")
            apply_mapping(p["id"], result["id"], dry_run)
            total_search += 1

        time.sleep(SEARCH_DELAY)

    # Summary
    total_mapped = total_exact + total_lastname + total_search
    log.info(
        f"Done. Exact: {total_exact}, Last-name: {total_lastname}, Search: {total_search}, "
        f"Total mapped: {total_mapped}, Skipped: {total_skipped}, Errors: {total_errors}"
    )
    if dry_run:
        log.info("(Dry run — no changes written)")


if __name__ == "__main__":
    main()
