"""
validate_ea_vs_production.py
------------------------------
Comprehensive comparison report between EA Sports College Football 26 OVR
ratings and CFBD production scores for all players who have both values.

Usage:
    python validate_ea_vs_production.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import math
from collections import Counter, defaultdict
from supabase_client import supabase


# ─── Tier functions (mirror calculate_cfo_valuations.py) ────────────────────

def prod_tier(ps: float) -> tuple[float, str]:
    if ps >= 90: return 1.4, "Elite (1.4x)"
    if ps >= 75: return 1.2, "Strong (1.2x)"
    if ps >= 50: return 1.0, "Average (1.0x)"
    if ps >= 25: return 0.65, "Below Avg (0.65x)"
    return 0.4, "Low (0.4x)"


def ea_tier(ea: int) -> tuple[float, str]:
    if ea >= 90: return 1.4, "Elite (1.4x)"
    if ea >= 82: return 1.2, "Strong (1.2x)"
    if ea >= 75: return 1.0, "Average (1.0x)"
    if ea >= 68: return 0.65, "Below Avg (0.65x)"
    return 0.4, "Low (0.4x)"


def pearson_r(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


# ─── Data fetching ──────────────────────────────────────────────────────────

def fetch_data() -> tuple[list[dict], dict[str, str]]:
    teams_resp = supabase.table("teams").select("id, university_name").execute()
    tnames = {t["id"]: t["university_name"] for t in (teams_resp.data or [])}

    all_p: list[dict] = []
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select(
                "id, name, position, team_id, star_rating, class_year, "
                "ea_rating, production_score, cfo_valuation, "
                "depth_chart_rank, is_on_depth_chart, roster_status"
            )
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

    return all_p, tnames


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    print("=" * 85)
    print("  EA RATING vs PRODUCTION SCORE — VALIDATION REPORT")
    print("=" * 85)

    players, tnames = fetch_data()
    print(f"\n  Active College Athletes loaded: {len(players)}")

    # Players with BOTH values
    both = [
        p for p in players
        if p.get("ea_rating") and int(p["ea_rating"]) > 0
        and p.get("production_score") is not None and float(p["production_score"]) > 0
    ]

    # Players with EA only (for OL section)
    ea_only = [
        p for p in players
        if p.get("ea_rating") and int(p["ea_rating"]) > 0
    ]

    print(f"  Players with both EA rating + production_score > 0: {len(both)}")

    # Compute tiers for each
    for p in both:
        ps = float(p["production_score"])
        ea = int(p["ea_rating"])
        p["_pt_mult"], p["_pt_label"] = prod_tier(ps)
        p["_et_mult"], p["_et_label"] = ea_tier(ea)
        p["_agree"] = p["_pt_mult"] == p["_et_mult"]
        if p["_pt_mult"] == p["_et_mult"]:
            p["_direction"] = "Agree"
        elif p["_et_mult"] > p["_pt_mult"]:
            p["_direction"] = "EA Higher"
        else:
            p["_direction"] = "Prod Higher"

    agree_count = sum(1 for p in both if p["_agree"])

    # ── A. OVERALL STATS ────────────────────────────────────────────────────
    ea_vals = [int(p["ea_rating"]) for p in both]
    ps_vals = [float(p["production_score"]) for p in both]
    corr = pearson_r(ea_vals, ps_vals)

    print(f"\n{'─' * 85}")
    print(f"  A. OVERALL STATS")
    print(f"{'─' * 85}")
    print(f"  Players compared:     {len(both)}")
    print(f"  Same tier (agree):    {agree_count} ({agree_count / len(both) * 100:.1f}%)")
    print(f"  Different tier:       {len(both) - agree_count} ({(len(both) - agree_count) / len(both) * 100:.1f}%)")
    print(f"  Average EA rating:    {sum(ea_vals) / len(ea_vals):.1f}")
    print(f"  Average Prod score:   {sum(ps_vals) / len(ps_vals):.1f}")
    print(f"  Pearson correlation:  {corr:.3f}")

    dir_counts = Counter(p["_direction"] for p in both)
    print(f"\n  Direction of disagreements:")
    print(f"    Agree:         {dir_counts.get('Agree', 0)}")
    print(f"    EA Higher:     {dir_counts.get('EA Higher', 0)}")
    print(f"    Prod Higher:   {dir_counts.get('Prod Higher', 0)}")

    # ── B. AGREEMENT BY POSITION ────────────────────────────────────────────
    print(f"\n{'─' * 85}")
    print(f"  B. AGREEMENT BY POSITION")
    print(f"{'─' * 85}")

    pos_groups: dict[str, list[dict]] = defaultdict(list)
    for p in both:
        pos_groups[p.get("position") or "?"].append(p)

    header = f"  {'Position':<8} {'Count':>5} {'Agree':>6} {'Agree%':>7} {'AvgEA':>6} {'AvgProd':>8} {'EAHi':>5} {'ProdHi':>7}"
    print(header)
    print(f"  {'─' * (len(header) - 2)}")

    for pos in sorted(pos_groups.keys(), key=lambda k: -len(pos_groups[k])):
        grp = pos_groups[pos]
        ag = sum(1 for p in grp if p["_agree"])
        avg_ea = sum(int(p["ea_rating"]) for p in grp) / len(grp)
        avg_ps = sum(float(p["production_score"]) for p in grp) / len(grp)
        ea_hi = sum(1 for p in grp if p["_direction"] == "EA Higher")
        pd_hi = sum(1 for p in grp if p["_direction"] == "Prod Higher")
        pct = ag / len(grp) * 100
        print(f"  {pos:<8} {len(grp):>5} {ag:>6} {pct:>6.1f}% {avg_ea:>6.1f} {avg_ps:>8.1f} {ea_hi:>5} {pd_hi:>7}")

    # ── C. TIER DISAGREEMENTS ───────────────────────────────────────────────
    print(f"\n{'─' * 85}")
    print(f"  C. TIER DISAGREEMENTS (sorted by size of gap)")
    print(f"{'─' * 85}")

    disagree = [p for p in both if not p["_agree"]]
    disagree.sort(key=lambda p: abs(p["_et_mult"] - p["_pt_mult"]), reverse=True)

    header = f"  {'Name':<25} {'Team':<16} {'Pos':<5} {'EA':>3} {'Prod':>5} {'EA Tier':<16} {'Prod Tier':<16} {'Dir':<10}"
    print(header)
    print(f"  {'─' * (len(header) - 2)}")

    for p in disagree[:40]:
        team = tnames.get(p.get("team_id", ""), "?")[:15]
        ps = float(p["production_score"])
        print(
            f"  {p['name']:<25} {team:<16} {p['position'] or '?':<5} "
            f"{p['ea_rating']:>3} {ps:>5.1f} "
            f"{p['_et_label']:<16} {p['_pt_label']:<16} {p['_direction']:<10}"
        )
    if len(disagree) > 40:
        print(f"  ... and {len(disagree) - 40} more")

    # ── D. BIGGEST OUTLIERS ─────────────────────────────────────────────────
    print(f"\n{'─' * 85}")
    print(f"  D. BIGGEST OUTLIERS (EA vs Production, absolute gap)")
    print(f"{'─' * 85}")

    for p in both:
        # EA is 0-99, production is 0-100 — close enough to compare directly
        p["_gap"] = int(p["ea_rating"]) - float(p["production_score"])

    outliers = sorted(both, key=lambda p: abs(p["_gap"]), reverse=True)[:20]

    header = f"  {'Name':<25} {'Team':<16} {'Pos':<5} {'EA':>3} {'Prod':>5} {'Gap':>6} {'Dir':<12} {'CFO Val':>12}"
    print(header)
    print(f"  {'─' * (len(header) - 2)}")

    for p in outliers:
        team = tnames.get(p.get("team_id", ""), "?")[:15]
        val = p.get("cfo_valuation")
        val_s = f"${val:>10,}" if val else f"{'—':>11}"
        gap_s = f"{p['_gap']:>+6.1f}"
        direction = "EA higher" if p["_gap"] > 0 else "Prod higher"
        print(
            f"  {p['name']:<25} {team:<16} {p['position'] or '?':<5} "
            f"{p['ea_rating']:>3} {float(p['production_score']):>5.1f} "
            f"{gap_s} {direction:<12} {val_s}"
        )

    # ── E. OL VALIDATION: EA vs Star Rating ─────────────────────────────────
    print(f"\n{'─' * 85}")
    print(f"  E. OL VALIDATION — EA RATING vs STAR RATING (no production data)")
    print(f"{'─' * 85}")

    ol_ea = [
        p for p in ea_only
        if (p.get("position") or "") in ("OL", "OT", "OG", "C", "IOL")
        and p.get("is_on_depth_chart")
    ]

    star_groups: dict[int, list[int]] = defaultdict(list)
    for p in ol_ea:
        star = p.get("star_rating") or 0
        star_groups[star].append(int(p["ea_rating"]))

    print(f"  OL players with EA rating (on DC): {len(ol_ea)}")
    print()
    print(f"  {'Stars':<8} {'Count':>5} {'Avg EA':>7} {'Min EA':>7} {'Max EA':>7} {'Consistent?':<12}")
    print(f"  {'─' * 50}")

    for star in sorted(star_groups.keys(), reverse=True):
        eas = star_groups[star]
        avg = sum(eas) / len(eas)
        star_s = f"{star}★" if star > 0 else "None"
        consistent = "Yes" if (star >= 4 and avg >= 78) or (star == 3 and 68 <= avg <= 82) or star == 0 else "Check"
        print(f"  {star_s:<8} {len(eas):>5} {avg:>7.1f} {min(eas):>7} {max(eas):>7} {consistent:<12}")

    # ── F. POSITION SUMMARY: Average EA OVR by Position ─────────────────────
    print(f"\n{'─' * 85}")
    print(f"  F. POSITION SUMMARY — AVERAGE EA OVR BY POSITION")
    print(f"{'─' * 85}")

    pos_ea: dict[str, list[int]] = defaultdict(list)
    for p in ea_only:
        if p.get("ea_rating"):
            pos_ea[p.get("position") or "?"].append(int(p["ea_rating"]))

    header = f"  {'Position':<8} {'Count':>5} {'Avg OVR':>8} {'Min':>5} {'Max':>5} {'90+':>5} {'<70':>5}"
    print(header)
    print(f"  {'─' * (len(header) - 2)}")

    for pos in sorted(pos_ea.keys(), key=lambda k: -sum(pos_ea[k]) / len(pos_ea[k])):
        eas = pos_ea[pos]
        avg = sum(eas) / len(eas)
        elite = sum(1 for e in eas if e >= 90)
        low = sum(1 for e in eas if e < 70)
        print(f"  {pos:<8} {len(eas):>5} {avg:>8.1f} {min(eas):>5} {max(eas):>5} {elite:>5} {low:>5}")

    print(f"\n{'=' * 85}")


if __name__ == "__main__":
    main()
