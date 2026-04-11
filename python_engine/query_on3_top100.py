"""Query On3 Top 100 football players against Supabase CFO valuations."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
from supabase_client import supabase
from name_utils import fuzzy_match_player

# Fetch all players + teams
all_p = []
offset = 0
while True:
    resp = supabase.table("players").select(
        "id, name, position, team_id, cfo_valuation, is_override"
    ).range(offset, offset + 999).execute()
    batch = resp.data or []
    all_p.extend(batch)
    if len(batch) < 1000: break
    offset += 1000

tresp = supabase.table("teams").select("id, university_name").execute()
teams = {t["university_name"]: t["id"] for t in (tresp.data or [])}
team_names = {t["id"]: t["university_name"] for t in (tresp.data or [])}

ON3 = [
    ("Arch Manning", "Texas", "QB", 5400000),
    ("Jeremiah Smith", "Ohio State", "WR", 4200000),
    ("Sam Leavitt", "LSU", "QB", 4000000),
    ("Brendan Sorsby", "Texas Tech", "QB", 3100000),
    ("Bryce Underwood", "Michigan", "QB", 3100000),
    ("Dante Moore", "Oregon", "QB", 3000000),
    ("Cam Coleman", "Texas", "WR", 2900000),
    ("LaNorris Sellers", "South Carolina", "QB", 2700000),
    ("Drew Mestemaker", "Oklahoma State", "QB", 2500000),
    ("Dylan Stewart", "South Carolina", "EDGE", 2500000),
    ("Julian Sayin", "Ohio State", "QB", 2400000),
    ("Josh Hoover", "Indiana", "QB", 2300000),
    ("Darian Mensah", "Miami", "QB", 2200000),
    ("Jayden Maiava", "USC", "QB", 2200000),
    ("Mason Heintschel", "Pittsburgh", "QB", 2100000),
    ("CJ Bailey", "NC State", "QB", 2100000),
    ("John Mateer", "Oklahoma", "QB", 2000000),
    ("Jackson Cantwell", "Miami", "OT", 1900000),
    ("David Stone", "Oklahoma", "DL", 1900000),
    ("Malik Washington", "Maryland", "QB", 1900000),
    ("Byrum Brown", "Auburn", "QB", 1900000),
    ("Jaron-Keawe Sagapolutele", "Cal", "QB", 1800000),
    ("Jordan Seaton", "LSU", "OT", 1700000),
    ("Jared Curtis", "Vanderbilt", "QB", 1700000),
    ("Ryan Coleman-Williams", "Alabama", "WR", 1600000),
    ("Trinidad Chambliss", "Ole Miss", "QB", 1600000),
    ("Colin Simmons", "Texas", "EDGE", 1500000),
    ("Evan Stewart", "Oregon", "WR", 1500000),
    ("Conner Weigman", "Houston", "QB", 1500000),
    ("Princewill Umanmielen", "LSU", "EDGE", 1400000),
    ("Rocco Becht", "Penn State", "QB", 1400000),
    ("Ryan Wingo", "Texas", "WR", 1400000),
    ("Noah Fifita", "Arizona", "QB", 1400000),
    ("Duce Robinson", "Florida State", "WR", 1300000),
    ("Malachi Toney", "Miami", "WR", 1300000),
    ("Dylan Raiola", "Oregon", "QB", 1300000),
    ("Chaz Coleman", "Tennessee", "EDGE", 1300000),
    ("Damon Wilson II", "Miami", "EDGE", 1300000),
    ("Keelon Russell", "Alabama", "QB", 1300000),
    ("Howard Sampson", "Texas Tech", "OT", 1300000),
    ("Gunner Stockton", "Georgia", "QB", 1300000),
    ("Bear Alexander", "Oregon", "DL", 1200000),
    ("Carter Smith", None, "OT", 1200000),
    ("Mark Bowman", "USC", "TE", 1200000),
    ("Cayden Green", "Missouri", "OT", 1200000),
]

results = []
not_found = []

for name, team, pos, on3_val in ON3:
    team_id = teams.get(team) if team else None
    result = fuzzy_match_player(name, all_p, team_filter=team_id, threshold=0.80)

    # If team-scoped search fails, try global
    if result is None and team_id:
        result = fuzzy_match_player(name, all_p, threshold=0.80)

    if result:
        p = result.player
        cfo = p.get("cfo_valuation")
        p_team = team_names.get(p.get("team_id", ""), "???")
        ovr = " OVR" if p.get("is_override") else ""
        results.append({
            "name": name, "team": team or "???", "pos": pos,
            "on3": on3_val, "cfo": cfo, "ratio": cfo / on3_val if cfo else None,
            "ovr": ovr, "method": result.method,
        })
    else:
        not_found.append({"name": name, "team": team or "???", "pos": pos, "on3": on3_val})

# Print table
print("=" * 115)
print("  ON3 TOP 100 (FOOTBALL) vs CFO VALUATIONS")
print("=" * 115)
print(f"  {'RK':>3} {'PLAYER':<28} {'TEAM':<18} {'POS':<5} {'ON3':>12} {'CFO':>12} {'RATIO':>7} {'NOTE'}")
print("  " + "-" * 113)

for i, r in enumerate(results, 1):
    on3_s = f"${r['on3']:,}"
    cfo_s = f"${r['cfo']:,}" if r['cfo'] else "NULL"
    ratio_s = f"{r['ratio']:.2f}x" if r['ratio'] else "-"
    print(f"  {i:>3} {r['name']:<28} {r['team']:<18} {r['pos']:<5} {on3_s:>12} {cfo_s:>12} {ratio_s:>7} {r['ovr']}")

if not_found:
    print(f"\n  NOT FOUND IN DB ({len(not_found)}):")
    for nf in not_found:
        print(f"    {nf['name']:<28} {nf['team']:<18} {nf['pos']:<5} ${nf['on3']:,}")

# Summary stats
ratios = [r["ratio"] for r in results if r["ratio"] is not None]
if ratios:
    ratios_sorted = sorted(ratios)
    median = ratios_sorted[len(ratios_sorted)//2]
    avg = sum(ratios) / len(ratios)
    above = sum(1 for r in ratios if r >= 1.0)
    below = sum(1 for r in ratios if r < 1.0)

    print(f"\n  SUMMARY STATS:")
    print(f"    Players matched:    {len(results)}/{len(ON3)}")
    print(f"    Players not found:  {len(not_found)}")
    print(f"    Average CFO/On3:    {avg:.2f}x")
    print(f"    Median CFO/On3:     {median:.2f}x")
    print(f"    CFO >= On3 (>=1.0x): {above}")
    print(f"    CFO < On3 (<1.0x):  {below}")
    print(f"    Min ratio:          {min(ratios):.2f}x")
    print(f"    Max ratio:          {max(ratios):.2f}x")
print("=" * 115)
