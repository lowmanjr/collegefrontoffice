"""
sync_bball_portal_display.py
-----------------------------
Syncs basketball transfer portal entries for display on /basketball/portal.
Captures both committed and evaluating players where origin OR destination
school matches one of our tracked teams in basketball_teams.

Different from sync_basketball_transfer_portal.py which moves players
between rosters. This script is display-only and rebuilds
basketball_portal_entries on each run.

Usage:
    python sync_bball_portal_display.py
    python sync_bball_portal_display.py --dry-run
"""

import json
import re
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8")
from supabase_client import supabase

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

RATE_LIMIT = 1.5

POSITION_MAP = {
    "PG": "PG", "SG": "SG", "SF": "SF", "PF": "PF", "C": "C",
    "G": "SG", "F": "SF", "CG": "SG", "GF": "SF", "FC": "PF",
}

POSITION_BASES = {
    "PG": 700_000, "SG": 600_000, "SF": 550_000,
    "PF": 500_000, "C": 450_000,
}

# Maps On3 school name variants → our university_name in basketball_teams
SCHOOL_ALIASES: dict[str, str] = {
    "byu cougars": "BYU",
    "kentucky wildcats": "Kentucky",
    "uconn huskies": "UConn",
    "connecticut huskies": "UConn",
    "duke blue devils": "Duke",
    "kansas jayhawks": "Kansas",
    "michigan wolverines": "Michigan",
    "georgia bulldogs": "Georgia",
    "san diego state aztecs": "San Diego State",
    "providence friars": "Providence",
    "louisville cardinals": "Louisville",
    "oregon ducks": "Oregon",
    "miami hurricanes": "Miami",
    "miami (fl)": "Miami",
}

# Schools that contain our team names as substrings — explicit non-matches
# to prevent "Kansas State" matching "Kansas", "Northern Michigan" matching "Michigan", etc.
SCHOOL_NON_MATCHES: set[str] = {
    # Kansas / Arkansas overlap ("kansas" is a substring of "arkansas")
    "kansas state", "kansas state wildcats",
    "arkansas", "arkansas razorbacks",
    "arkansas-little rock", "little rock trojans",
    "arkansas-pine bluff", "arkansas pine bluff golden lions",
    "arkansas state", "arkansas state red wolves",
    "central arkansas", "central arkansas bears",
    "missouri-kansas city", "missouri-kansas city kangaroos",
    # Duke / Dukes overlap ("duke" is a substring of "dukes")
    "james madison", "james madison dukes",
    "duquesne", "duquesne dukes",
    # Kentucky overlap
    "eastern kentucky", "eastern kentucky colonels",
    "western kentucky", "western kentucky hilltoppers",
    "northern kentucky", "northern kentucky norse",
    # Georgia overlap
    "west georgia", "west georgia wolves",
    "georgia tech", "georgia state", "georgia southern",
    # Tennessee overlap
    "tennessee state", "tennessee tech",
    "east tennessee", "east tennessee state",
    "middle tennessee", "middle tennessee blue raiders",
    # Michigan overlap
    "michigan state", "northern michigan", "western michigan",
    "eastern michigan", "central michigan",
    # Miami overlap
    "miami (oh)", "miami ohio", "miami redhawks", "miami university redhawks",
    # Oregon overlap
    "oregon state", "oregon state beavers",
    # Connecticut overlap
    "central connecticut", "central connecticut state",
    # Carolina overlap
    "north carolina", "east carolina", "south carolina",
}


def normalize_position(pos: str | None) -> str | None:
    if not pos:
        return None
    return POSITION_MAP.get(pos.upper(), pos.upper())


