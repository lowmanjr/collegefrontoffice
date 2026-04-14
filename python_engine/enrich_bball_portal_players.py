"""
Creates basketball_players records for portal players who don't
yet exist in our DB — typically players from schools not yet
tracked by CFO.

Approach: finds each player on their origin school's ESPN roster,
fetches their season stats, and creates a full record with valuation.

Players from non-tracked schools are created with team_id = NULL.
When that school is later onboarded, ingest_bball_espn_rosters.py
matches by espn_athlete_id and fills in team_id automatically.

Pipeline position: Run after parse_bball_portal_txt.py,
before calculate_bball_valuations.py and generate_bball_slugs.py.

Usage:
  python enrich_bball_portal_players.py --dry-run
  python enrich_bball_portal_players.py
"""

import argparse
import re
import sys
import time
import unicodedata

import requests

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from supabase_client import supabase

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
CURRENT_SEASON = 2026
RATE_LIMIT = 0.8

NAME_ALIASES: dict[str, str] = {
    "somto cyril": "somtochukwu cyril",
    "rob wright": "robert wright iii",
    "kennard davis": "kennard davis jr.",
    "richard barron": "rich barron",
}

# Maps On3 school names from portal entries → ESPN team IDs
SCHOOL_ESPN_IDS: dict[str, int] = {
    "Alabama Crimson Tide": 333,
    "Arkansas Razorbacks": 8,
    "Arkansas-Little Rock Trojans": 2031,
    "Arkansas-Pine Bluff Golden Lions": 2029,
    "Boise State Broncos": 68,
    "California Golden Bears": 25,
    "Central Arkansas Bears": 2110,
    "Creighton Bluejays": 156,
    "Connecticut Huskies": 41,
    "Duquesne Dukes": 2184,
    "Eastern Kentucky Colonels": 2198,
    "Florida Gators": 57,
    "Georgetown Hoyas": 46,
    "Houston Cougars": 248,
    "Illinois Fighting Illini": 356,
    "Indiana Hoosiers": 84,
    "Iowa State Cyclones": 66,
    "James Madison Dukes": 256,
    "Kansas State Wildcats": 2306,
    "Loyola (Chi) Ramblers": 2350,
    "Missouri-Kansas City Kangaroos": 140,
    "North Carolina Tar Heels": 153,
    "Northern Kentucky Norse": 94,
    "Ohio State Buckeyes": 194,
    "Oklahoma Sooners": 201,
    "Oklahoma State Cowboys": 197,
    "Oregon State Beavers": 204,
    "Pittsburgh Panthers": 221,
    "South Florida Bulls": 58,
    "Tennessee Volunteers": 2633,
    "Texas A&M Aggies": 245,
    "USF Bulls": 58,
    "University of San Francisco Dons": 2539,
    "Villanova Wildcats": 222,
    "West Georgia Wolves": 2698,
    "Western Kentucky Hilltoppers": 98,
    "Xavier Musketeers": 2752,
}

POSITION_MAP: dict[str, str] = {
    "PG": "PG", "SG": "SG", "SF": "SF", "PF": "PF", "C": "C",
    "G": "SG", "F": "SF", "CG": "SG", "GF": "SF", "FC": "PF",
}


