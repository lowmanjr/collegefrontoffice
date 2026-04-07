"""
scrape_cfbd_production.py
--------------------------
Fetches 2025 season stats from the CollegeFootballData (CFBD) API using a
team-batching strategy (the API does not support per-player lookups), then
calculates a normalized production_score (0-100) and an estimated snaps_played
for each matched College Athlete, and writes both back to Supabase.

Architecture:
  Pass 1 — fetch all 16 teams from Supabase, hit CFBD once per team, aggregate
            all returned player stats into master_stats keyed by integer playerId.
  Pass 2 — fetch College Athletes with cfbd_id set, cast cfbd_id to int, look up
            directly in master_stats, score, and update Supabase.

Scoring rules by position group:
  QB       — passing yards, rushing yards, passing TDs, rushing TDs
  RB/WR/TE — rushing yards, receiving yards, rushing TDs, receiving TDs
  DEF      — tackles, TFLs, sacks, passes defended
  OL       — games played / started (stats are sparse for linemen)
  Other    — games played proxy only

Usage:
    python scrape_cfbd_production.py

Requirements:
    pip install supabase python-dotenv requests
"""

import os
import time
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# 1. SETUP
# ---------------------------------------------------------------------------

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))

SUPABASE_URL      = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise EnvironmentError("Missing Supabase credentials in .env.local")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

CFBD_API_KEY = os.getenv("CFBD_API_KEY")

if not CFBD_API_KEY:
    raise EnvironmentError("Missing CFBD_API_KEY in .env.local")

CFBD_HEADERS = {
    "Authorization": f"Bearer {CFBD_API_KEY}",
    "Accept": "application/json",
}

CFBD_STATS_URL = "https://api.collegefootballdata.com/stats/player/season"
CFBD_YEAR      = 2025
TEAM_DELAY     = 1  # seconds between per-team CFBD requests

# ---------------------------------------------------------------------------
# 2. POSITION GROUP CLASSIFICATION
# ---------------------------------------------------------------------------

QB_POSITIONS  = {"QB"}
RB_POSITIONS  = {"RB", "FB"}
WR_POSITIONS  = {"WR", "TE"}
DEF_POSITIONS = {"DL", "DE", "DT", "EDGE", "NT", "LB", "ILB", "OLB", "CB", "S", "DB", "FS", "SS"}
OL_POSITIONS  = {"OL", "OT", "OG", "C", "LT", "RT", "G"}


def position_group(position: str) -> str:
    pos = position.strip().upper()
    if pos in QB_POSITIONS:
        return "QB"
    if pos in RB_POSITIONS:
        return "RB"
    if pos in WR_POSITIONS:
        return "WR"
    if pos in DEF_POSITIONS:
        return "DEF"
    if pos in OL_POSITIONS:
        return "OL"
    return "OTHER"


# ---------------------------------------------------------------------------
# 3. PRODUCTION SCORING ALGORITHM
# ---------------------------------------------------------------------------

# Normalization caps representing elite single-season outputs
_CAPS = {
    "QB":  {"pass_yds": 4500, "rush_yds": 800,  "pass_td": 40, "rush_td": 12},
    "RB":  {"rush_yds": 1500, "rec_yds":  600,  "rush_td": 15, "rec_td":  6},
    "WR":  {"rec_yds":  1500, "rush_yds": 200,  "rec_td":  15, "rush_td": 3},
    "DEF": {"tackles":  120,  "tfl":      20,   "sacks":   15, "pd":      20},
    "OL":  {"games":    13},
}


def _stat(stats_map: dict[str, float], *keys: str) -> float:
    """Return the first matching key value from stats_map, defaulting to 0."""
    for key in keys:
        val = stats_map.get(key)
        if val is not None:
            return float(val)
    return 0.0


