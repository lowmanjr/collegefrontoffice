"""
update_team_markets.py
----------------------
Populates the conference and market_multiplier columns in the Supabase
teams table for all 16 tracked programs.

Multiplier rules:
  SEC / Big Ten   → 1.20
  ACC / Independent → 1.00

Usage:
    python update_team_markets.py

Requirements:
    pip install supabase python-dotenv
"""

import os
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

# ---------------------------------------------------------------------------
# 2. TEAM DICTIONARY  (university_name → conference)
# ---------------------------------------------------------------------------

TEAM_CONFERENCES: dict[str, str] = {
    # SEC
    "Alabama":       "SEC",
    "Georgia":       "SEC",
    "Texas":         "SEC",
    "LSU":           "SEC",
    "Tennessee":     "SEC",
    "Oklahoma":      "SEC",
    "Florida":       "SEC",
    "South Carolina": "SEC",
    # Big Ten
    "Ohio State":    "Big Ten",
    "Oregon":        "Big Ten",
    "Michigan":      "Big Ten",
    "USC":           "Big Ten",
    "Washington":    "Big Ten",
    # ACC
    "Miami":         "ACC",
    "Clemson":       "ACC",
    # Independent
    "Notre Dame":    "Independent",
}

# ---------------------------------------------------------------------------
# 3. MULTIPLIER LOGIC
# ---------------------------------------------------------------------------

MULTIPLIERS: dict[str, float] = {
    "SEC":         1.20,
    "Big Ten":     1.20,
    "ACC":         1.00,
    "Independent": 1.00,
}

# ---------------------------------------------------------------------------
# 4. FETCH ALL TEAMS FROM SUPABASE
# ---------------------------------------------------------------------------

print("Fetching all teams from Supabase...")
resp = supabase.table("teams").select("id, university_name").execute()
teams = resp.data or []
print(f"  {len(teams)} team(s) fetched.\n")

# ---------------------------------------------------------------------------
# 5. MATCH & UPDATE
# ---------------------------------------------------------------------------

updated   = 0
unmatched: list[str] = []

print("=" * 65)
print("Updating conference and market_multiplier...")
print("=" * 65)

for team in teams:
    name = team["university_name"]
    conference = TEAM_CONFERENCES.get(name)

    if conference is None:
        unmatched.append(name)
        continue

    multiplier = MULTIPLIERS[conference]

    supabase.table("teams").update(
        {"conference": conference, "market_multiplier": multiplier}
    ).eq("id", team["id"]).execute()

    print(
        f"  [UPDATED] {name:<20}  conference={conference:<12}  "
        f"market_multiplier={multiplier:.2f}"
    )
    updated += 1

# ---------------------------------------------------------------------------
# 6. SUMMARY
# ---------------------------------------------------------------------------

print(f"\n{'=' * 65}")
print(f"Update complete.")
print(f"  Teams updated   : {updated}")
print(f"  Teams unmatched : {len(unmatched)}")
print(f"  Total teams     : {len(teams)}")

if unmatched:
    print(f"\nUnmatched teams ({len(unmatched)}):")
    for name in sorted(unmatched):
        print(f"  — {name}")
