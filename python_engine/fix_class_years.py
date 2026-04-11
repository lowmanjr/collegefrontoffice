"""
fix_class_years.py
-------------------
Populates class_year (integer 1-5) for active College Athletes who have NULL.
Matches by team + fuzzy name against CFBD roster data (doesn't require cfbd_id).

CFBD year field: 1=FR, 2=SO, 3=JR, 4=SR, 5+=GR → maps directly to our 1-5 integers.

Captures before/after snapshot of all valuations to measure impact.

Usage:
    python fix_class_years.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import re
import time
import unicodedata
import requests
from collections import defaultdict
from difflib import SequenceMatcher
from supabase_client import supabase

CFBD_API_KEY = os.getenv("CFBD_API_KEY")
if not CFBD_API_KEY:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))
    CFBD_API_KEY = os.getenv("CFBD_API_KEY")

CFBD_HEADERS = {"Authorization": f"Bearer {CFBD_API_KEY}", "Accept": "application/json"}
CFBD_ROSTER_URL = "https://api.collegefootballdata.com/roster"
CFBD_YEAR = 2025


def normalize(name):
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


def main():
    print("=" * 70)
    print("  FIX CLASS YEARS: Populate NULLs via CFBD team+name matching")
    print("=" * 70)

    # Step 1: Fetch teams
    tresp = supabase.table("teams").select("id, university_name").execute()
    teams = {t["id"]: t["university_name"] for t in (tresp.data or [])}
    team_id_by_name = {t["university_name"]: t["id"] for t in (tresp.data or [])}
    print(f"  {len(teams)} teams loaded.\n")

    # Step 2: Fetch all active CAs with NULL class_year
    target = []
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, team_id, class_year, is_on_depth_chart, cfo_valuation")
            .eq("player_tag", "College Athlete")
            .eq("roster_status", "active")
            .is_("class_year", "null")
            .range(offset, offset + 999)
            .execute()
        )
        batch = resp.data or []
        target.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    on_dc = [p for p in target if p.get("is_on_depth_chart")]
    print(f"  {len(target):,} active CAs with NULL class_year")
    print(f"  {len(on_dc):,} of those are on depth chart (valuation impact)\n")

    # Step 3: Snapshot all current valuations for before/after comparison
    print("  Snapshotting current valuations...")
    before_vals = {}
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select("id, cfo_valuation")
            .eq("player_tag", "College Athlete")
            .eq("roster_status", "active")
            .range(offset, offset + 999)
            .execute()
        )
        batch = resp.data or []
        for p in batch:
            if p.get("cfo_valuation"):
                before_vals[p["id"]] = p["cfo_valuation"]
        if len(batch) < 1000:
            break
        offset += 1000
    print(f"  {len(before_vals):,} valuations snapshotted.\n")

    # Step 4: Fetch CFBD rosters per team and build name -> year dict
    print("  Fetching CFBD rosters...")
    # Group targets by team
    targets_by_team = defaultdict(list)
    for p in target:
        tid = p.get("team_id")
        if tid:
            targets_by_team[tid].append(p)

    updated = 0
    unmatched = 0
    errors = 0

    for team_id, team_players in targets_by_team.items():
        team_name = teams.get(team_id, "")
        if not team_name:
            continue

        # Fetch CFBD roster for this team
        try:
            r = requests.get(
                CFBD_ROSTER_URL,
                headers=CFBD_HEADERS,
                params={"year": CFBD_YEAR, "team": team_name},
                timeout=20,
            )
            r.raise_for_status()
            cfbd_roster = r.json()
        except requests.RequestException:
            cfbd_roster = []

        # Build name -> year dict from CFBD roster
        cfbd_lookup = {}
        for cr in cfbd_roster:
            name = (cr.get("firstName", "") + " " + cr.get("lastName", "")).strip()
            year_int = cr.get("year")
            if name and year_int is not None:
                cfbd_lookup[normalize(name)] = min(int(year_int), 5)  # cap at 5

        if not cfbd_lookup:
            unmatched += len(team_players)
            time.sleep(0.5)
            continue

        cfbd_keys = list(cfbd_lookup.keys())

        # Match each target player
        for p in team_players:
            pname = p.get("name", "")
            pnorm = normalize(pname)

            # Exact match first
            year_val = cfbd_lookup.get(pnorm)
            match_type = "exact"

            # Fuzzy fallback
            if year_val is None:
                best_score = 0
                best_key = None
                for ck in cfbd_keys:
                    score = fuzzy_score(pname, ck)
                    if score > best_score:
                        best_score = score
                        best_key = ck
                if best_key and best_score >= 0.85:
                    year_val = cfbd_lookup[best_key]
                    match_type = f"fuzzy ({best_score:.2f})"

            if year_val is not None:
                try:
                    supabase.table("players").update(
                        {"class_year": year_val}
                    ).eq("id", p["id"]).execute()
                    updated += 1
                except Exception:
                    errors += 1
            else:
                unmatched += 1

        time.sleep(0.5)

    print(f"\n  Updated:   {updated:,}")
    print(f"  Unmatched: {unmatched:,}")
    print(f"  Errors:    {errors}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
