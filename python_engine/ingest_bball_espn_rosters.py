"""
ingest_bball_espn_rosters.py
----------------------------
Pulls men's basketball rosters from ESPN's public API and upserts players
into the basketball_players table. Basketball equivalent of ingest_espn_rosters.py.

Source: https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/{id}/roster

Usage:
    python ingest_bball_espn_rosters.py              # ingest all teams
    python ingest_bball_espn_rosters.py --dry-run    # parse only, no DB writes
    python ingest_bball_espn_rosters.py --team byu   # single team
"""

import logging
import sys
import time
import requests
from supabase_client import supabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SPORT_PATH = "basketball/mens-college-basketball"
BASE_URL = "https://site.api.espn.com/apis/site/v2/sports"
RATE_LIMIT_SECONDS = 1.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

# ---------------------------------------------------------------------------
# Position normalization
# ESPN basketball only returns G, F, C — map to our 5-position schema.
# ---------------------------------------------------------------------------

POSITION_MAP = {
    "PG": "PG",
    "SG": "SG",
    "SF": "SF",
    "PF": "PF",
    "C":  "C",
    "G":  "SG",   # Generic guard -> SG
    "F":  "SF",   # Generic forward -> SF
    "CG": "SG",   # Combo guard -> SG (matches On3 normalization)
    "GF": "SF",   # Guard-forward -> SF
    "FC": "PF",   # Forward-center -> PF
}


def normalize_position(raw_pos: str | None) -> str | None:
    if not raw_pos:
        return None
    return POSITION_MAP.get(raw_pos.strip().upper(), raw_pos.strip().upper())


# ---------------------------------------------------------------------------
# ESPN roster fetch
# ---------------------------------------------------------------------------

