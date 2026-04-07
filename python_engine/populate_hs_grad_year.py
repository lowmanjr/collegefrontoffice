"""
populate_hs_grad_year.py
-------------------------
Populates hs_grad_year for all High School Recruits where it is currently NULL.

The class_year field was previously normalized from graduation years to a 1-5
college scale during Sprint 3. This script reverses that conversion for HS recruits:

    class_year = 1 → hs_grad_year = 2026  (just graduated, enrolling as FR)
    class_year = 2 → hs_grad_year = 2027  (rising HS senior)
    class_year = 3 → hs_grad_year = 2028  (rising HS junior)
    class_year = 4 → hs_grad_year = 2029  (future prospect)
    class_year = 5 → default 2027 (anomalous — flagged for review)
    class_year = NULL → default 2027  (current recruiting cycle)

Also flags players tagged "High School Recruit" with experience_level =
"Active Roster" or "Portal" as likely mislabeled college athletes.

Usage:
    python populate_hs_grad_year.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import datetime
from collections import Counter
from supabase_client import supabase

GRAD_YEAR_BASE = 2025  # class_year + GRAD_YEAR_BASE = hs_grad_year
DEFAULT_GRAD_YEAR = 2027  # current recruiting cycle


def fetch_hs_recruits() -> list[dict]:
    """Fetch all HS recruits with NULL hs_grad_year."""
    all_hs = []
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, position, star_rating, class_year, hs_grad_year, "
                    "experience_level, player_tag, team_id")
            .eq("player_tag", "High School Recruit")
            .is_("hs_grad_year", "null")
            .range(offset, offset + 999)
            .execute()
        )
        batch = resp.data or []
        all_hs.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return all_hs


def main():
    print("=" * 80)
    print("  POPULATE HS_GRAD_YEAR")
    print("=" * 80)

    recruits = fetch_hs_recruits()
    print(f"\n  HS recruits with NULL hs_grad_year: {len(recruits)}")

    if not recruits:
        print("  Nothing to update.")
        return

    updates: list[dict] = []
    flagged: list[dict] = []
    assignments: Counter = Counter()
    by_year: Counter = Counter()

    for p in recruits:
        pid = str(p["id"])
        cy = p.get("class_year")
        el = (p.get("experience_level") or "").strip()

        # Flag mislabeled players
        if el in ("Active Roster", "Portal"):
            flagged.append(p)

        # Determine hs_grad_year from class_year
        if cy is not None and isinstance(cy, (int, float)):
            cy_int = int(cy)
            if 1 <= cy_int <= 4:
                grad_year = GRAD_YEAR_BASE + cy_int
                reason = f"class_year={cy_int} -> {grad_year}"
            elif cy_int == 5:
                grad_year = DEFAULT_GRAD_YEAR
                reason = f"class_year=5 (anomalous) -> default {DEFAULT_GRAD_YEAR}"
                if p not in flagged:
                    flagged.append(p)
            else:
                grad_year = DEFAULT_GRAD_YEAR
                reason = f"class_year={cy_int} (unexpected) -> default {DEFAULT_GRAD_YEAR}"
        else:
            grad_year = DEFAULT_GRAD_YEAR
            reason = f"class_year=NULL -> default {DEFAULT_GRAD_YEAR}"

        updates.append({"id": pid, "hs_grad_year": grad_year})
        assignments[reason] += 1
        by_year[grad_year] += 1

    # Print assignment summary
    print(f"\n  Assignment logic:")
    for reason, cnt in sorted(assignments.items(), key=lambda x: -x[1]):
        print(f"    {reason}: {cnt}")

    print(f"\n  By hs_grad_year:")
    for yr in sorted(by_year.keys()):
        print(f"    {yr}: {by_year[yr]}")

    # Print flagged players
    if flagged:
        print(f"\n  FLAGGED ({len(flagged)} potentially mislabeled):")
        print(f"  {'NAME':<28} {'POS':<5} {'STAR':>4} {'CY':>4} {'EXP_LVL':<15}")
        print(f"  {'-' * 65}")
        for p in flagged[:20]:
            print(
                f"  {(p.get('name') or '?'):<28} {(p.get('position') or '?'):<5} "
                f"{p.get('star_rating') or '-':>4} {p.get('class_year') or '-':>4} "
                f"{(p.get('experience_level') or '-'):<15}"
            )
        if len(flagged) > 20:
            print(f"  ... and {len(flagged) - 20} more")

    # Write updates
    print(f"\n  Writing {len(updates)} hs_grad_year values...")
    now = datetime.datetime.utcnow().isoformat()
    written = 0
    errors = 0
    BATCH = 200

    rows = [{"id": u["id"], "hs_grad_year": u["hs_grad_year"], "last_updated": now} for u in updates]
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        try:
            supabase.table("players").upsert(chunk, on_conflict="id").execute()
            written += len(chunk)
        except Exception as exc:
            print(f"  [BATCH ERROR] {exc}")
            for row in chunk:
                try:
                    supabase.table("players").update(
                        {"hs_grad_year": row["hs_grad_year"], "last_updated": row["last_updated"]}
                    ).eq("id", row["id"]).execute()
                    written += 1
                except Exception as row_exc:
                    print(f"    [ROW ERROR] {row['id']}: {row_exc}")
                    errors += 1

    print(f"  Written: {written}, Errors: {errors}")
    print("=" * 80)


if __name__ == "__main__":
    main()
