"""Quick post-enrichment diagnostic: before/after counts + Michael Terry III walkthrough."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
from supabase_client import supabase

# Fetch all active College Athletes
all_p = []
offset = 0
while True:
    resp = (
        supabase.table("players")
        .select("id, name, position, star_rating, class_year, depth_chart_rank, "
                "cfo_valuation, is_on_depth_chart, team_id")
        .eq("player_tag", "College Athlete")
        .eq("roster_status", "active")
        .range(offset, offset + 999)
        .execute()
    )
    batch = resp.data or []
    all_p.extend(batch)
    if len(batch) < 1000:
        break
    offset += 1000

total = len(all_p)
no_star = [p for p in all_p if not p.get("star_rating") or p["star_rating"] == 0]
no_class = [p for p in all_p if p.get("class_year") is None]
both = [p for p in all_p if (not p.get("star_rating") or p["star_rating"] == 0) and p.get("class_year") is None]
no_star_dc = [p for p in no_star if p.get("is_on_depth_chart")]
no_class_dc = [p for p in no_class if p.get("is_on_depth_chart")]

print("=" * 70)
print("  BEFORE / AFTER ENRICHMENT COMPARISON")
print("=" * 70)
print(f"  Total active College Athletes: {total:,}")
print()
print(f"  {'METRIC':<40} {'BEFORE':>10} {'AFTER':>10} {'FIXED':>10}")
print("  " + "-" * 62)
print(f"  {'star_rating = 0/NULL':<40} {'10,876':>10} {len(no_star):>10,} {10876 - len(no_star):>10,}")
print(f"  {'class_year = NULL':<40} {'10,583':>10} {len(no_class):>10,} {10583 - len(no_class):>10,}")
print(f"  {'Both missing':<40} {'10,570':>10} {len(both):>10,} {10570 - len(both):>10,}")
print(f"  {'star gap + on depth chart':<40} {'3,582':>10} {len(no_star_dc):>10,} {3582 - len(no_star_dc):>10,}")
print(f"  {'class gap + on depth chart':<40} {'3,464':>10} {len(no_class_dc):>10,} {3464 - len(no_class_dc):>10,}")
print()
pct_star = (total - len(no_star)) / total * 100
pct_class = (total - len(no_class)) / total * 100
print(f"  star_rating coverage: {pct_star:.1f}% (was 4.2%)")
print(f"  class_year coverage:  {pct_class:.1f}% (was 6.8%)")

# Michael Terry III
print(f"\n\n{'=' * 70}")
print("  MICHAEL TERRY III -- POST-ENRICHMENT")
print(f"{'=' * 70}")

resp = supabase.table("players").select(
    "id, name, position, player_tag, star_rating, class_year, composite_score, "
    "cfo_valuation, is_override, is_on_depth_chart, depth_chart_rank, "
    "nfl_draft_projection, production_score, ea_rating, total_followers, "
    "hs_grad_year, team_id"
).eq("name", "Michael Terry III").execute()
r = resp.data[0]

tresp = supabase.table("teams").select("university_name, market_multiplier").eq("id", r["team_id"]).execute()
team = tresp.data[0]
mkt = float(team["market_multiplier"])

star = r.get("star_rating") or 0
cy = r.get("class_year")
prod = float(r.get("production_score") or 0)
ea = r.get("ea_rating")
draft = r.get("nfl_draft_projection")
dc = r.get("depth_chart_rank")
followers = r.get("total_followers") or 0
val = r.get("cfo_valuation")

print(f"  position:             {r['position']}")
print(f"  star_rating:          {star}  (was 0)")
print(f"  class_year:           {cy}  (was NULL)")
print(f"  depth_chart_rank:     {dc}")
print(f"  nfl_draft_projection: {draft}")
print(f"  production_score:     {prod}")
print(f"  ea_rating:            {ea}")
print(f"  total_followers:      {followers:,}")
print(f"  market_multiplier:    {mkt}")
if val:
    print(f"  cfo_valuation:        ${val:,}")
else:
    print(f"  cfo_valuation:        NULL")

print(f"\n  V3.5 FORMULA WALKTHROUGH:")
print(f"  -------------------------")

pos_base = 550_000
print(f"  1. Position base (WR):           $550,000")

draft_mult = 1.0
print(f"  2. Draft premium:                1.0x  (sentinel {draft})")

# Talent modifier
if prod > 0:
    if prod >= 90: tm = 1.4
    elif prod >= 75: tm = 1.2
    elif prod >= 50: tm = 1.0
    elif prod >= 25: tm = 0.65
    else: tm = 0.4
    tm_label = f"Production {prod}"
elif ea and int(ea) > 0:
    eav = int(ea)
    if eav >= 90: tm = 1.4
    elif eav >= 82: tm = 1.2
    elif eav >= 75: tm = 1.0
    elif eav >= 68: tm = 0.65
    else: tm = 0.4
    tm_label = f"EA Rating {eav} (fallback)"
elif star >= 5: tm, tm_label = 1.15, "5-star proxy"
elif star == 4: tm, tm_label = 1.0, "4-star proxy"
elif star == 3: tm, tm_label = 0.9, "3-star proxy"
elif star >= 1: tm, tm_label = 0.8, f"{star}-star proxy"
else: tm, tm_label = 1.0, "No talent data (neutral)"
print(f"  3. Talent modifier:              {tm}x  ({tm_label})")

print(f"  4. Market multiplier (Texas):    {mkt}x")

# Experience
exp_map = {1: (0.90, "Freshman"), 2: (1.00, "Sophomore"), 3: (1.10, "Junior"),
           4: (1.15, "Senior"), 5: (1.20, "Super Senior")}
if cy is not None:
    try:
        cy_int = int(cy)
        exp, exp_label = exp_map.get(cy_int, (1.0, f"Year {cy_int}"))
    except (ValueError, TypeError):
        exp, exp_label = 1.0, f"class_year={cy}"
else:
    exp, exp_label = 1.0, "Unknown year"
print(f"  5. Experience multiplier:        {exp}x  ({exp_label})")

# DC rank
starter_count = 3  # WR
if dc and dc <= starter_count:
    dc_mult, dc_label = 1.0, f"Starter ({dc} of {starter_count})"
elif dc:
    backup = dc - starter_count
    if backup == 1: dc_mult = 0.55
    elif backup == 2: dc_mult = 0.40
    else: dc_mult = 0.25
    dc_label = f"Backup {backup} (multi-starter)"
else:
    dc_mult, dc_label = 0.55, "Unknown rank"
print(f"  6. Depth chart rank:             {dc_mult}x  ({dc_label})")

soc = min(followers, 150_000)
print(f"  7. Social premium:               ${soc:,}  ({followers:,} followers)")

football = pos_base * draft_mult * tm * mkt * exp * dc_mult
total_val = max(int(football + soc), 10_000)
print(f"\n  MATH:")
print(f"    football = $550,000 x {draft_mult} x {tm} x {mkt} x {exp} x {dc_mult}")
print(f"             = ${int(football):,}")
print(f"    cfo_val  = max(floor(${int(football):,} + ${soc:,}), $10,000)")
print(f"             = ${total_val:,}")
if val:
    print(f"\n    Stored:    ${val:,}")
    match = "YES" if val == total_val else f"NO ({val} vs {total_val})"
    print(f"    Match:     {match}")
else:
    print(f"\n    Stored:    NULL")
print(f"\n    On3:       $177,000")
if total_val:
    print(f"    Ratio:     {total_val/177000:.1f}x CFO / On3")
print(f"    Previous:  $720,128 (was {720128/177000:.1f}x On3)")
print(f"    Delta:     ${720128 - total_val:+,} ({(total_val - 720128)/720128*100:+.1f}%)")
print(f"{'=' * 70}")
