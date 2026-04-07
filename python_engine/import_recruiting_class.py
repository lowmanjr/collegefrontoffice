"""
import_recruiting_class.py
---------------------------
Imports recruiting class data from CFBD API into our players table.

Usage:
    python import_recruiting_class.py --year 2026 --min-stars 4
    python import_recruiting_class.py --year 2027 --min-stars 4
    python import_recruiting_class.py --year 2026 --min-stars 3  # include 3-stars

After running, execute: python calculate_cfo_valuations.py
"""
import sys; sys.stdout.reconfigure(encoding="utf-8")

import os
import csv
import argparse
import time
import unicodedata
import re
import requests
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from supabase_client import supabase
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))
CFBD_API_KEY = os.getenv("CFBD_API_KEY")
CFBD_HEADERS = {"Authorization": f"Bearer {CFBD_API_KEY}"}
CFBD_BASE = "https://api.collegefootballdata.com"


def norm(name):
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    return " ".join(re.sub(r"[^a-z0-9 ]", "", ascii_name.lower()).split())


def fuzzy(a, b):
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def load_teams():
    resp = supabase.table("teams").select("id, university_name").execute()
    team_map = {}
    for t in (resp.data or []):
        team_map[norm(t["university_name"])] = t["id"]
        # Also add common short names
        name = t["university_name"]
        team_map[norm(name)] = t["id"]
    return team_map


def fetch_existing_hs(year):
    """Fetch existing HS recruits for this grad year."""
    all_p = []
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, position, star_rating, composite_score, hs_grad_year")
            .eq("player_tag", "High School Recruit")
            .eq("hs_grad_year", year)
            .range(offset, offset + 999)
            .execute()
        )
        batch = resp.data or []
        all_p.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return all_p


def fetch_cfbd_recruits(year):
    try:
        resp = requests.get(f"{CFBD_BASE}/recruiting/players",
                            headers=CFBD_HEADERS, params={"year": year}, timeout=30)
        if resp.status_code == 200:
            return resp.json() or []
        print(f"  [API ERROR] Status {resp.status_code}")
        return []
    except Exception as e:
        print(f"  [API ERROR] {e}")
        return []


def match_committed_school(committed_to, team_map):
    """Try to match CFBD committedTo field to one of our 16 teams."""
    if not committed_to:
        return None
    ct = norm(committed_to)
    # Exact match
    if ct in team_map:
        return team_map[ct]
    # Fuzzy match
    for tname, tid in team_map.items():
        if fuzzy(ct, tname) >= 0.85:
            return tid
    return None


