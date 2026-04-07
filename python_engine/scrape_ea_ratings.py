"""
scrape_ea_ratings.py
---------------------
Fetches EA Sports College Football 26 player ratings for our 16 tracked
teams via the Next.js data API, fuzzy-matches against our players table,
and outputs a CSV report.

Data source: ea.com/games/ea-sports-college-football/ratings
API: Next.js _next/data/{buildId}/en/games/ea-sports-college-football/ratings.json?team={id}

Usage:
    python scrape_ea_ratings.py                      # dry-run, all 16 teams
    python scrape_ea_ratings.py --team georgia        # single team
    python scrape_ea_ratings.py --team georgia --apply # write ea_overall to DB (future)
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import argparse
import csv
import json
import os
import re
import time
import unicodedata
from difflib import SequenceMatcher

import requests
from supabase_client import supabase

# ─── Constants ──────────────────────────────────────────────────────────────

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
REQUEST_DELAY = 1.0  # seconds between API calls

CSV_OUT = os.path.join(os.path.dirname(__file__), "data", "ea_ratings.csv")

# EA team IDs for our 16 tracked teams.
# Key = normalized university_name (lowercase).
EA_TEAM_IDS: dict[str, int] = {
    "alabama":        3,
    "clemson":        20,
    "florida":        29,
    "georgia":        32,
    "lsu":            48,
    "miami":          52,
    "michigan":       54,
    "notre dame":     70,
    "ohio state":     72,
    "oklahoma":       73,
    "oregon":         77,
    "south carolina": 88,
    "tennessee":      94,
    "texas":          96,
    "usc":           110,
    "washington":    120,
}

DEFAULT_THRESHOLD = 0.80


# ─── Helpers ────────────────────────────────────────────────────────────────

def norm(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-z0-9 ]", "", ascii_name.lower())
    return " ".join(clean.split())


def fuzzy(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


# ─── Build ID discovery ────────────────────────────────────────────────────

def get_build_id() -> str | None:
    """Extract the Next.js buildId from the ratings page."""
    try:
        resp = requests.get(
            "https://www.ea.com/games/ea-sports-college-football/ratings",
            headers={"User-Agent": USER_AGENT},
            timeout=20,
        )
        resp.raise_for_status()
        match = re.search(r'"buildId":"([^"]+)"', resp.text)
        if match:
            return match.group(1)
    except Exception as exc:
        print(f"  [ERROR] Failed to fetch build ID: {exc}")
    return None


# ─── EA API ─────────────────────────────────────────────────────────────────

def fetch_ea_team(build_id: str, ea_team_id: int) -> list[dict]:
    """
    Fetch all players for an EA team via the Next.js data API.
    Returns list of {name, position, ovr, school_year, jersey}.
    """
    url = (
        f"https://www.ea.com/_next/data/{build_id}/en/games/"
        f"ea-sports-college-football/ratings.json?team={ea_team_id}"
    )
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"    [ERROR] API request failed: {exc}")
        return []

    items = data.get("pageProps", {}).get("ratingDetails", {}).get("items", [])

    players: list[dict] = []
    for item in items:
        first = (item.get("firstName") or "").strip()
        last = (item.get("lastName") or "").strip()
        name = f"{first} {last}".strip()
        if not name:
            continue

        pos_data = item.get("position") or {}
        team_data = item.get("team") or {}

        players.append({
            "name": name,
            "position": pos_data.get("shortLabel", "?"),
            "position_full": pos_data.get("label", "?"),
            "ovr": item.get("overallRating", 0),
            "school_year": item.get("schoolYear", "?"),
            "jersey": item.get("jerseyNum"),
            "team_label": team_data.get("label", "?"),
        })

    return players


# ─── DB fetching ────────────────────────────────────────────────────────────

def fetch_teams() -> dict[str, str]:
    resp = supabase.table("teams").select("id, university_name").execute()
    return {t["id"]: t["university_name"] for t in (resp.data or [])}


def fetch_college_athletes() -> list[dict]:
    all_players: list[dict] = []
    offset = 0
    PAGE = 1000
    while True:
        resp = (
            supabase.table("players")
            .select(
                "id, name, position, team_id, cfo_valuation, "
                "is_on_depth_chart, depth_chart_rank, roster_status, "
                "star_rating, class_year, production_score"
            )
            .eq("player_tag", "College Athlete")
            .range(offset, offset + PAGE - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE
    return all_players


# ─── Matching ───────────────────────────────────────────────────────────────

def match_ea_players(
    ea_players: list[dict],
    db_players: list[dict],
    team_id: str,
    threshold: float,
) -> tuple[list[dict], list[dict]]:
    """
    Fuzzy-match EA players against our DB players for one team.
    Returns (matched, unmatched).
    """
    team_roster = [p for p in db_players if str(p.get("team_id")) == team_id]
    db_index = {norm(p["name"]): p for p in team_roster}

    matched: list[dict] = []
    unmatched: list[dict] = []

    for ea in ea_players:
        ea_norm = norm(ea["name"])

        # Exact match
        if ea_norm in db_index:
            p = db_index[ea_norm]
            matched.append({**ea, "player_id": str(p["id"]), "player_name": p["name"],
                            "match_confidence": 1.0, "db_player": p})
            continue

        # Fuzzy match
        best_score = 0.0
        best_player = None
        for db_name, player in db_index.items():
            score = SequenceMatcher(None, ea_norm, db_name).ratio()
            if score > best_score:
                best_score = score
                best_player = player

        if best_player and best_score >= threshold:
            matched.append({**ea, "player_id": str(best_player["id"]),
                            "player_name": best_player["name"],
                            "match_confidence": round(best_score, 3),
                            "db_player": best_player})
        else:
            unmatched.append({**ea, "best_score": round(best_score, 3)})

    return matched, unmatched


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scrape EA CFB 26 ratings")
    parser.add_argument("--team", type=str, default=None, help="Single team (e.g. --team georgia)")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help=f"Match threshold (default {DEFAULT_THRESHOLD})")
    args = parser.parse_args()

    print("=" * 80)
    print("  EA SPORTS COLLEGE FOOTBALL 26 — RATINGS SCRAPER")
    print("=" * 80)

    # ── Discover build ID ───────────────────────────────────────────────────
    print("\n  Discovering Next.js build ID...")
    build_id = get_build_id()
    if not build_id:
        print("  [FATAL] Could not discover build ID. Exiting.")
        return
    print(f"  Build ID: {build_id}")

    # ── Load DB data ────────────────────────────────────────────────────────
    print("\n  Loading teams and players from Supabase...")
    teams = fetch_teams()
    players = fetch_college_athletes()
    print(f"  Teams: {len(teams)}, College athletes: {len(players)}")

    team_name_to_id = {v.lower(): k for k, v in teams.items()}

    # ── Determine which teams to run ────────────────────────────────────────
    if args.team:
        team_filter = args.team.strip().lower()
        if team_filter not in EA_TEAM_IDS:
            print(f"\n  [ERROR] Team '{args.team}' not found.")
            print(f"  Available: {', '.join(sorted(EA_TEAM_IDS.keys()))}")
            return
        teams_to_run = {team_filter: EA_TEAM_IDS[team_filter]}
    else:
        teams_to_run = EA_TEAM_IDS

    # ── Scrape and match ────────────────────────────────────────────────────
    all_matched: list[dict] = []
    all_unmatched: list[dict] = []
    summary_rows: list[tuple] = []

    print(f"\n{'=' * 80}")

    for team_key, ea_id in teams_to_run.items():
        db_team_id = team_name_to_id.get(team_key)
        display = teams.get(db_team_id, team_key.title()) if db_team_id else team_key.title()

        print(f"\n  [{display}] EA team ID={ea_id}")

        ea_players = fetch_ea_team(build_id, ea_id)
        print(f"    Fetched: {len(ea_players)} players from EA")

        if not ea_players:
            summary_rows.append((display, 0, 0, 0))
            time.sleep(REQUEST_DELAY)
            continue

        if not db_team_id:
            print(f"    [WARN] Team not found in our DB — skipping match")
            summary_rows.append((display, len(ea_players), 0, len(ea_players)))
            time.sleep(REQUEST_DELAY)
            continue

        matched, unmatched = match_ea_players(ea_players, players, db_team_id, args.threshold)

        # Print matched players sorted by OVR
        matched.sort(key=lambda m: -m["ovr"])
        print(f"    Matched: {len(matched)}, Unmatched: {len(unmatched)}")

        if unmatched:
            print(f"    Unmatched EA names:")
            for u in sorted(unmatched, key=lambda x: -x["ovr"])[:8]:
                print(f"      {u['name']:<28} {u['position']:<6} OVR={u['ovr']}  best={u['best_score']:.2f}")
            if len(unmatched) > 8:
                print(f"      ... and {len(unmatched) - 8} more")

        for m in matched:
            m["team_display"] = display
        all_matched.extend(matched)
        all_unmatched.extend(unmatched)

        summary_rows.append((display, len(ea_players), len(matched), len(unmatched)))

        if team_key != list(teams_to_run.keys())[-1]:
            time.sleep(REQUEST_DELAY)

    # ── Write CSV ───────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(CSV_OUT), exist_ok=True)
    fieldnames = [
        "ea_name", "ea_team", "ea_position", "ea_ovr", "ea_school_year",
        "matched_player_name", "matched_player_id", "match_confidence",
        "cfo_position", "cfo_valuation", "depth_chart_rank", "production_score",
    ]
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for m in sorted(all_matched, key=lambda x: -x["ovr"]):
            db = m.get("db_player", {})
            writer.writerow({
                "ea_name": m["name"],
                "ea_team": m.get("team_display", m.get("team_label", "?")),
                "ea_position": m["position"],
                "ea_ovr": m["ovr"],
                "ea_school_year": m.get("school_year", "?"),
                "matched_player_name": m["player_name"],
                "matched_player_id": m["player_id"],
                "match_confidence": m["match_confidence"],
                "cfo_position": db.get("position", "?"),
                "cfo_valuation": db.get("cfo_valuation"),
                "depth_chart_rank": db.get("depth_chart_rank"),
                "production_score": db.get("production_score"),
            })
    print(f"\n  CSV written: {CSV_OUT} ({len(all_matched)} rows)")

    # ── Print top matches ───────────────────────────────────────────────────
    top = sorted(all_matched, key=lambda m: -m["ovr"])[:30]
    if top:
        header = f"{'OVR':<5} {'EA NAME':<28} {'TEAM':<18} {'EA POS':<7} {'CFO MATCH':<28} {'CFO POS':<7} {'CONF':>5} {'PROD':>6} {'CFO VAL':>12}"
        print(f"\n{'=' * len(header)}")
        print(f"  TOP EA RATINGS — MATCHED TO CFO")
        print(f"{'=' * len(header)}")
        print(f"  {header}")
        print(f"  {'─' * len(header)}")
        for m in top:
            db = m.get("db_player", {})
            val = db.get("cfo_valuation")
            val_s = f"${val:>10,}" if val else f"{'—':>11}"
            prod = db.get("production_score")
            prod_s = f"{prod:>5.1f}" if prod else f"{'—':>5}"
            print(
                f"  {m['ovr']:<5} {m['name']:<28} {m.get('team_display', '?'):<18} "
                f"{m['position']:<7} {m['player_name']:<28} "
                f"{db.get('position', '?'):<7} {m['match_confidence']:>5.2f} "
                f"{prod_s} {val_s}"
            )

    # ── Summary table ───────────────────────────────────────────────────────
    print(f"\n  {'TEAM':<22} {'EA':>4} {'MATCH':>6} {'UNMTCH':>7}")
    print(f"  {'─' * 42}")
    total_ea = total_match = total_unmatch = 0
    for name, ea, match, unmatch in summary_rows:
        print(f"  {name:<22} {ea:>4} {match:>6} {unmatch:>7}")
        total_ea += ea
        total_match += match
        total_unmatch += unmatch
    print(f"  {'─' * 42}")
    print(f"  {'TOTAL':<22} {total_ea:>4} {total_match:>6} {total_unmatch:>7}")

    print(f"\n{'=' * 80}")


if __name__ == "__main__":
    main()
