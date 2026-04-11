"""
generate_texas_tech_comparison.py
----------------------------------
Generates a comparison CSV of CFO valuations vs On3 NIL valuations for Texas Tech.

Usage:
    python generate_texas_tech_comparison.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import csv
from supabase_client import supabase
from name_utils import fuzzy_match_player

CSV_OUT = os.path.join(os.path.dirname(__file__), "data", "texas_tech_comparison.csv")

# ─── On3 NIL data for Texas Tech (April 2026) ───────────────────────────────

ON3_DATA = [
    ("Brendan Sorsby", "QB", 3_100_000),
    ("Howard Sampson", "OT", 1_300_000),
    ("Brice Pollock", "CB", 850_000),
    ("Sheridan Wilson", "IOL", 728_000),
    ("Terrance Carter", "TE", 692_000),
    ("Micah Hudson", "WR", 590_000),
    ("Austin Romaine", "LB", 558_000),
    ("Cameron Dickey", "RB", 541_000),
    ("Jacob Ponton", "OT", 299_000),
    ("Hunter Zambrano", "OT", 241_000),
    ("Lloyd Jones", "QB", 130_000),
]


def fetch_team_id():
    resp = supabase.table("teams").select("id").eq("university_name", "Texas Tech").execute()
    rows = resp.data or []
    if not rows:
        print("[ERROR] Team 'Texas Tech' not found.")
        sys.exit(1)
    return str(rows[0]["id"])


def fetch_players(team_id):
    all_players = []
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, position, cfo_valuation, player_tag, roster_status")
            .eq("team_id", team_id)
            .eq("player_tag", "College Athlete")
            .range(offset, offset + 999)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return [p for p in all_players if (p.get("roster_status") or "active") == "active"]


def match_players(on3_data, db_players):
    matched = []
    unmatched_on3 = []
    db_used = set()
    remaining = list(db_players)

    for on3_name, on3_pos, on3_val in on3_data:
        result = fuzzy_match_player(on3_name, remaining, threshold=0.85)
        if result is not None:
            player = result.player
            pid = str(player["id"])
            if result.method != "exact":
                print(f"  [{result.method}] '{on3_name}' -> '{player['name']}' ({result.score:.2f})")
            matched.append({
                "name": player["name"],
                "position": on3_pos,
                "cfo_valuation": player.get("cfo_valuation"),
                "on3_valuation": on3_val,
            })
            db_used.add(pid)
            remaining = [p for p in remaining if str(p["id"]) != pid]
        else:
            print(f"  [UNMATCHED] On3 player not in DB: {on3_name} ({on3_pos})")
            unmatched_on3.append({
                "name": f"{on3_name} (NOT IN DB)",
                "position": on3_pos,
                "cfo_valuation": None,
                "on3_valuation": on3_val,
            })

    unmatched_db = []
    for p in db_players:
        if str(p["id"]) not in db_used:
            unmatched_db.append({
                "name": p["name"],
                "position": p.get("position") or "",
                "cfo_valuation": p.get("cfo_valuation"),
                "on3_valuation": None,
            })

    return matched, unmatched_on3, unmatched_db


def write_csv(matched, unmatched_on3, unmatched_db):
    matched.sort(key=lambda x: x["on3_valuation"] or 0, reverse=True)
    unmatched_db.sort(key=lambda x: x["cfo_valuation"] or 0, reverse=True)
    unmatched_on3.sort(key=lambda x: x["on3_valuation"] or 0, reverse=True)
    all_rows = matched + unmatched_db + unmatched_on3

    os.makedirs(os.path.dirname(CSV_OUT), exist_ok=True)
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Player", "Position", "CFO Valuation", "On3 Valuation", "Override Value"])
        for row in all_rows:
            writer.writerow([
                row["name"],
                row["position"],
                row["cfo_valuation"] if row["cfo_valuation"] is not None else "",
                row["on3_valuation"] if row["on3_valuation"] is not None else "",
                "",
            ])
    return all_rows


def main():
    print("=" * 70)
    print("  TEXAS TECH COMPARISON: CFO vs On3 Valuations")
    print("=" * 70)

    print("\nStep 1: Fetching Texas Tech players from Supabase...")
    team_id = fetch_team_id()
    print(f"  Texas Tech team_id: {team_id}")
    db_players = fetch_players(team_id)
    print(f"  {len(db_players)} active College Athletes found.\n")

    print(f"Step 2: On3 data loaded -- {len(ON3_DATA)} players.\n")

    print("Step 3: Matching On3 players to DB...")
    matched, unmatched_on3, unmatched_db = match_players(ON3_DATA, db_players)

    print(f"\nStep 4: Generating CSV...")
    all_rows = write_csv(matched, unmatched_on3, unmatched_db)

    print(f"\n{'=' * 70}")
    print(f"  SUMMARY")
    print(f"{'=' * 70}")
    print(f"  On3 players:           {len(ON3_DATA)}")
    print(f"  DB players (active):   {len(db_players)}")
    print(f"  Matched:               {len(matched)}")
    print(f"  On3 not in DB:         {len(unmatched_on3)}")
    print(f"  DB not in On3:         {len(unmatched_db)}")
    print(f"  Total CSV rows:        {len(all_rows)}")
    print(f"\n  CSV saved to: {CSV_OUT}")
    print(f"  -> Fill in the 'Override Value' column for players that need overrides.")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