def load_csv_recruits(csv_path):
    """Load recruits from a CSV file. Returns list of dicts with CFBD-compatible keys."""
    recruits = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("name") or "").strip()
            if not name:
                continue
            stars = int(row.get("star_rating") or row.get("stars") or 0)
            comp = row.get("composite_score") or row.get("rating") or None
            if comp:
                try:
                    comp = float(comp)
                except ValueError:
                    comp = None
            recruits.append({
                "name": name,
                "position": (row.get("position") or "").strip() or None,
                "stars": stars,
                "rating": comp,
                "committedTo": (row.get("committed_school") or row.get("committedTo") or "").strip() or None,
            })
    return recruits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True, help="Recruiting class year (e.g., 2027)")
    parser.add_argument("--min-stars", type=int, default=4, help="Minimum star rating to import (default: 4)")
    parser.add_argument("--csv", type=str, default=None, help="Path to CSV file (instead of CFBD API)")
    args = parser.parse_args()

    year = args.year
    min_stars = args.min_stars

    print("=" * 80)
    print(f"  IMPORT RECRUITING CLASS {year} (min {min_stars}-star)")
    print("=" * 80)

    # Load our teams
    team_map = load_teams()

    # Fetch data from CSV or CFBD
    if args.csv:
        print(f"\n  Loading from CSV: {args.csv}")
        all_data = load_csv_recruits(args.csv)
        if not all_data:
            print(f"  No data in CSV. Exiting.")
            return
        print(f"  Total CSV records: {len(all_data)}")
    else:
        print(f"\n  Fetching CFBD recruiting data for {year}...")
        all_data = fetch_cfbd_recruits(year)
        if not all_data:
            print(f"  No CFBD data available for {year}. Exiting.")
            return
        print(f"  Total CFBD records: {len(all_data)}")

    # Filter by star rating
    eligible = [r for r in all_data if (r.get("stars") or 0) >= min_stars]
    print(f"  Eligible ({min_stars}+ stars): {len(eligible)}")

    star_dist = Counter(r.get("stars") for r in eligible)
    for s in sorted(star_dist.keys(), reverse=True):
        print(f"    {s}-star: {star_dist[s]}")

    # Load existing HS recruits for this year
    existing = fetch_existing_hs(year)
    existing_norms = {norm(p["name"]): p for p in existing}
    print(f"\n  Existing {year} recruits in DB: {len(existing)}")

    # Process each recruit
    inserted = 0
    updated = 0
    skipped = 0
    errors = 0
    team_counts = Counter()
    pos_counts = Counter()
    star_counts = Counter()

    for r in eligible:
        name = (r.get("name") or "").strip()
        if not name:
            continue

        stars = r.get("stars") or 0
        rating = r.get("rating") or None  # composite score (0-1 scale)
        position = (r.get("position") or "").strip() or None
        committed = r.get("committedTo")
        cfbd_recruit_id = r.get("id")

        # Convert rating from 0-1 scale to our format if needed
        composite = float(rating) if rating else None

        # Match to our team
        team_id = match_committed_school(committed, team_map)

        # Check if already exists
        n = norm(name)
        existing_player = existing_norms.get(n)

        # Also try fuzzy match
        if not existing_player:
            for en, ep in existing_norms.items():
                if fuzzy(n, en) >= 0.90:
                    existing_player = ep
                    break

        if existing_player:
            # Update existing record with better data
            update_data = {}
            if composite and not existing_player.get("composite_score"):
                update_data["composite_score"] = composite
            if stars and (not existing_player.get("star_rating") or stars > existing_player["star_rating"]):
                update_data["star_rating"] = stars
            if position and not existing_player.get("position"):
                update_data["position"] = position

            if update_data:
                try:
                    supabase.table("players").update(update_data).eq("id", existing_player["id"]).execute()
                    updated += 1
                except Exception as e:
                    errors += 1
            else:
                skipped += 1
            continue

        # Insert new recruit
        new_player = {
            "name": name,
            "position": position,
            "star_rating": stars,
            "composite_score": composite,
            "player_tag": "High School Recruit",
            "hs_grad_year": year,
            "experience_level": "High School",
            "is_public": True,
            "status": "Active",
            "roster_status": "active",
            "is_on_depth_chart": False,
            "is_override": False,
            "team_id": team_id,
        }

        try:
            supabase.table("players").insert(new_player).execute()
            inserted += 1
            star_counts[stars] += 1
            pos_counts[position or "NULL"] += 1
            if team_id:
                team_counts[team_id] += 1
        except Exception as e:
            # Likely duplicate or constraint violation
            errors += 1

    # Summary
    print(f"\n{'=' * 80}")
    print(f"  IMPORT SUMMARY — CLASS OF {year}")
    print(f"{'=' * 80}")
    print(f"  New recruits inserted: {inserted}")
    print(f"  Existing updated:      {updated}")
    print(f"  Skipped (no change):   {skipped}")
    print(f"  Errors:                {errors}")

    if star_counts:
        print(f"\n  New recruits by star rating:")
        for s in sorted(star_counts.keys(), reverse=True):
            print(f"    {s}-star: {star_counts[s]}")

    if pos_counts:
        print(f"\n  New recruits by position:")
        for p in sorted(pos_counts.keys()):
            print(f"    {p:<8} {pos_counts[p]}")

    # Get team names for display
    teams_resp = supabase.table("teams").select("id, university_name").execute()
    team_names = {t["id"]: t["university_name"] for t in (teams_resp.data or [])}

    our_team_count = sum(team_counts.values())
    other_count = inserted - our_team_count
    print(f"\n  Committed to our 16 teams: {our_team_count}")
    print(f"  Other schools / uncommitted: {other_count}")

    if team_counts:
        print(f"\n  By team:")
        for tid in sorted(team_counts.keys(), key=lambda x: -team_counts[x]):
            print(f"    {team_names.get(tid, '?'):<22} {team_counts[tid]:>4}")

    print(f"\n  Next step: Run 'python calculate_cfo_valuations.py' to generate valuations.")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