def normalize(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower().strip()
    name = re.sub(r"[.'']", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def fetch_roster(espn_team_id: int) -> list[dict]:
    """Fetch a team's roster from ESPN."""
    url = (
        f"https://site.api.espn.com/apis/site/v2/sports/basketball/"
        f"mens-college-basketball/teams/{espn_team_id}/roster"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return []
        return resp.json().get("athletes", [])
    except Exception as e:
        print(f"  Roster fetch error for team {espn_team_id}: {e}")
        return []


def find_player_on_roster(
    target_name: str, roster: list[dict]
) -> dict | None:
    """Match a portal name to an ESPN roster entry by normalized name."""
    target = normalize(target_name)
    for athlete in roster:
        espn_name = normalize(athlete.get("displayName", ""))
        if target == espn_name:
            return athlete
        # Try without periods (J.P. → JP)
        if target.replace(".", "") == espn_name.replace(".", ""):
            return athlete
    # Fuzzy: try last-name match + first initial
    target_parts = target.split()
    if len(target_parts) >= 2:
        for athlete in roster:
            espn_name = normalize(athlete.get("displayName", ""))
            espn_parts = espn_name.split()
            if (
                len(espn_parts) >= 2
                and target_parts[-1] == espn_parts[-1]
                and target_parts[0][0] == espn_parts[0][0]
            ):
                return athlete
    return None


def fetch_stats(espn_id: str) -> dict:
    """Fetch season stats from ESPN Core API."""
    url = (
        f"https://sports.core.api.espn.com/v2/sports/basketball/"
        f"leagues/mens-college-basketball/seasons/{CURRENT_SEASON}/"
        f"types/2/athletes/{espn_id}/statistics"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return {}
        cats = resp.json().get("splits", {}).get("categories", [])
        stats: dict = {}
        for cat in cats:
            for s in cat.get("stats", []):
                n = s.get("name")
                v = s.get("value")
                if n == "avgMinutes":
                    stats["mpg"] = round(float(v or 0), 1)
                elif n == "avgPoints":
                    stats["ppg"] = round(float(v or 0), 1)
                elif n == "avgRebounds":
                    stats["rpg"] = round(float(v or 0), 1)
                elif n == "avgAssists":
                    stats["apg"] = round(float(v or 0), 1)
                elif n == "PER":
                    stats["per"] = round(float(v or 0), 1)
        return stats
    except Exception:
        return {}


def get_role_tier(mpg: float) -> str:
    if mpg >= 30:
        return "franchise"
    if mpg >= 24:
        return "star"
    if mpg >= 16:
        return "starter"
    if mpg >= 8:
        return "rotation"
    return "bench"


def main(dry_run: bool = False) -> None:
    print("Loading portal entries and existing players...")

    entries = (
        supabase.table("basketball_portal_entries")
        .select(
            "player_name, position, status, origin_school, "
            "origin_team_id, destination_team_id, headshot_url"
        )
        .execute()
        .data
    )

    existing = (
        supabase.table("basketball_players")
        .select("name")
        .execute()
        .data
    )
    existing_names = set()
    for p in existing:
        norm = normalize(p["name"])
        existing_names.add(norm)

    # Find missing
    missing: list[dict] = []
    seen: set[str] = set()
    for e in entries:
        norm = normalize(e["player_name"])
        # Resolve alias, then normalize the alias target too
        alias = NAME_ALIASES.get(norm)
        resolved = normalize(alias) if alias else norm
        if resolved not in existing_names and norm not in existing_names and resolved not in seen:
            missing.append(e)
            seen.add(resolved)

    print(f"Found {len(missing)} portal players not in DB\n")

    if not missing:
        print("Nothing to do.")
        return

    # Cache fetched rosters to avoid re-fetching for same school
    roster_cache: dict[int, list[dict]] = {}
    created = 0
    not_found = 0

    for e in missing:
        name = e["player_name"]
        position = POSITION_MAP.get((e.get("position") or "").upper(), e.get("position"))
        origin_school = e.get("origin_school") or "?"
        origin_team_id = e.get("origin_team_id")

        print(f"Processing: {name} ({position}) from {origin_school}")

        # Look up ESPN team ID for origin school
        espn_team_id = SCHOOL_ESPN_IDS.get(origin_school)
        espn_id = None
        headshot_url = e.get("headshot_url")
        stats: dict = {}

        if espn_team_id:
            # Fetch roster (cached)
            if espn_team_id not in roster_cache:
                roster_cache[espn_team_id] = fetch_roster(espn_team_id)
                time.sleep(RATE_LIMIT)

            roster = roster_cache[espn_team_id]
            athlete = find_player_on_roster(name, roster)

            if athlete:
                espn_id = str(athlete.get("id", ""))
                # ESPN headshot (prefer over On3 if available)
                hs = athlete.get("headshot", {})
                if isinstance(hs, dict) and hs.get("href"):
                    headshot_url = hs["href"]
                print(f"  ESPN ID: {espn_id} (matched on roster)")

                # Fetch stats
                stats = fetch_stats(espn_id)
                time.sleep(RATE_LIMIT)
                if stats.get("mpg"):
                    print(
                        f"  Stats: MPG={stats['mpg']:.1f} "
                        f"PPG={stats.get('ppg', 0):.1f} "
                        f"PER={stats.get('per', 0):.1f}"
                    )
                else:
                    print("  No stats (transfer mid-season or limited minutes)")
            else:
                print(f"  NOT on ESPN roster for {origin_school}")
                not_found += 1
        else:
            print(f"  No ESPN team ID for '{origin_school}' — skipping roster lookup")
            not_found += 1

        # Build placeholder ESPN ID if not found
        if not espn_id:
            slug_part = re.sub(r"[^a-z0-9]", "_", name.lower().strip())
            espn_id = f"portal_{slug_part}"
            print(f"  Using placeholder ID: {espn_id}")

        mpg = stats.get("mpg", 0)
        role_tier = get_role_tier(mpg)
        usage_rate = round(mpg / 40.0, 4) if mpg > 0 else None

        record = {
            "name": name,
            "position": position,
            "player_tag": "College Athlete",
            "acquisition_type": "portal",
            "roster_status": "active",
            "team_id": origin_team_id,
            "espn_athlete_id": espn_id,
            "headshot_url": headshot_url,
            "is_public": True,
            "usage_rate": usage_rate,
            "ppg": stats.get("ppg"),
            "rpg": stats.get("rpg"),
            "apg": stats.get("apg"),
            "per": stats.get("per"),
            "role_tier": role_tier,
        }

        print(f"  → team_id={'set' if origin_team_id else 'NULL'} "
              f"role={role_tier} espn={'real' if not espn_id.startswith('portal_') else 'placeholder'}")

        if not dry_run:
            try:
                supabase.table("basketball_players").insert(record).execute()
            except Exception as ex:
                print(f"  INSERT ERROR: {ex}")
                not_found += 1
                print()
                continue
        created += 1
        print()

    label = "would be " if dry_run else ""
    print(f"Done. {created} players {label}created, {not_found} not found on ESPN.")
    if dry_run:
        print("(Dry run — no changes written)")
    elif created > 0:
        print("\nNext steps:")
        print("  python generate_bball_slugs.py")
        print("  python scrape_bball_247_headshots.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