def fetch_espn_roster(espn_id: str) -> list[dict]:
    """
    Fetch a basketball roster from ESPN. Returns a flat list of athlete dicts.
    Handles both flat arrays and position-grouped structures.
    """
    url = f"{BASE_URL}/{SPORT_PATH}/teams/{espn_id}/roster"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error(f"  ESPN API request failed: {exc}")
        return []

    data = resp.json()
    raw_athletes = data.get("athletes", [])

    # Flatten: ESPN may return a flat list or grouped by position
    athletes = []
    for entry in raw_athletes:
        if isinstance(entry, dict) and "items" in entry:
            # Grouped structure (like football): each entry has position + items[]
            athletes.extend(entry.get("items", []))
        elif isinstance(entry, dict):
            # Flat structure: each entry IS an athlete
            athletes.append(entry)

    return athletes


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def espn_id_from_logo(logo_url: str | None) -> str | None:
    """Derive ESPN team ID from logo URL: .../teamlogos/ncaa/500/{id}.png"""
    if not logo_url:
        return None
    return logo_url.split("/")[-1].replace(".png", "")


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    # Parse --team filter
    team_filter = None
    for i, arg in enumerate(sys.argv):
        if arg == "--team" and i + 1 < len(sys.argv):
            team_filter = sys.argv[i + 1].lower()

    # Load teams dynamically from DB
    query = supabase.table("basketball_teams").select("id, university_name, slug, logo_url")
    if team_filter:
        query = query.eq("slug", team_filter)
    teams_resp = query.order("university_name").execute()
    db_teams = {t["slug"]: t for t in (teams_resp.data or [])}

    # Derive ESPN IDs from logo URLs
    teams_to_process = []
    for t in db_teams.values():
        espn_id = espn_id_from_logo(t.get("logo_url"))
        if not espn_id:
            log.warning(f"[SKIP] {t['university_name']}: no ESPN ID derivable from logo_url")
            continue
        teams_to_process.append({"slug": t["slug"], "espn_id": espn_id})

    if team_filter and not teams_to_process:
        log.error(f"No team with slug '{team_filter}' in basketball_teams")
        return

    # Fetch existing players to enable idempotent re-runs
    existing_resp = (
        supabase.table("basketball_players")
        .select("id, espn_athlete_id, acquisition_type, roster_status")
        .not_.is_("espn_athlete_id", "null")
        .execute()
    )
    existing_by_espn_id: dict[str, str] = {
        p["espn_athlete_id"]: p["id"]
        for p in (existing_resp.data or [])
    }
    # Track portal-protected players: never overwrite team_id or roster_status
    # for players already moved/departed/evaluating via the portal pipeline.
    # Only protect players who have a team_id already set — players with
    # team_id = NULL need their team_id filled when their school is onboarded.
    PROTECTED_ACQUISITION = {"portal", "portal_evaluating"}
    PROTECTED_ROSTER = {"departed_transfer"}

    # Need team_id to check NULL — fetch it for portal/departed players
    portal_resp = (
        supabase.table("basketball_players")
        .select("espn_athlete_id, team_id, acquisition_type, roster_status")
        .not_.is_("espn_athlete_id", "null")
        .execute()
    )
    protected_ids: set[str] = {
        p["espn_athlete_id"]
        for p in (portal_resp.data or [])
        if p.get("team_id") is not None  # only protect if already assigned
        and (
            p.get("acquisition_type") in PROTECTED_ACQUISITION
            or p.get("roster_status") in PROTECTED_ROSTER
        )
    }

    total_upserted = 0
    total_skipped = 0
    total_errors = 0

    for team_cfg in teams_to_process:
        slug = team_cfg["slug"]
        espn_id = team_cfg["espn_id"]

        db_team = db_teams.get(slug)
        if not db_team:
            log.warning(f"[SKIP] slug '{slug}' not found in basketball_teams table")
            continue

        team_id = db_team["id"]
        team_name = db_team["university_name"]

        log.info(f"Processing {team_name} (ESPN ID: {espn_id})...")

        athletes = fetch_espn_roster(espn_id)
        log.info(f"  Fetched {len(athletes)} athletes from ESPN")

        records_to_insert = []
        records_to_update = []
        skipped = 0

        for athlete in athletes:
            athlete_id = athlete.get("id")
            if not athlete_id:
                log.warning(f"  [SKIP] Athlete missing ID: {athlete.get('fullName', '?')}")
                skipped += 1
                continue

            athlete_id_str = str(athlete_id)
            full_name = (athlete.get("fullName") or athlete.get("displayName") or "").strip()
            if not full_name:
                log.warning(f"  [SKIP] Athlete {athlete_id} missing name")
                skipped += 1
                continue

            # Position
            pos_obj = athlete.get("position", {})
            raw_pos = pos_obj.get("abbreviation") if isinstance(pos_obj, dict) else None
            position = normalize_position(raw_pos)

            # Headshot
            headshot_obj = athlete.get("headshot", {})
            headshot_url = None
            if isinstance(headshot_obj, dict):
                headshot_url = headshot_obj.get("href")

            record = {
                "name": full_name,
                "position": position,
                "team_id": team_id,
                "player_tag": "College Athlete",
                "roster_status": "active",
                "espn_athlete_id": athlete_id_str,
                "headshot_url": headshot_url,
                "is_public": True,
            }

            if athlete_id_str in existing_by_espn_id:
                record["id"] = existing_by_espn_id[athlete_id_str]
                # Guard: never overwrite roster state for portal players
                if athlete_id_str in protected_ids:
                    record.pop("team_id", None)
                    record.pop("roster_status", None)
                    record.pop("player_tag", None)
                records_to_update.append(record)
            else:
                records_to_insert.append(record)

        log.info(f"  Mapped {len(records_to_insert) + len(records_to_update)} players ({skipped} skipped)")
        total_skipped += skipped

        if dry_run:
            for r in records_to_insert + records_to_update:
                tag = "NEW" if "id" not in r else "UPD"
                log.info(f"  [{tag}] {r['name']:25s} | {str(r['position']):4s} | ESPN: {r['espn_athlete_id']}")
            total_upserted += len(records_to_insert) + len(records_to_update)
        else:
            count = 0
            # Insert new players
            if records_to_insert:
                try:
                    supabase.table("basketball_players").insert(records_to_insert).execute()
                    count += len(records_to_insert)
                except Exception as exc:
                    log.warning(f"  [BATCH INSERT ERROR] {exc}")
                    # Fall back to row-by-row
                    for row in records_to_insert:
                        try:
                            supabase.table("basketball_players").insert(row).execute()
                            count += 1
                        except Exception as row_exc:
                            log.error(f"  [ROW ERROR] {row['name']}: {row_exc}")
                            total_errors += 1

            # Update existing players
            for row in records_to_update:
                try:
                    player_id = row.pop("id")
                    supabase.table("basketball_players").update(row).eq("id", player_id).execute()
                    count += 1
                except Exception as exc:
                    log.error(f"  [UPDATE ERROR] {row['name']}: {exc}")
                    total_errors += 1

            log.info(f"  {team_name} complete: {count} players upserted")
            total_upserted += count

        time.sleep(RATE_LIMIT_SECONDS)

    log.info("")
    log.info(f"Summary: {len(teams_to_process)} team(s) processed, "
             f"{total_upserted} players upserted, "
             f"{total_skipped} skipped, {total_errors} errors")
    if dry_run:
        log.info("(Dry run -- no changes written)")


if __name__ == "__main__":
    main()
