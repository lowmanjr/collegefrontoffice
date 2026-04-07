"""
assign_default_depth_chart.py
------------------------------
Assigns a conservative default depth chart rank to active 4/5-star college
athletes who are not on any depth chart and have no valuation.

Assigns depth_chart_rank = STARTER_COUNT + 2 (2nd backup) for their position.
This is conservative enough to not inflate valuations, but puts them on the
chart so the pedigree floor can activate for underclassmen and the engine can
compute a value for upperclassmen.

Does NOT touch: override players, departed players, HS recruits, players
already on depth chart.

Usage:
    python assign_default_depth_chart.py              # dry-run (default)
    python assign_default_depth_chart.py --apply      # write to DB
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import argparse
import datetime
from collections import Counter

from supabase_client import supabase

# Mirror the position starter counts from calculate_cfo_valuations.py
POSITION_STARTER_COUNTS: dict[str, int] = {
    "QB": 1, "RB": 1, "TE": 2, "K": 1, "P": 1, "LS": 1, "PK": 1,
    "WR": 3,
    "OL": 5, "OT": 5, "OG": 5, "C": 5, "IOL": 5,
    "EDGE": 2, "DE": 2,
    "DT": 2, "DL": 2,
    "LB": 3, "DB": 3,
    "CB": 2,
    "S": 2,
    "ATH": 1,
}

SINGLE_STARTER_POSITIONS = {"QB", "RB", "K", "P", "LS", "PK", "ATH"}

DEFAULT_RANK = 4


def compute_assigned_rank(position: str | None) -> int:
    """Returns STARTER_COUNT + 2 for the position, or DEFAULT_RANK if unknown."""
    if not position:
        return DEFAULT_RANK
    pos = position.upper().strip()
    starter_count = POSITION_STARTER_COUNTS.get(pos)
    if starter_count is None:
        return DEFAULT_RANK
    return starter_count + 2


def compute_expected_multiplier(
    rank: int, position: str | None, star: int, class_year: int | None,
) -> float:
    """Compute the depth chart multiplier this player will get, including pedigree floor."""
    pos = (position or "").upper().strip()
    starter_count = POSITION_STARTER_COUNTS.get(pos, 1)
    is_single = pos in SINGLE_STARTER_POSITIONS

    # Raw multiplier
    if rank <= starter_count:
        raw = 1.0
    else:
        backup_depth = rank - starter_count
        if is_single:
            if backup_depth == 1: raw = 0.35
            elif backup_depth == 2: raw = 0.20
            else: raw = 0.12
        else:
            if backup_depth == 1: raw = 0.55
            elif backup_depth == 2: raw = 0.40
            else: raw = 0.25

    # Pedigree floor
    cy = class_year if class_year is not None else 99
    if cy <= 3 and star >= 5:
        return max(raw, 1.0)
    if cy <= 3 and star == 4:
        return max(raw, 0.45)
    return raw


def main():
    parser = argparse.ArgumentParser(
        description="Assign default depth chart rank to unvalued 4/5-star active athletes"
    )
    parser.add_argument("--apply", action="store_true", help="Write to DB (default is dry-run)")
    args = parser.parse_args()

    dry_run = not args.apply
    mode = "DRY RUN" if dry_run else "LIVE"

    print("=" * 85)
    print(f"  ASSIGN DEFAULT DEPTH CHART ({mode})")
    print("=" * 85)

    # ── Fetch candidates ────────────────────────────────────────────────────
    teams_resp = supabase.table("teams").select("id, university_name").execute()
    tnames = {t["id"]: t["university_name"] for t in (teams_resp.data or [])}

    all_p: list[dict] = []
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select(
                "id, name, position, team_id, star_rating, class_year, "
                "is_on_depth_chart, depth_chart_rank, is_override, "
                "roster_status, player_tag, cfo_valuation"
            )
            .eq("player_tag", "College Athlete")
            .eq("roster_status", "active")
            .gte("star_rating", 4)
            .is_("cfo_valuation", "null")
            .range(offset, offset + 999)
            .execute()
        )
        batch = resp.data or []
        all_p.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    print(f"\n  Active 4/5-star athletes with no valuation: {len(all_p)}")

    # ── Filter candidates ───────────────────────────────────────────────────
    candidates: list[dict] = []
    skipped_override = 0
    skipped_on_dc = 0
    skipped_no_team = 0

    for p in all_p:
        if p.get("is_override"):
            skipped_override += 1
            continue
        if p.get("is_on_depth_chart"):
            skipped_on_dc += 1
            continue
        if not p.get("team_id"):
            skipped_no_team += 1
            continue
        candidates.append(p)

    print(f"  Candidates to assign: {len(candidates)}")
    print(f"  Skipped (override): {skipped_override}")
    print(f"  Skipped (already on DC): {skipped_on_dc}")
    print(f"  Skipped (no team_id): {skipped_no_team}")

    if not candidates:
        print("\n  No candidates to process.")
        print(f"\n{'=' * 85}")
        return

    # ── Compute assignments ─────────────────────────────────────────────────
    assignments: list[dict] = []
    for p in candidates:
        pos = p.get("position")
        star = p.get("star_rating") or 0
        try:
            cy = int(p["class_year"]) if p.get("class_year") else None
        except (TypeError, ValueError):
            cy = None

        rank = compute_assigned_rank(pos)
        mult = compute_expected_multiplier(rank, pos, star, cy)

        assignments.append({
            "id": p["id"],
            "name": p["name"],
            "team": tnames.get(p.get("team_id", ""), "?"),
            "position": pos or "?",
            "star": star,
            "class_year": cy,
            "assigned_rank": rank,
            "expected_mult": mult,
        })

    assignments.sort(key=lambda a: (-a["star"], a["team"], a["name"]))

    # ── Print table ─────────────────────────────────────────────────────────
    print(f"\n  {'Name':<28} {'Team':<18} {'Pos':<6} {'Star':>4} {'Cls':>4} {'Rank':>5} {'Mult':>6} {'Floor?':<8}")
    print(f"  {'─' * 82}")

    for a in assignments:
        cy_s = str(a["class_year"]) if a["class_year"] is not None else "—"
        # Check if pedigree floor is active
        cy = a["class_year"] if a["class_year"] is not None else 99
        floor = ""
        if cy <= 3 and a["star"] >= 5:
            floor = "5★ floor"
        elif cy <= 3 and a["star"] == 4:
            floor = "4★ floor"

        print(
            f"  {a['name']:<28} {a['team']:<18} {a['position']:<6} "
            f"{a['star']:>4} {cy_s:>4} {a['assigned_rank']:>5} "
            f"{a['expected_mult']:>6.2f} {floor:<8}"
        )

    # ── Position breakdown ──────────────────────────────────────────────────
    pos_counts = Counter(a["position"] for a in assignments)
    print(f"\n  By position:")
    for pos, cnt in sorted(pos_counts.items(), key=lambda x: -x[1]):
        rank = compute_assigned_rank(pos)
        print(f"    {pos:<6} {cnt:>3} players → rank {rank}")

    star_counts = Counter(a["star"] for a in assignments)
    print(f"\n  By star rating:")
    for star in sorted(star_counts.keys(), reverse=True):
        print(f"    {star}★: {star_counts[star]}")

    # ── Apply ───────────────────────────────────────────────────────────────
    if dry_run:
        print(f"\n  DRY RUN — {len(assignments)} assignments NOT applied.")
        print(f"  To apply: python assign_default_depth_chart.py --apply")
    else:
        now = datetime.datetime.utcnow().isoformat()
        applied = 0
        errors = 0
        for a in assignments:
            try:
                supabase.table("players").update({
                    "is_on_depth_chart": True,
                    "depth_chart_rank": a["assigned_rank"],
                    "last_updated": now,
                }).eq("id", a["id"]).execute()
                applied += 1
            except Exception as exc:
                print(f"    [ERROR] {a['name']}: {exc}")
                errors += 1
        print(f"\n  Applied: {applied}, Errors: {errors}")

    print(f"\n{'=' * 85}")


if __name__ == "__main__":
    main()
