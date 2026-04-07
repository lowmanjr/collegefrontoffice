"""
explore_data.py
---------------
Step 1A: Explore database state — cfbd_id coverage by position.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from supabase_client import supabase


def main():
    # ── 1. Count players with non-null cfbd_id ────────────────────────────────
    resp_total = supabase.table("players").select("id", count="exact").execute()
    total_players = resp_total.count

    resp_with_cfbd = (
        supabase.table("players")
        .select("id", count="exact")
        .not_.is_("cfbd_id", "null")
        .execute()
    )
    with_cfbd_count = resp_with_cfbd.count

    print("=" * 60)
    print("DATABASE EXPLORATION — cfbd_id coverage")
    print("=" * 60)
    print(f"Total players in DB        : {total_players:,}")
    print(f"Players WITH cfbd_id       : {with_cfbd_count:,}")
    print(f"Players WITHOUT cfbd_id    : {total_players - with_cfbd_count:,}")
    print()

    # ── 2. Breakdown by position: players WITH cfbd_id ─────────────────────────
    resp_with = (
        supabase.table("players")
        .select("position, cfbd_id")
        .not_.is_("cfbd_id", "null")
        .execute()
    )
    with_cfbd = resp_with.data or []

    pos_counts_with: dict[str, int] = {}
    for p in with_cfbd:
        pos = (p.get("position") or "UNKNOWN").upper().strip()
        pos_counts_with[pos] = pos_counts_with.get(pos, 0) + 1

    print("Players WITH cfbd_id — by position:")
    print(f"  {'Position':<10}  {'Count':>6}")
    print("  " + "-" * 20)
    for pos, cnt in sorted(pos_counts_with.items(), key=lambda x: -x[1]):
        print(f"  {pos:<10}  {cnt:>6}")
    print()

    # ── 3. Breakdown by position: players WITHOUT cfbd_id on depth chart ───────
    resp_without = (
        supabase.table("players")
        .select("position")
        .is_("cfbd_id", "null")
        .eq("is_on_depth_chart", True)
        .execute()
    )
    without_cfbd_dc = resp_without.data or []

    pos_counts_without: dict[str, int] = {}
    for p in without_cfbd_dc:
        pos = (p.get("position") or "UNKNOWN").upper().strip()
        pos_counts_without[pos] = pos_counts_without.get(pos, 0) + 1

    print("Players WITHOUT cfbd_id (on depth chart) — by position:")
    print(f"  {'Position':<10}  {'Count':>6}")
    print("  " + "-" * 20)
    if pos_counts_without:
        for pos, cnt in sorted(pos_counts_without.items(), key=lambda x: -x[1]):
            print(f"  {pos:<10}  {cnt:>6}")
    else:
        print("  (none)")
    print()

    # ── 4. Sample 5 players with cfbd_id (mix of positions) ───────────────────
    resp_sample = (
        supabase.table("players")
        .select("id, name, position, cfbd_id, star_rating")
        .not_.is_("cfbd_id", "null")
        .limit(100)
        .execute()
    )
    sample_pool = resp_sample.data or []

    # Pick one from each position group if possible
    seen_positions = set()
    samples = []
    for p in sample_pool:
        pos = (p.get("position") or "UNKNOWN").upper().strip()
        if pos not in seen_positions:
            seen_positions.add(pos)
            samples.append(p)
        if len(samples) >= 5:
            break
    # Fill remainder if needed
    for p in sample_pool:
        if len(samples) >= 5:
            break
        if p not in samples:
            samples.append(p)

    print("5 Sample players with cfbd_id:")
    print(f"  {'Name':<28}  {'Pos':<6}  {'Stars':<6}  {'cfbd_id':>10}")
    print("  " + "-" * 58)
    for p in samples:
        print(
            f"  {(p.get('name') or '—'):<28}  "
            f"{(p.get('position') or '—').upper():<6}  "
            f"{(p.get('star_rating') or 0):<6}  "
            f"{p.get('cfbd_id'):>10}"
        )

    print()
    print("Sample cfbd_ids (for CFBD API exploration):")
    for p in samples:
        print(f"  {p.get('cfbd_id')}  ({p.get('name')}, {p.get('position')})")


if __name__ == "__main__":
    main()
