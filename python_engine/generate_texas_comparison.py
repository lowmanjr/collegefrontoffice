"""
generate_texas_comparison.py
----------------------------
Generates a comparison CSV of CFO valuations vs On3 NIL valuations for Texas.
Queries Supabase for active College Athletes, matches against On3 data,
and outputs a CSV with an empty Override Value column for manual review.

Usage:
    python generate_texas_comparison.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import csv
import re
import unicodedata
from difflib import SequenceMatcher
from supabase_client import supabase

CSV_OUT = os.path.join(os.path.dirname(__file__), "data", "texas_comparison.csv")

# ─── On3 NIL data for Texas (April 2026) ────────────────────────────────────
# Pre-parsed from On3 team rankings page.
# Format: (name, position, on3_valuation_dollars)

ON3_DATA = [
    ("Arch Manning", "QB", 5_400_000),
    ("Cam Coleman", "WR", 2_900_000),
    ("Colin Simmons", "EDGE", 1_500_000),
    ("Ryan Wingo", "WR", 1_400_000),
    ("Trevor Goosby", "OT", 1_000_000),
    ("Justus Terry", "DL", 825_000),
    ("Hero Kanu", "DL", 655_000),
    ("Rasheem Biles", "LB", 595_000),
    ("Melvin Siani", "OT", 565_000),
    ("Hollywood Smothers", "RB", 550_000),
    ("Raleek Brown", "RB", 535_000),
    ("Jonah Williams", "S", 442_000),
    ("Brandon Baker", "OT", 440_000),
    ("Kaliq Lockett", "WR", 425_000),
    ("Kade Phillips", "CB", 422_000),
    ("Lance Jackson", "EDGE", 328_000),
    ("Jelani McDonald", "S", 304_000),
    ("CJ Baxter", "RB", 275_000),
    ("Morice Blackwell", "LB", 274_000),
    ("Gavin Holmes", "CB", 266_000),
    ("K.J. Lacey", "QB", 236_000),
    ("Jett Bush", "LB", 232_000),
    ("Jaime Ffrench", "WR", 214_000),
    ("Jahleel Billingsley", "TE", 206_000),
    ("Aaron Butler", "WR", 180_000),
    ("Graceson Littleton", "CB", 179_000),
    ("Michael Terry III", "WR", 177_000),
    ("Jerrick Gibson", "RB", 172_000),
    ("Kobe Black", "CB", 170_000),
    ("James Simon", "RB", 167_000),
    ("Trey Owens", "QB", 167_000),
    ("Xavier Filsaime", "S", 166_000),
    ("Zelus Hicks", "S", 165_000),
    ("Jordon Johnson-Rubell", "S", 164_000),
    ("Daylan McCutcheon", "WR", 162_000),
    ("Parker Livingstone", "WR", 161_000),
    ("Wardell Mack", "CB", 161_000),
    ("Zina Umeozulu", "EDGE", 159_000),
    ("Jordan Washington", "TE", 159_000),
    ("Christian Clark", "RB", 158_000),
    ("Tyanthony Smith", "LB", 157_000),
    ("Smith Orogbo", "EDGE", 156_000),
    ("Nick Townsend", "TE", 155_000),
    ("Daniel Cruz", "IOL", 150_000),
    ("Myron Charles", "DL", 149_000),
    ("Josiah Sharma", "DL", 148_000),
    ("Warren Roberson", "CB", 144_000),
    ("Colton Vasek", "EDGE", 111_000),
    ("DeAndre Moore Jr.", "WR", 110_000),
]


# ─── Name normalization ─────────────────────────────────────────────────────

def normalize(name):
    """Lowercase, strip suffixes (Jr./III/II/IV), remove periods/apostrophes/hyphens."""
    if not name:
        return ""
    n = unicodedata.normalize("NFKD", name)
    n = n.encode("ascii", "ignore").decode("ascii")
    n = n.lower().strip()
    n = re.sub(r"\b(jr\.?|sr\.?|ii|iii|iv|v)\b", "", n)
    n = n.replace(".", "").replace("'", "").replace("-", " ")
    return " ".join(n.split())


def fuzzy_score(a, b):
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


# ─── Supabase queries ───────────────────────────────────────────────────────

def fetch_texas_team_id():
    resp = (
        supabase.table("teams")
        .select("id")
        .eq("university_name", "Texas")
        .execute()
    )
    rows = resp.data or []
    if not rows:
        print("[ERROR] Team 'Texas' not found in teams table.")
        sys.exit(1)
    return str(rows[0]["id"])


def fetch_texas_players(team_id):
    """Fetch all active College Athlete players for Texas."""
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
    active = [p for p in all_players if (p.get("roster_status") or "active") == "active"]
    return active


# ─── Matching ────────────────────────────────────────────────────────────────

def match_players(on3_data, db_players):
    """Match On3 players to DB players by normalized name, with fuzzy fallback."""
    matched = []
    unmatched_on3 = []
    db_used = set()

    for on3_name, on3_pos, on3_val in on3_data:
        best_match = None
        best_score = 0
        exact = False

        for p in db_players:
            if str(p["id"]) in db_used:
                continue
            db_name = p.get("name", "")
            if normalize(db_name) == normalize(on3_name):
                best_match = p
                exact = True
                break
            score = fuzzy_score(on3_name, db_name)
            if score > best_score:
                best_score = score
                best_match = p

        if exact or (best_match and best_score >= 0.85):
            pid = str(best_match["id"])
            if not exact:
                print(f"  [FUZZY] '{on3_name}' -> '{best_match['name']}' ({best_score:.2f})")
            matched.append({
                "name": best_match["name"],
                "position": on3_pos,
                "cfo_valuation": best_match.get("cfo_valuation"),
                "on3_valuation": on3_val,
            })
            db_used.add(pid)
        else:
            print(f"  [UNMATCHED] On3 player not in DB: {on3_name} ({on3_pos})")
            unmatched_on3.append({
                "name": f"{on3_name} (NOT IN DB)",
                "position": on3_pos,
                "cfo_valuation": None,
                "on3_valuation": on3_val,
            })

    # DB players not matched to any On3 entry
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


# ─── CSV generation ─────────────────────────────────────────────────────────

def write_csv(matched, unmatched_on3, unmatched_db):
    """Write comparison CSV: matched (sorted by On3 desc), then DB-only, then On3-only."""
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


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  TEXAS COMPARISON: CFO vs On3 Valuations")
    print("=" * 70)

    print("\nStep 1: Fetching Texas players from Supabase...")
    team_id = fetch_texas_team_id()
    print(f"  Texas team_id: {team_id}")
    db_players = fetch_texas_players(team_id)
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
