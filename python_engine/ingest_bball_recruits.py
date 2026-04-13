"""
Ingests high school basketball recruits from national CSV files
into basketball_players.

Reads:
  data/basketball_recruits_2026.csv
  data/basketball_recruits_2027.csv
  data/basketball_recruits_2028.csv

For each recruit:
- Sets player_tag = 'High School Recruit'
- Sets acquisition_type = 'recruit'
- Sets hs_grad_year from CSV
- Sets team_id from committed_school_slug (if committed)
- Deduplicates by espn_athlete_id

Usage:
    python ingest_bball_recruits.py
    python ingest_bball_recruits.py --dry-run
    python ingest_bball_recruits.py --year 2026
"""

import csv
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
from supabase_client import supabase

POSITION_MAP = {
    "PG": "PG", "SG": "SG", "SF": "SF", "PF": "PF", "C": "C",
    "G": "SG", "F": "SF", "CG": "SG",
}


def load_teams() -> dict:
    teams = supabase.table("basketball_teams") \
        .select("id, slug, market_multiplier").execute().data
    return {t["slug"]: t for t in teams}


def load_existing_players() -> dict:
    players = supabase.table("basketball_players") \
        .select("id, espn_athlete_id, name").execute().data
    return {p["espn_athlete_id"]: p for p in players if p.get("espn_athlete_id")}


def ingest_csv(filepath: str, teams: dict, existing: dict, dry_run: bool) -> int:
    if not os.path.exists(filepath):
        print(f"  {filepath} not found — skipping")
        return 0

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if not r.get("espn_athlete_id", "").startswith("#")]

    year = int(os.path.basename(filepath).replace("basketball_recruits_", "").replace(".csv", ""))
    print(f"  {os.path.basename(filepath)}: {len(rows)} recruits")

    inserts = []
    updates = []

    for row in rows:
        espn_id = row.get("espn_athlete_id", "").strip()
        if not espn_id:
            continue

        slug = row.get("committed_school_slug", "").strip()
        team = teams.get(slug) if slug else None

        position = POSITION_MAP.get(
            row.get("position_247", "").upper(),
            row.get("position_247") or None,
        )

        record = {
            "name": row["player_name"].strip(),
            "position": position,
            "player_tag": "High School Recruit",
            "acquisition_type": "recruit",
            "hs_grad_year": year,
            "class_year": "Freshman",
            "experience_level": "Freshman",
            "star_rating": int(row["star_rating"]) if row.get("star_rating") else None,
            "composite_score": float(row["composite_score"]) if row.get("composite_score") else None,
            "espn_athlete_id": espn_id,
            "team_id": team["id"] if team else None,
            "roster_status": "active",
            "is_public": True,
        }

        if espn_id in existing:
            record["id"] = existing[espn_id]["id"]
            updates.append(record)
        else:
            inserts.append(record)

    print(f"    Inserts: {len(inserts)}, Updates: {len(updates)}")

    if dry_run:
        for r in (inserts + updates)[:5]:
            team_slug = slug or "uncommitted"
            print(f"    {r['name']:28s} | {str(r['position']):4s} | {r['star_rating']}* | {team_slug}")
        return len(inserts) + len(updates)

    for i in range(0, len(inserts), 50):
        supabase.table("basketball_players").insert(inserts[i : i + 50]).execute()

    for u in updates:
        pid = u.pop("id")
        supabase.table("basketball_players").update(u).eq("id", pid).execute()

    return len(inserts) + len(updates)


def main(dry_run: bool = False, year: int | None = None) -> None:
    teams = load_teams()
    existing = load_existing_players()
    print(f"Loaded {len(teams)} teams, {len(existing)} existing players")

    years = [year] if year else [2026, 2027, 2028]
    total = 0
    for y in years:
        path = f"data/basketball_recruits_{y}.csv"
        print(f"\nProcessing {y} recruits...")
        count = ingest_csv(path, teams, existing, dry_run)
        total += count

    print(f"\nTotal processed: {total}")
    if not dry_run:
        print("Run calculate_bball_valuations.py to price recruits")
        print("Run generate_bball_slugs.py for new player profiles")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    year_arg = None
    for i, arg in enumerate(sys.argv):
        if arg == "--year" and i + 1 < len(sys.argv):
            year_arg = int(sys.argv[i + 1])
    main(dry_run=dry_run, year=year_arg)
