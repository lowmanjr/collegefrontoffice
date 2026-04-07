"""
populate_draft_projections.py
------------------------------
Populates nfl_draft_projection for depth-chart players using two data sources:

1. CFBD API — matches 2025 actual draft picks against our players via cfbd_id
   to find players who were projected but returned to school (their preDraftRanking
   serves as a baseline projection).

2. CSV file — reads from python_engine/data/draft_projections.csv for manual
   mock draft data entry (the primary method for 2026 projections).

Usage:
    python populate_draft_projections.py              # normal: skip existing
    python populate_draft_projections.py --force      # overwrite existing projections
    python populate_draft_projections.py --csv-only   # skip CFBD, CSV only
    python populate_draft_projections.py --cfbd-only  # skip CSV, CFBD only

CSV format (python_engine/data/draft_projections.csv):
    player_name,position,school,projected_pick
    Cam Ward,QB,Miami,1
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import csv
import argparse
import datetime
import requests
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from dotenv import load_dotenv
from supabase_client import supabase

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))

CFBD_API_KEY = os.getenv("CFBD_API_KEY")
BASE_URL = "https://api.collegefootballdata.com"
HEADERS = {"Authorization": f"Bearer {CFBD_API_KEY}"} if CFBD_API_KEY else {}

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "draft_projections.csv")


# ─── Database helpers ────────────────────────────────────────────────────────

def fetch_depth_chart_players() -> list[dict]:
    """Fetch all depth-chart players with fields needed for matching."""
    all_players = []
    offset = 0
    PAGE = 1000
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, position, team_id, cfbd_id, nfl_draft_projection, is_on_depth_chart")
            .eq("is_on_depth_chart", True)
            .range(offset, offset + PAGE - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE
    return all_players


def fetch_all_players_for_matching() -> list[dict]:
    """Fetch ALL players (including non-DC) for CSV fuzzy matching."""
    all_players = []
    offset = 0
    PAGE = 1000
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, position, team_id, nfl_draft_projection, is_on_depth_chart")
            .range(offset, offset + PAGE - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE
    return all_players


def fetch_teams() -> dict:
    resp = supabase.table("teams").select("id, university_name").execute()
    return {t["id"]: t["university_name"] for t in (resp.data or [])}


def has_valid_projection(player: dict) -> bool:
    proj = player.get("nfl_draft_projection")
    return proj is not None and 0 < proj < 500


# ─── Source 1: CFBD draft picks ──────────────────────────────────────────────

def fetch_cfbd_draft_picks(year: int) -> list[dict]:
    """Fetch actual draft picks from CFBD for a given year."""
    if not CFBD_API_KEY:
        print("  [SKIP] No CFBD_API_KEY set.")
        return []
    url = f"{BASE_URL}/draft/picks"
    try:
        resp = requests.get(url, headers=HEADERS, params={"year": year}, timeout=30)
        resp.raise_for_status()
        return resp.json() or []
    except Exception as exc:
        print(f"  [API ERROR] draft picks year {year}: {exc}")
        return []


def match_cfbd_draft(players: list[dict], force: bool) -> dict[str, int]:
    """
    Match CFBD 2025 draft picks against our players by cfbd_id.
    Returns {player_uuid: projected_pick} for matches found.

    Uses preDraftRanking as the projection value (pre-draft consensus),
    falling back to actual overall pick if preDraftRanking is missing.
    """
    updates: dict[str, int] = {}

    # Build cfbd_id → player lookup
    cfbd_map: dict[int, dict] = {}
    for p in players:
        if p.get("cfbd_id"):
            cfbd_map[int(p["cfbd_id"])] = p

    if not cfbd_map:
        print("  No players with cfbd_id to match.")
        return updates

    # Fetch 2025 draft picks
    print("  Fetching 2025 draft picks from CFBD...")
    picks = fetch_cfbd_draft_picks(2025)
    if not picks:
        print("  No 2025 draft data available.")
        return updates

    matched = 0
    for pick in picks:
        college_id = pick.get("collegeAthleteId")
        if college_id and college_id in cfbd_map:
            player = cfbd_map[college_id]
            # Player was drafted in 2025 — they shouldn't be in our active DB
            # but if they are, their preDraftRanking is useful
            projection = pick.get("preDraftRanking") or pick.get("overall")
            if projection and projection > 0:
                pid = str(player["id"])
                if force or not has_valid_projection(player):
                    updates[pid] = int(projection)
                    matched += 1

    print(f"  CFBD 2025 draft: {len(picks)} picks, {matched} matched our players.")
    return updates


# ─── Source 2: CSV file ──────────────────────────────────────────────────────

def normalize(s: str) -> str:
    """Normalize a name/school for fuzzy matching."""
    return (s or "").lower().strip().replace(".", "").replace("'", "").replace("-", " ")


def fuzzy_score(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def match_csv_projections(players: list[dict], teams: dict, force: bool) -> dict[str, int]:
    """
    Read draft_projections.csv and fuzzy-match against our players.
    Returns {player_uuid: projected_pick}.
    """
    updates: dict[str, int] = {}

    if not os.path.exists(CSV_PATH):
        print(f"  [SKIP] CSV not found: {CSV_PATH}")
        return updates

    # Build lookup structures
    team_name_to_id = {normalize(v): k for k, v in teams.items()}
    # Also build reverse: player name + school → player
    player_index: list[tuple[str, str, dict]] = []
    for p in players:
        name = normalize(p.get("name") or "")
        school = normalize(teams.get(str(p.get("team_id", "")), ""))
        player_index.append((name, school, p))

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"  Read {len(rows)} entries from CSV.")

    matched = 0
    unmatched = []
    for row in rows:
        csv_name = row.get("player_name", "").strip()
        csv_pos = row.get("position", "").strip().upper()
        csv_school = row.get("school", "").strip()
        csv_pick = row.get("projected_pick", "").strip()

        if not csv_name or not csv_pick:
            continue

        try:
            pick_num = int(csv_pick)
        except ValueError:
            print(f"  [WARN] Invalid pick number for {csv_name}: {csv_pick}")
            continue

        if pick_num < 1 or pick_num > 300:
            print(f"  [WARN] Pick {pick_num} out of range for {csv_name}")
            continue

        # Find best match
        best_match = None
        best_score = 0.0

        for pname, pschool, player in player_index:
            name_score = fuzzy_score(csv_name, player.get("name", ""))
            school_score = fuzzy_score(csv_school, teams.get(str(player.get("team_id", "")), ""))

            # Bonus for position match
            pos_bonus = 0.05 if csv_pos == (player.get("position") or "").upper().strip() else 0

            # Combined score: name is most important, school confirms
            combined = name_score * 0.65 + school_score * 0.30 + pos_bonus

            if combined > best_score:
                best_score = combined
                best_match = player

        if best_match and best_score >= 0.70:
            pid = str(best_match["id"])
            if force or not has_valid_projection(best_match):
                updates[pid] = pick_num
                matched += 1
            else:
                existing = best_match.get("nfl_draft_projection")
                if existing and existing < 500:
                    pass  # Already has projection, skip
        else:
            unmatched.append(f"{csv_name} ({csv_school}) — best score: {best_score:.2f}")

    print(f"  CSV: {matched} matched, {len(unmatched)} unmatched.")
    if unmatched:
        for u in unmatched[:10]:
            print(f"    Unmatched: {u}")

    return updates


# ─── Write updates ───────────────────────────────────────────────────────────

def write_projections(updates: dict[str, int], players: list[dict]) -> int:
    """Write nfl_draft_projection to the database. Returns count written."""
    if not updates:
        print("\nNo updates to write.")
        return 0

    now = datetime.datetime.utcnow().isoformat()
    player_map = {str(p["id"]): p for p in players}
    written = 0

    for pid, pick in updates.items():
        try:
            supabase.table("players").update(
                {"nfl_draft_projection": pick, "last_updated": now}
            ).eq("id", pid).execute()
            written += 1
        except Exception as exc:
            name = player_map.get(pid, {}).get("name", pid)
            print(f"  [ERROR] {name}: {exc}")

    return written


# ─── Summary ─────────────────────────────────────────────────────────────────

def print_summary(updates: dict[str, int], players: list[dict], teams: dict, written: int):
    player_map = {str(p["id"]): p for p in players}

    print(f"\n{'=' * 90}")
    print(f"  DRAFT PROJECTION UPDATE SUMMARY")
    print(f"{'=' * 90}")
    print(f"  Players updated: {written}")

    if not updates:
        return

    # By round
    rounds = Counter()
    for pick in updates.values():
        rnd = (pick - 1) // 32 + 1
        rounds[rnd] += 1
    print(f"\n  By projected round:")
    for rnd in sorted(rounds.keys()):
        print(f"    Round {rnd}: {rounds[rnd]}")

    # By position
    positions = Counter()
    for pid in updates:
        p = player_map.get(pid, {})
        positions[(p.get("position") or "?").upper()] += 1
    print(f"\n  By position:")
    for pos, cnt in sorted(positions.items(), key=lambda x: -x[1]):
        print(f"    {pos:<6} {cnt}")

    # List all updates
    sorted_updates = sorted(updates.items(), key=lambda x: x[1])
    print(f"\n  {'RK':<4} {'NAME':<28} {'POS':<6} {'TEAM':<20} {'PICK':>5}")
    print(f"  {'-' * 70}")
    for i, (pid, pick) in enumerate(sorted_updates, 1):
        p = player_map.get(pid, {})
        team = teams.get(str(p.get("team_id", "")), "")[:19]
        print(f"  {i:<4} {p.get('name', '?'):<28} {(p.get('position') or '?'):<6} {team:<20} {pick:>5}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Populate NFL draft projections")
    parser.add_argument("--force", action="store_true", help="Overwrite existing projections")
    parser.add_argument("--csv-only", action="store_true", help="Skip CFBD, use CSV only")
    parser.add_argument("--cfbd-only", action="store_true", help="Skip CSV, use CFBD only")
    args = parser.parse_args()

    print("=" * 90)
    print("  NFL DRAFT PROJECTION PIPELINE")
    print("=" * 90)

    teams = fetch_teams()
    dc_players = fetch_depth_chart_players()
    all_players = fetch_all_players_for_matching()
    print(f"  Depth chart players: {len(dc_players)}")
    print(f"  Total players (for matching): {len(all_players)}")

    existing = sum(1 for p in dc_players if has_valid_projection(p))
    print(f"  Already have projections: {existing}")
    print(f"  Force overwrite: {args.force}\n")

    all_updates: dict[str, int] = {}

    # Source 1: CFBD
    if not args.csv_only:
        print("─── Source 1: CFBD 2025 Draft Picks ───")
        cfbd_updates = match_cfbd_draft(dc_players, args.force)
        all_updates.update(cfbd_updates)

    # Source 2: CSV
    if not args.cfbd_only:
        print("\n─── Source 2: CSV Mock Draft Data ───")
        csv_updates = match_csv_projections(all_players, teams, args.force)
        # Only include DC players from CSV matches
        dc_ids = {str(p["id"]) for p in dc_players}
        csv_dc = {pid: pick for pid, pick in csv_updates.items() if pid in dc_ids}
        non_dc = len(csv_updates) - len(csv_dc)
        if non_dc:
            print(f"  Filtered out {non_dc} non-depth-chart match(es).")
        all_updates.update(csv_dc)

    # Write
    print(f"\n─── Writing Updates ───")
    written = write_projections(all_updates, all_players)
    print_summary(all_updates, all_players, teams, written)

    # ── Future enhancement: web scraping approach ────────────────────────────
    # To scrape mock draft data from a public source, you could use:
    #
    # import requests
    # from bs4 import BeautifulSoup
    #
    # def scrape_mock_draft(url: str) -> list[dict]:
    #     """
    #     Scrape a public mock draft page and extract projections.
    #     Example sources:
    #       - ESPN: https://www.espn.com/nfl/draft/rounds/_/round/1
    #       - NFL.com: https://www.nfl.com/draft/tracker/picks
    #       - The Athletic, PFF, etc.
    #
    #     Each source has a different HTML structure, so the selectors
    #     below are illustrative:
    #
    #     resp = requests.get(url, headers={"User-Agent": "CFO-Bot/1.0"})
    #     soup = BeautifulSoup(resp.text, "html.parser")
    #
    #     projections = []
    #     for row in soup.select(".mock-draft-pick"):
    #         name = row.select_one(".player-name").text.strip()
    #         school = row.select_one(".player-school").text.strip()
    #         pick_num = int(row.select_one(".pick-number").text.strip())
    #         position = row.select_one(".player-position").text.strip()
    #         projections.append({
    #             "player_name": name,
    #             "position": position,
    #             "school": school,
    #             "projected_pick": pick_num,
    #         })
    #     return projections
    #
    # To use this:
    # 1. Write projections to CSV: save results to data/draft_projections.csv
    # 2. Run this script with --csv-only to process the CSV
    # 3. Or modify this script to call scrape_mock_draft() directly
    #    and feed results into the matching pipeline.
    #
    # Note: Always check the site's robots.txt and terms of service.
    # Rate-limit requests (time.sleep(1) between pages).
    # Many sports sites block automated scraping.


if __name__ == "__main__":
    main()
