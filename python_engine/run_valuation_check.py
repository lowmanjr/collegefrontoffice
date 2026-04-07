"""
run_valuation_check.py
----------------------
1. Check for players with NULL names
2. Run the V3.1 valuation engine
3. Report results
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
sys.stdout.reconfigure(encoding="utf-8")

from supabase_client import supabase
import calculate_cfo_valuations as engine

# ── 1. NULL name check ────────────────────────────────────────────────────────

print("=" * 65)
print("  STEP 1: NULL NAME CHECK")
print("=" * 65)

resp = supabase.table("players").select("id, player_tag, team_id").is_("name", "null").execute()
null_name_rows = resp.data or []

if null_name_rows:
    print(f"  ⚠  WARNING: {len(null_name_rows)} player(s) have NULL name:")
    for row in null_name_rows:
        print(f"      id={row['id']}  tag={row.get('player_tag')}  team={row.get('team_id')}")
else:
    print("  ✓  No players with NULL name found.\n")

# ── 2. Run valuation engine ───────────────────────────────────────────────────

print("=" * 65)
print("  STEP 2: RUNNING V3.1 VALUATION ENGINE")
print("=" * 65 + "\n")

overrides_map      = engine.fetch_nil_overrides()
multipliers, names = engine.fetch_teams()
players            = engine.fetch_players()

if not players:
    print("No players found. Exiting.")
    sys.exit(1)

results, stats = engine.run_valuations(players, multipliers, names, overrides_map)

# ── 3. Report ─────────────────────────────────────────────────────────────────

print("\n" + "=" * 65)
print("  STEP 3: RESULTS REPORT")
print("=" * 65)
engine.print_summary(results, stats)