def calculate_production(stats_list: list[dict], position: str) -> tuple[int, int]:
    """
    Parse a list of CFBD stat-row dicts for a single player and return
    (production_score, snaps_played).

    Each row in stats_list has the shape:
      {"statType": "passingYards", "stat": 3200, ...}

    production_score is normalized to 0-100 against position-specific caps.
    snaps_played is estimated as games_played * 50 (CFBD has no raw snap data).
    Returns (0, 0) when no usable stats are present.
    """
    if not stats_list:
        return 0, 0

    # Flatten into a lowercase, space-stripped key dict for resilient lookup
    stats_map: dict[str, float] = {}
    for entry in stats_list:
        stat_type = (entry.get("statType") or "").lower().replace(" ", "")
        stat_val  = entry.get("stat")
        if stat_type and stat_val is not None:
            try:
                stats_map[stat_type] = float(stat_val)
            except (TypeError, ValueError):
                pass

    if not stats_map:
        return 0, 0

    games_played = _stat(stats_map, "gamesplayed", "games")
    snaps_played = int(games_played * 50)

    group     = position_group(position)
    raw_score = 0.0

    if group == "QB":
        caps = _CAPS["QB"]
        pass_yds = _stat(stats_map, "passingyards", "passyards")
        rush_yds = _stat(stats_map, "rushingyards", "rushyards")
        pass_td  = _stat(stats_map, "passingtds", "passingtouchdowns", "passtouchdowns")
        rush_td  = _stat(stats_map, "rushingtds", "rushingtouchdowns", "rushtouchdowns")
        raw_score = (
            (pass_yds / caps["pass_yds"]) * 45
            + (rush_yds / caps["rush_yds"]) * 15
            + (pass_td  / caps["pass_td"])  * 30
            + (rush_td  / caps["rush_td"])  * 10
        )

    elif group == "RB":
        caps = _CAPS["RB"]
        rush_yds = _stat(stats_map, "rushingyards", "rushyards")
        rec_yds  = _stat(stats_map, "receivingyards", "recyards")
        rush_td  = _stat(stats_map, "rushingtds", "rushingtouchdowns", "rushtouchdowns")
        rec_td   = _stat(stats_map, "receivingtds", "receivingtouchdowns", "rectouchdowns")
        raw_score = (
            (rush_yds / caps["rush_yds"]) * 50
            + (rec_yds  / caps["rec_yds"])  * 20
            + (rush_td  / caps["rush_td"])  * 20
            + (rec_td   / caps["rec_td"])   * 10
        )

    elif group == "WR":
        caps = _CAPS["WR"]
        rec_yds  = _stat(stats_map, "receivingyards", "recyards")
        rush_yds = _stat(stats_map, "rushingyards", "rushyards")
        rec_td   = _stat(stats_map, "receivingtds", "receivingtouchdowns", "rectouchdowns")
        rush_td  = _stat(stats_map, "rushingtds", "rushingtouchdowns", "rushtouchdowns")
        raw_score = (
            (rec_yds  / caps["rec_yds"])  * 55
            + (rush_yds / caps["rush_yds"]) * 10
            + (rec_td   / caps["rec_td"])   * 30
            + (rush_td  / caps["rush_td"])  * 5
        )

    elif group == "DEF":
        caps = _CAPS["DEF"]
        tackles = _stat(stats_map, "tackles", "totaltackles", "solotackles")
        tfl     = _stat(stats_map, "tacklesforloss", "tfl", "tackleforloss")
        sacks   = _stat(stats_map, "sacks")
        pd      = _stat(stats_map, "passesdefended", "passdeflections", "pd", "pbu")
        raw_score = (
            (tackles / caps["tackles"]) * 35
            + (tfl     / caps["tfl"])     * 25
            + (sacks   / caps["sacks"])   * 25
            + (pd      / caps["pd"])      * 15
        )

    elif group == "OL":
        caps  = _CAPS["OL"]
        games = max(games_played, _stat(stats_map, "gamesstarted"))
        raw_score = (games / caps["games"]) * 100

    else:
        # K, P, LS, ATH, etc. — participation proxy only
        raw_score = (games_played / 13) * 50

    production_score = max(0, min(100, round(raw_score)))
    return production_score, snaps_played


# ---------------------------------------------------------------------------
# 4. PASS 1 — BUILD MASTER STATS DICT FROM CFBD (one request per team)
#
# master_stats: integer playerId → list of stat-row dicts for that player
# ---------------------------------------------------------------------------

def fetch_teams() -> list[str]:
    """Return university_name values from our Supabase teams table."""
    print("Fetching teams from Supabase...")
    resp = supabase.table("teams").select("university_name").execute()
    names = [row["university_name"] for row in (resp.data or [])]
    print(f"  {len(names)} team(s): {names}\n")
    return names


