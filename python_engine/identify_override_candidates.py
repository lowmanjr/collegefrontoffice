"""
identify_override_candidates.py
--------------------------------
Screens players for potential NIL override candidates by comparing our
algorithmic CFO valuation against On3 valuations and social following.

Outputs:
  - Formatted report to stdout
  - CSV to python_engine/data/override_candidates.csv

Usage:
    python identify_override_candidates.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import csv
from supabase_client import supabase

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CSV_OUT = os.path.join(DATA_DIR, "override_candidates.csv")


def load_teams():
    resp = supabase.table("teams").select("id, university_name").execute()
    return {t["id"]: t["university_name"] for t in (resp.data or [])}


def fetch_all_players():
    all_p = []
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, position, team_id, on3_valuation, cfo_valuation, "
                    "is_override, total_followers, star_rating, depth_chart_rank, "
                    "production_score, nfl_draft_projection, player_tag")
            .range(offset, offset + 999)
            .execute()
        )
        batch = resp.data or []
        all_p.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return all_p


def fmt(v):
    return f"${v:>11,}" if v else "NULL"


def main():
    teams = load_teams()
    players = fetch_all_players()
    os.makedirs(DATA_DIR, exist_ok=True)

    # ─── Phase 1: Internal screening ─────────────────────────────────────

    candidates = []

    # Sort by cfo_valuation desc to identify top 50
    valued = [p for p in players if p.get("cfo_valuation") and not p.get("is_override")]
    valued.sort(key=lambda x: x["cfo_valuation"], reverse=True)
    top50_ids = {str(p["id"]) for p in valued[:50]}

    for p in players:
        if p.get("is_override"):
            continue  # already an override

        pid = str(p["id"])
        on3 = p.get("on3_valuation") or 0
        cfo = p.get("cfo_valuation") or 0
        followers = p.get("total_followers") or 0
        ratio = on3 / cfo if cfo > 0 else (999 if on3 > 0 else 0)

        reasons = []

        # Criterion 1: On3 >= 2x CFO and On3 >= $500K
        if on3 >= 500_000 and ratio >= 2.0:
            reasons.append(f"On3 ${on3:,} is {ratio:.1f}x our ${cfo:,}")

        # Criterion 2: High social following + potentially undervalued
        if followers >= 200_000 and cfo < 1_000_000:
            reasons.append(f"{followers:,} followers but CFO only ${cfo:,}")

        # Criterion 3: Top 50 by CFO (manual review)
        if pid in top50_ids:
            reasons.append("Top 50 by CFO valuation — manual review")

        if not reasons:
            continue

        # Compute confidence
        if ratio >= 3.0 and on3 >= 500_000:
            confidence = "HIGH"
        elif ratio >= 2.0 and on3 >= 500_000:
            confidence = "MEDIUM"
        elif ratio >= 1.5 and on3 > 0:
            confidence = "LOW"
        elif pid in top50_ids:
            confidence = "LOW"
        elif followers >= 200_000:
            confidence = "LOW"
        else:
            confidence = "LOW"

        # Suggested action
        if confidence == "HIGH":
            action = "OVERRIDE"
        elif confidence == "MEDIUM":
            action = "REVIEW"
        else:
            action = "SKIP"

        # Suggested value
        suggested = on3 if on3 > 0 else None

        candidates.append({
            "id": pid,
            "name": p.get("name", "?"),
            "position": (p.get("position") or "?").upper(),
            "team_id": p.get("team_id"),
            "team": teams.get(str(p.get("team_id", "")), ""),
            "cfo_valuation": cfo,
            "on3_valuation": on3,
            "ratio": ratio,
            "followers": followers,
            "star_rating": p.get("star_rating"),
            "depth_chart_rank": p.get("depth_chart_rank"),
            "production_score": p.get("production_score"),
            "draft": p.get("nfl_draft_projection"),
            "confidence": confidence,
            "action": action,
            "suggested_value": suggested,
            "reasons": reasons,
        })

    # Sort: HIGH first, then by on3 desc, then cfo desc
    conf_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    candidates.sort(key=lambda x: (conf_order.get(x["confidence"], 3), -(x["on3_valuation"] or 0), -x["cfo_valuation"]))

    # ─── Phase 2: Present candidates ─────────────────────────────────────

    print("=" * 130)
    print("  OVERRIDE CANDIDATES — REQUIRES REVIEW")
    print("=" * 130)
    print(f"  Total candidates: {len(candidates)}")
    print(f"  HIGH confidence:  {sum(1 for c in candidates if c['confidence'] == 'HIGH')}")
    print(f"  MEDIUM:           {sum(1 for c in candidates if c['confidence'] == 'MEDIUM')}")
    print(f"  LOW:              {sum(1 for c in candidates if c['confidence'] == 'LOW')}")

    print(f"\n{'RK':<4} {'CONF':<7} {'NAME':<28} {'POS':<6} {'TEAM':<18} "
          f"{'CFO VAL':>12} {'ON3 VAL':>12} {'RATIO':>7} {'FOLLOWERS':>10} {'ACTION':<10}")
    print("-" * 130)

    for i, c in enumerate(candidates, 1):
        on3_s = fmt(c["on3_valuation"]) if c["on3_valuation"] else "N/A"
        ratio_s = f"{c['ratio']:.1f}x" if c["on3_valuation"] else "-"
        print(f"{i:<4} {c['confidence']:<7} {c['name']:<28} {c['position']:<6} {c['team']:<18} "
              f"{fmt(c['cfo_valuation']):>12} {on3_s:>12} {ratio_s:>7} {c['followers']:>10,} {c['action']:<10}")

    # Detail for HIGH candidates
    high_candidates = [c for c in candidates if c["confidence"] == "HIGH"]
    if high_candidates:
        print(f"\n{'=' * 100}")
        print("  HIGH CONFIDENCE — DETAILED")
        print(f"{'=' * 100}")
        for c in high_candidates:
            print(f"\n  {c['name']} ({c['position']}, {c['team']})")
            print(f"    CFO Valuation:     {fmt(c['cfo_valuation'])}")
            print(f"    On3 Valuation:     {fmt(c['on3_valuation'])}")
            print(f"    Ratio:             {c['ratio']:.1f}x")
            print(f"    Social Followers:  {c['followers']:,}")
            print(f"    Star Rating:       {c['star_rating'] or '-'}")
            print(f"    DC Rank:           {c['depth_chart_rank'] or '-'}")
            print(f"    Production Score:  {c['production_score'] or '-'}")
            print(f"    Draft Projection:  {c['draft'] or '-'}")
            print(f"    Reasons:           {'; '.join(c['reasons'])}")
            print(f"    Suggested Value:   {fmt(c['suggested_value'])}")
            print(f"    Note: Verify with ESPN/The Athletic before finalizing")

    # Quick entry format for HIGH candidates
    if high_candidates:
        print(f"\n{'=' * 100}")
        print("  QUICK ENTRY FORMAT (paste into approved_overrides.csv)")
        print("  player_name,total_value,years,annualized_value,source_name,source_url")
        print(f"{'=' * 100}")
        for c in high_candidates:
            sv = c["suggested_value"] or c["cfo_valuation"]
            name = c["name"]
            print(f"  {name},{sv},1,{sv},On3,https://www.on3.com/nil/rankings/player/college/football/")

    # ─── Phase 3: CSV export ─────────────────────────────────────────────

    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "player_id", "player_name", "position", "team", "cfo_valuation",
            "on3_valuation", "ratio", "confidence", "suggested_value", "action_taken",
        ])
        writer.writeheader()
        for c in candidates:
            writer.writerow({
                "player_id": c["id"],
                "player_name": c["name"],
                "position": c["position"],
                "team": c["team"],
                "cfo_valuation": c["cfo_valuation"],
                "on3_valuation": c["on3_valuation"] or "",
                "ratio": f"{c['ratio']:.2f}" if c["on3_valuation"] else "",
                "confidence": c["confidence"],
                "suggested_value": c["suggested_value"] or "",
                "action_taken": "",
            })

    print(f"\n  CSV saved to: {CSV_OUT}")
    print(f"  {len(candidates)} candidate(s) exported.")
    print("=" * 100)


if __name__ == "__main__":
    main()