def compute_portal_valuation(
    player_db: dict | None,
    position: str | None,
    star_rating: int | None,
    market_multiplier: float,
) -> int:
    """Simplified formula for portal display valuations."""
    # If player exists in our DB with a valuation, use it as floor
    existing_val = None
    if player_db and not player_db.get("is_override"):
        existing_val = player_db.get("cfo_valuation")

    has_stats = bool(player_db and (player_db.get("usage_rate") or 0) > 0)
    mpg = (player_db.get("usage_rate") or 0) * 40 if player_db else 0

    pos_base = POSITION_BASES.get(normalize_position(position) or "", 575_000)

    # Role tier
    if has_stats:
        if mpg >= 30:    role = 2.20
        elif mpg >= 24:  role = 1.65
        elif mpg >= 16:  role = 1.20
        elif mpg >= 8:   role = 0.75
        else:            role = 0.30
    else:
        role = 0.60

    # Talent
    per = float(player_db.get("per") or 0) if player_db else 0
    if has_stats and per > 0:
        if per >= 25:    talent = 1.30
        elif per >= 20:  talent = 1.20
        elif per >= 15:  talent = 1.10
        elif per >= 10:  talent = 1.00
        else:            talent = 0.90
    else:
        star_map = {5: 1.30, 4: 1.15, 3: 1.00, 2: 0.85, 1: 0.85}
        talent = star_map.get(star_rating or 0, 0.85)

    # Experience
    exp_map = {
        "Freshman": 0.85, "Sophomore": 0.95, "Junior": 1.05,
        "Senior": 1.10, "Graduate": 1.15,
    }
    exp = exp_map.get(player_db.get("experience_level", "") if player_db else "", 0.90)

    # Social
    ig = player_db.get("ig_followers") or 0 if player_db else 0
    x = player_db.get("x_followers") or 0 if player_db else 0
    tt = player_db.get("tiktok_followers") or 0 if player_db else 0
    weighted = ig + int(x * 0.7) + int(tt * 1.2)
    if weighted >= 1_000_000:    social = 150_000
    elif weighted >= 500_000:    social = 75_000
    elif weighted >= 100_000:    social = 25_000
    elif weighted >= 50_000:     social = 10_000
    elif weighted >= 10_000:     social = 3_000
    else:                        social = 0

    formula = int(pos_base * role * talent * market_multiplier * exp) + social
    formula = max(formula, 5_000)

    if existing_val:
        return max(formula, existing_val)
    return formula


