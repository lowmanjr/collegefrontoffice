"""
Sync rosters using ESPN athlete IDs as the source of truth.
For each team, fetches ESPN's current roster and:
- Moves players who transferred (ESPN ID exists at a different team in our DB)
- Creates new players not in our DB
- Flags players in our DB who are no longer on any ESPN roster

Usage: python sync_espn_rosters_by_id.py [--dry-run] [--team Texas]
"""

import logging
import sys
import re
import time
import unicodedata
import requests
from collections import defaultdict
from supabase_client import supabase
from ingest_espn_rosters import ESPN_IDS_BY_NAME

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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


def fetch_espn_roster(espn_team_id: int) -> list[dict]:
    """Fetch all athletes from ESPN's roster endpoint for a team."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/{espn_team_id}/roster?limit=500"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning(f"  Failed to fetch ESPN roster for team {espn_team_id}: {e}")
        return []

    athletes = []
    for group in data.get("athletes", []):
        for a in group.get("items", []):
            espn_id = int(a.get("id", 0))
            name = a.get("displayName", "")
            position = a.get("position", {}).get("abbreviation", "")
            if espn_id and name:
                athletes.append({
                    "espn_id": espn_id,
                    "name": name,
                    "position": position,
                    "headshot_url": f"https://a.espncdn.com/combiner/i?img=/i/headshots/college-football/players/full/{espn_id}.png&w=200&h=146",
                })
    return athletes


def main():
    dry_run = "--dry-run" in sys.argv

    target_team = None
    for i, arg in enumerate(sys.argv):
        if arg == "--team" and i + 1 < len(sys.argv):
            target_team = sys.argv[i + 1]
            break

    # Fetch all teams
    teams_resp = supabase.table("teams").select("id, university_name").execute()
    teams = {t["university_name"]: t["id"] for t in (teams_resp.data or [])}
    team_id_to_name = {t["id"]: t["university_name"] for t in (teams_resp.data or [])}
    log.info(f"Loaded {len(teams)} teams")

    # Fetch ALL college athletes from DB (paginated)
    log.info("Fetching all college athletes from DB...")
    all_db_players = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, team_id, espn_athlete_id, is_override, roster_status, headshot_url, position")
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

    # Build ESPN ID lookup: espn_athlete_id -> player record
    espn_id_lookup = {}
    for p in all_db_players:
        eid = p.get("espn_athlete_id")
        if eid:
            espn_id_lookup[eid] = p

    # Also build name lookup for fallback matching
    name_lookup: dict[str, list[dict]] = defaultdict(list)
    for p in all_db_players:
        norm = normalize(p["name"])
        name_lookup[norm].append(p)

    total_transferred = 0
    total_created = 0
    total_updated = 0
    total_already_correct = 0

    teams_to_process = list(ESPN_IDS_BY_NAME.items())
    if target_team:
        teams_to_process = [(k, v) for k, v in ESPN_IDS_BY_NAME.items() if k.lower() == target_team.lower()]
        if not teams_to_process:
            log.error(f"Team '{target_team}' not found")
            sys.exit(1)

    for team_name, espn_team_id in teams_to_process:
        team_id = teams.get(team_name)
        if not team_id:
            continue

        espn_roster = fetch_espn_roster(espn_team_id)
        if not espn_roster:
            continue

        team_transferred = 0
        team_created = 0
        team_updated = 0

        for athlete in espn_roster:
            eid = athlete["espn_id"]

            # Check if we have this ESPN ID in our DB
            db_player = espn_id_lookup.get(eid)

            if db_player:
                if db_player.get("team_id") == team_id:
                    total_already_correct += 1

                    # Update headshot if missing
                    if not db_player.get("headshot_url"):
                        if not dry_run:
                            supabase.table("players").update({
                                "headshot_url": athlete["headshot_url"]
                            }).eq("id", db_player["id"]).execute()
                        team_updated += 1
                    continue

                # Player exists but at a DIFFERENT team — this is a transfer
                if db_player.get("is_override"):
                    continue

                old_team = team_id_to_name.get(db_player.get("team_id"), "UNKNOWN")

                if dry_run:
                    if total_transferred < 50:
                        log.info(f"  [TRANSFER] {athlete['name']} (ESPN {eid}): {old_team} -> {team_name}")
                else:
                    supabase.table("players").update({
                        "team_id": team_id,
                        "roster_status": "active",
                        "headshot_url": athlete["headshot_url"],
                    }).eq("id", db_player["id"]).execute()

                    db_player["team_id"] = team_id

                total_transferred += 1
                team_transferred += 1
            else:
                # ESPN ID not in our DB — check by name
                norm = normalize(athlete["name"])
                name_matches = name_lookup.get(norm, [])

                matched_by_name = None
                for m in name_matches:
                    if m.get("team_id") == team_id and not m.get("espn_athlete_id"):
                        matched_by_name = m
                        break

                if matched_by_name:
                    if not dry_run:
                        supabase.table("players").update({
                            "espn_athlete_id": eid,
                            "headshot_url": athlete["headshot_url"],
                        }).eq("id", matched_by_name["id"]).execute()
                    team_updated += 1
                    total_updated += 1
                else:
                    slug = slugify(athlete["name"])
                    team_slug = slugify(team_name)

                    if dry_run:
                        if total_created < 30:
                            log.info(f"  [NEW] {athlete['name']} ({athlete['position']}) -> {team_name}")
                    else:
                        try:
                            supabase.table("players").insert({
                                "name": athlete["name"],
                                "position": athlete["position"] if athlete["position"] else None,
                                "team_id": team_id,
                                "player_tag": "College Athlete",
                                "roster_status": "active",
                                "is_public": True,
                                "is_override": False,
                                "espn_athlete_id": eid,
                                "headshot_url": athlete["headshot_url"],
                                "slug": slug,
                            }).execute()
                        except Exception:
                            try:
                                supabase.table("players").insert({
                                    "name": athlete["name"],
                                    "position": athlete["position"] if athlete["position"] else None,
                                    "team_id": team_id,
                                    "player_tag": "College Athlete",
                                    "roster_status": "active",
                                    "is_public": True,
                                    "is_override": False,
                                    "espn_athlete_id": eid,
                                    "headshot_url": athlete["headshot_url"],
                                    "slug": f"{slug}-{team_slug}",
                                }).execute()
                            except Exception as e2:
                                log.warning(f"  Failed to create {athlete['name']}: {e2}")
                                continue

                    total_created += 1
                    team_created += 1

        if team_transferred or team_created or team_updated:
            log.info(f"  {team_name}: {team_transferred} transfers, {team_created} new, {team_updated} updated")

        time.sleep(0.5)

    log.info(f"Done.")
    log.info(f"  Transfers moved: {total_transferred}")
    log.info(f"  New players created: {total_created}")
    log.info(f"  Updated (ESPN ID/headshot): {total_updated}")
    log.info(f"  Already correct: {total_already_correct}")
    if dry_run:
        log.info("(Dry run -- no changes written)")


if __name__ == "__main__":
    main()