def build_master_stats(team_names: list[str]) -> dict[int, list[dict]]:
    """
    Hit CFBD once per team and aggregate every returned stat row into a dict
    keyed by integer playerId for deterministic, type-safe matching.
    """
    master: dict[int, list[dict]] = {}
    api_errors = 0

    print("=" * 65)
    print(f"Fetching CFBD player stats by team (year={CFBD_YEAR})...")
    print("=" * 65)

    for team_name in team_names:
        print(f"  [{team_name}]... ", end="", flush=True)

        try:
            r = requests.get(
                CFBD_STATS_URL,
                headers=CFBD_HEADERS,
                params={"year": CFBD_YEAR, "team": team_name},
                timeout=20,
            )
            if r.status_code == 401:
                print("\n[ERROR] 401 Unauthorized — check CFBD_API_KEY in .env.local.")
                raise SystemExit(1)
            r.raise_for_status()
            rows: list[dict] = r.json()
        except requests.RequestException as exc:
            print(f"[ERROR] {exc}")
            api_errors += 1
            time.sleep(TEAM_DELAY)
            continue

        new_players = 0
        for row in rows:
            raw_pid = row.get("playerId")
            if raw_pid is None:
                continue
            try:
                pid = int(raw_pid)
            except (ValueError, TypeError):
                continue
            if pid not in master:
                master[pid] = []
                new_players += 1
            master[pid].append(row)

        print(f"{len(rows)} stat rows, {new_players} new players  (master total: {len(master)})")
        time.sleep(TEAM_DELAY)

    print(f"\nCFBD fetch complete. {len(master)} unique players in master stats dict.")
    if api_errors:
        print(f"  ({api_errors} team request(s) failed — those players will be skipped)")
    print()
    return master


# ---------------------------------------------------------------------------
# 5. PASS 2 — FETCH SUPABASE PLAYERS, MATCH, SCORE, UPDATE
# ---------------------------------------------------------------------------

def fetch_players() -> list[dict]:
    """Return all College Athletes that have a cfbd_id set."""
    PAGE_SIZE   = 1000
    all_players: list[dict] = []
    offset      = 0

    print("Fetching College Athletes with cfbd_id from Supabase...")
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, position, cfbd_id")
            .eq("player_tag", "College Athlete")
            .not_.is_("cfbd_id", "null")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    print(f"  {len(all_players)} player(s) fetched.\n")
    return all_players


def match_and_update(players: list[dict], master: dict[int, list[dict]]) -> None:
    updated  = 0
    no_match = 0
    no_stats = 0

    print("=" * 65)
    print("Matching players to master stats and updating Supabase...")
    print("=" * 65)

    for player in players:
        name     = player["name"]
        position = (player.get("position") or "ATH").strip().upper()

        # Deterministic integer lookup — cfbd_id is already an integer column
        try:
            cfbd_id = int(player["cfbd_id"])
        except (TypeError, ValueError):
            no_match += 1
            continue

        stats_list = master.get(cfbd_id)

        if stats_list is None:
            no_match += 1
            continue

        production_score, snaps_played = calculate_production(stats_list, position)

        if production_score == 0 and snaps_played == 0:
            no_stats += 1
            continue

        supabase.table("players").update(
            {"production_score": production_score, "snaps_played": snaps_played}
        ).eq("id", player["id"]).execute()

        group = position_group(position)
        print(
            f"  [UPDATED] {name:<28}  {position:<5}  {group:<5}  "
            f"score={production_score:>3}/100  snaps≈{snaps_played:,}"
        )
        updated += 1

    print(f"\n{'=' * 65}")
    print(f"Production enrichment complete.")
    print(f"  Players updated         : {updated}")
    print(f"  Players not in CFBD     : {no_match}")
    print(f"  Players no usable stats : {no_stats}")
    print(f"  Total processed         : {len(players)}")


# ---------------------------------------------------------------------------
# 6. MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    team_names = fetch_teams()
    if not team_names:
        print("No teams found in Supabase. Exiting.")
        return

    master = build_master_stats(team_names)
    if not master:
        print("No stats collected from CFBD. Exiting.")
        return

    players = fetch_players()
    if not players:
        print("No eligible players found in Supabase. Exiting.")
        return

    match_and_update(players, master)


if __name__ == "__main__":
    main()