def scrape_portal(status: str) -> list[dict]:
    """Scrape all pages of On3 portal for given status."""
    players: list[dict] = []
    page = 1
    while True:
        url = (
            f"https://www.on3.com/transfer-portal/wire/basketball/"
            f"?status={status}&page={page}"
        )
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
        except Exception as e:
            print(f"  Request error page {page}: {e}")
            break
        if resp.status_code != 200:
            break
        match = re.search(
            r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            resp.text, re.DOTALL,
        )
        if not match:
            break
        data = json.loads(match.group(1))
        items = data["props"]["pageProps"]["playerData"]["list"]
        if not items:
            break
        players.extend(items)
        print(f"  Page {page}: {len(items)} entries")
        page += 1
        time.sleep(RATE_LIMIT)
    return players


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    print("Loading teams from DB...")
    teams_result = supabase.table("basketball_teams") \
        .select("id, university_name, market_multiplier").execute()
    teams_by_name: dict[str, dict] = {
        t["university_name"]: t for t in teams_result.data
    }
    # Build reverse lookup for On3 names
    teams_lower = {name.lower(): name for name in teams_by_name}
    print(f"  {len(teams_by_name)} teams loaded")

    def resolve_team(school_full: str | None) -> dict | None:
        if not school_full:
            return None
        # Direct match
        if school_full in teams_by_name:
            return teams_by_name[school_full]
        # Alias
        alias = SCHOOL_ALIASES.get(school_full.lower())
        if alias and alias in teams_by_name:
            return teams_by_name[alias]
        # Check non-matches before substring (prevents Kansas State → Kansas)
        sl = school_full.lower()
        for non in SCHOOL_NON_MATCHES:
            if non in sl:
                return None
        # Substring fallback
        for our_name in teams_by_name:
            if our_name.lower() in sl:
                return teams_by_name[our_name]
        return None

    print("Loading existing player records...")
    players_result = supabase.table("basketball_players") \
        .select(
            "id, name, cfo_valuation, is_override, usage_rate, per, "
            "experience_level, star_rating, headshot_url, "
            "ig_followers, x_followers, tiktok_followers"
        ).execute()
    players_by_name: dict[str, dict] = {
        p["name"].lower().strip(): p for p in players_result.data
    }
    print(f"  {len(players_by_name)} players loaded")

    print()
    print("Scraping On3 basketball portal — committed...")
    committed = scrape_portal("committed")
    print(f"  Total committed: {len(committed)}")

    print()
    print("Scraping On3 basketball portal — entered (evaluating)...")
    entered = scrape_portal("entered")
    print(f"  Total entered: {len(entered)}")

    print()
    print("Filtering to our teams...")
    records: list[dict] = []
    seen_slugs: set[str] = set()

    for portal_status, items in [("committed", committed), ("entered", entered)]:
        for item in items:
            origin_raw = (item.get("lastTeam") or {}).get("fullName", "")
            commit_obj = item.get("commitStatus") or {}
            dest_obj = commit_obj.get("committedOrganization") or {}
            dest_raw = dest_obj.get("fullName", "") if dest_obj else ""

            origin_team = resolve_team(origin_raw)
            dest_team = resolve_team(dest_raw) if dest_raw else None

            if not origin_team and not dest_team:
                continue

            # Dedup by On3 slug
            slug = item.get("key") or item.get("slug")
            if slug and slug in seen_slugs:
                continue
            if slug:
                seen_slugs.add(slug)

            player_name = item.get("name", "")
            pos_raw = item.get("positionAbbreviation")
            position = normalize_position(pos_raw)

            # Star rating from On3
            rating_obj = item.get("rating") or item.get("transferRating") or {}
            star_rating = rating_obj.get("stars") if isinstance(rating_obj, dict) else None

            # On3 NIL value
            nil_obj = item.get("valuation") or {}
            on3_nil = nil_obj.get("amount") if isinstance(nil_obj, dict) else None

            # Headshot
            player_db = players_by_name.get(player_name.lower().strip())
            headshot = None
            if player_db and player_db.get("headshot_url"):
                headshot = player_db["headshot_url"]
            elif item.get("defaultAssetUrl"):
                headshot = item["defaultAssetUrl"]

            # Market multiplier: destination if committed, origin if evaluating
            if portal_status == "committed" and dest_team:
                mm = dest_team["market_multiplier"]
            elif origin_team:
                mm = origin_team["market_multiplier"]
            else:
                mm = 1.00

            if not star_rating and player_db:
                star_rating = player_db.get("star_rating")

            cfo_val = compute_portal_valuation(
                player_db, position, star_rating, mm,
            )

            entry_date = commit_obj.get("transferEntered") or commit_obj.get("date")
            commitment_date = commit_obj.get("date") if portal_status == "committed" else None

            records.append({
                "player_name": player_name,
                "position": position,
                "origin_school": origin_raw or None,
                "destination_school": dest_raw or None,
                "origin_team_id": origin_team["id"] if origin_team else None,
                "destination_team_id": dest_team["id"] if dest_team else None,
                "status": "committed" if portal_status == "committed" else "evaluating",
                "star_rating": star_rating,
                "cfo_valuation": cfo_val,
                "on3_nil_value": int(on3_nil) if on3_nil else None,
                "headshot_url": headshot,
                "entry_date": entry_date,
                "commitment_date": commitment_date,
                "on3_player_slug": slug,
            })

    committed_ct = sum(1 for r in records if r["status"] == "committed")
    eval_ct = sum(1 for r in records if r["status"] == "evaluating")
    print(f"  Relevant entries: {len(records)} ({committed_ct} committed, {eval_ct} evaluating)")
    print()

    for r in sorted(records, key=lambda x: -(x.get("cfo_valuation") or 0))[:30]:
        dest = r["destination_school"] or "(uncommitted)"
        in_db = "DB" if players_by_name.get(r["player_name"].lower().strip()) else "new"
        print(
            f"  [{r['status']:<10}] [{in_db:3}] "
            f"{r['player_name']:28s} | {str(r['position'] or '?'):4s} | "
            f"{str(r['origin_school'] or '?'):30s} -> "
            f"{dest:30s} | ${r['cfo_valuation'] or 0:>9,}"
        )

    if dry_run:
        print("\nDRY RUN — no DB writes")
        return

    print()
    print("Clearing existing portal entries...")
    supabase.table("basketball_portal_entries") \
        .delete() \
        .neq("id", "00000000-0000-0000-0000-000000000000") \
        .execute()

    if records:
        print(f"Inserting {len(records)} portal entries...")
        for i in range(0, len(records), 50):
            batch = records[i:i + 50]
            supabase.table("basketball_portal_entries").insert(batch).execute()
        print(f"Done. {len(records)} entries written.")
    else:
        print("No relevant portal entries found.")


if __name__ == "__main__":
    main()
