"""
sync_roster_status.py
----------------------
Flags departed players by cross-referencing CFBD transfer portal, current
rosters, class year, and draft projections.

Never deletes records — only updates roster_status:
  active, departed_draft, departed_transfer, departed_graduated, departed_other

Known issues:
  - Tennessee and South Carolina have poor CFBD name matching, causing excessive
    false-positive departures. These teams were manually reset to 'active' and
    should be excluded or handled with extra care until name matching is improved.
  - Override players (is_override=true) are never auto-flagged; logged for manual review.

Usage:
    python sync_roster_status.py --dry-run   # preview changes
    python sync_roster_status.py             # apply changes

Prerequisites:
    Run the SQL migration in supabase/migrations/00004_roster_status.sql first.
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import argparse
import time
import datetime
import unicodedata
import re
import requests
from difflib import SequenceMatcher
from collections import defaultdict, Counter
from supabase_client import supabase
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))

CFBD_API_KEY = os.getenv("CFBD_API_KEY")
CFBD_BASE = "https://api.collegefootballdata.com"
CFBD_HEADERS = {"Authorization": f"Bearer {CFBD_API_KEY}"} if CFBD_API_KEY else {}
REQUEST_DELAY = 0.15


# ─── Helpers ─────────────────────────────────────────────────────────────────

def norm(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-z0-9 ]", "", ascii_name.lower())
    return " ".join(clean.split())


def fuzzy(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def cfbd_get(path: str, params: dict = None) -> list | None:
    try:
        resp = requests.get(f"{CFBD_BASE}{path}", headers=CFBD_HEADERS,
                            params=params or {}, timeout=20)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def load_teams():
    resp = supabase.table("teams").select("id, university_name").execute()
    return {t["id"]: t["university_name"] for t in (resp.data or [])}


def has_roster_status_column() -> bool:
    try:
        supabase.table("players").select("roster_status").limit(1).execute()
        return True
    except Exception:
        return False


def fetch_all_college_athletes():
    # Check if roster_status column exists
    cols = ("id, name, position, team_id, class_year, cfbd_id, "
            "nfl_draft_projection, cfo_valuation, is_on_depth_chart, "
            "is_override, player_tag, depth_chart_rank")
    if has_roster_status_column():
        cols += ", roster_status"

    all_p = []
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select(cols)
            .eq("player_tag", "College Athlete")
            .range(offset, offset + 999)
            .execute()
        )
        batch = resp.data or []
        all_p.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return all_p


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without updating DB")
    args = parser.parse_args()

    dry_run = args.dry_run
    mode = "DRY RUN" if dry_run else "LIVE"

    print("=" * 80)
    print(f"  SYNC ROSTER STATUS ({mode})")
    print("=" * 80)

    teams = load_teams()
    team_by_name = {}
    for tid, tname in teams.items():
        team_by_name[norm(tname)] = tid
        team_by_name[tname.lower()] = tid

    players = fetch_all_college_athletes()
    print(f"  College athletes: {len(players)}")

    # Build lookup structures
    players_by_team: dict[str, list[dict]] = defaultdict(list)
    players_by_id: dict[str, dict] = {}
    for p in players:
        if p.get("team_id"):
            players_by_team[str(p["team_id"])].append(p)
        players_by_id[str(p["id"])] = p

    # Track all status updates: player_id → (new_status, reason)
    updates: dict[str, tuple[str, str]] = {}

    # Override protection: never auto-flag override players
    override_ids = {str(p["id"]) for p in players if p.get("is_override") is True}
    override_skips: list[tuple[dict, str]] = []  # (player, reason) for logging

    # ── Phase 1: Transfer Portal ─────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  PHASE 1: CFBD TRANSFER PORTAL (2026)")
    print(f"{'─' * 70}")

    portal_data = cfbd_get("/player/portal", {"year": 2026})
    if not portal_data:
        print("  [WARN] No 2026 portal data available.")
        portal_data = []
    else:
        print(f"  Total portal entries: {len(portal_data)}")

    portal_matched = 0
    portal_incoming = 0

    # Normalize our team names for matching
    our_team_norms = {}
    for tid, tname in teams.items():
        our_team_norms[norm(tname)] = tid

    for entry in portal_data:
        origin = (entry.get("origin") or "").strip()
        dest = (entry.get("destination") or "").strip()
        first = (entry.get("firstName") or "").strip()
        last = (entry.get("lastName") or "").strip()
        full_name = f"{first} {last}"

        # Check if origin is one of our teams
        origin_tid = None
        for team_norm, tid in our_team_norms.items():
            if fuzzy(norm(origin), team_norm) >= 0.85:
                origin_tid = tid
                break

        if not origin_tid:
            # Check if destination is one of our teams (incoming transfer)
            for team_norm, tid in our_team_norms.items():
                if fuzzy(norm(dest), team_norm) >= 0.85:
                    portal_incoming += 1
                    break
            continue

        # Match player on our roster
        team_roster = players_by_team.get(origin_tid, [])
        best_match = None
        best_score = 0
        for p in team_roster:
            s = fuzzy(full_name, p["name"])
            if s > best_score:
                best_score = s
                best_match = p

        if best_match and best_score >= 0.80:
            pid = str(best_match["id"])
            if pid in override_ids:
                override_skips.append((best_match, f"Transfer portal: {origin} → {dest or '?'}"))
                continue
            if pid not in updates:
                updates[pid] = ("departed_transfer", f"Transfer portal: {origin} → {dest or '?'}")
                portal_matched += 1
                val = best_match.get("cfo_valuation")
                val_s = f"${val:,}" if val else "NULL"
                print(f"    TRANSFER: {best_match['name']:<28} {teams.get(origin_tid, '?'):<18} → {dest or '?':<18} val={val_s}")

    print(f"\n  Portal matches (departed from our teams): {portal_matched}")
    print(f"  Portal incoming (to our teams): {portal_incoming}")

    # ── Phase 2: Current Roster Cross-Reference ──────────────────────────
    print(f"\n{'─' * 70}")
    print("  PHASE 2: CFBD ROSTER CROSS-REFERENCE")
    print(f"{'─' * 70}")

    not_on_roster: list[dict] = []
    roster_year = None

    for tid, tname in teams.items():
        # Try 2026 first, fall back to 2025
        roster = None
        for year in [2026, 2025]:
            roster = cfbd_get("/roster", {"team": tname, "year": year})
            if roster:
                if roster_year is None:
                    roster_year = year
                    print(f"  Using CFBD roster year: {year}")
                break
            time.sleep(REQUEST_DELAY)

        if not roster:
            print(f"  [WARN] No roster data for {tname}")
            continue

        # Build CFBD roster lookup: cfbd_id set + normalized name set
        cfbd_ids_on_roster = set()
        cfbd_names_on_roster = set()
        for r in roster:
            if r.get("id"):
                cfbd_ids_on_roster.add(str(r["id"]))
            fn = (r.get("firstName") or "")
            ln = (r.get("lastName") or "")
            cfbd_names_on_roster.add(norm(f"{fn} {ln}"))

        # Check our players against CFBD roster
        our_roster = players_by_team.get(tid, [])
        for p in our_roster:
            pid = str(p["id"])
            if pid in updates:
                continue  # already flagged by portal

            # Match by cfbd_id first
            if p.get("cfbd_id") and str(p["cfbd_id"]) in cfbd_ids_on_roster:
                continue  # still on roster

            # Match by name
            p_norm = norm(p["name"])
            found = False
            for rname in cfbd_names_on_roster:
                if fuzzy(p_norm, rname) >= 0.85:
                    found = True
                    break

            if not found:
                not_on_roster.append(p)

        time.sleep(REQUEST_DELAY)

    print(f"  Players on our DC but NOT on CFBD {roster_year or '?'} roster: {len(not_on_roster)}")

    # ── Phase 3: Classify departures ─────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  PHASE 3: CLASSIFY DEPARTURES")
    print(f"{'─' * 70}")

    draft_count = 0
    grad_count = 0
    other_count = 0

    for p in not_on_roster:
        pid = str(p["id"])
        if pid in updates:
            continue
        if pid in override_ids:
            override_skips.append((p, f"Not on {roster_year} roster (class_year={p.get('class_year')})"))
            continue

        cy = p.get("class_year")
        draft = p.get("nfl_draft_projection")
        has_strong_draft = draft and 0 < draft < 100

        # Junior/Senior with strong draft projection → draft declaration
        if has_strong_draft and (cy or 0) >= 3:
            updates[pid] = ("departed_draft", f"Draft declaration (proj pick {draft}, class_year {cy})")
            draft_count += 1
            val = p.get("cfo_valuation")
            val_s = f"${val:,}" if val else "NULL"
            print(f"    DRAFT:     {p['name']:<28} {(p.get('position') or '?'):<6} pick={draft} cy={cy} val={val_s}")
            continue

        # Super senior not on roster → graduated
        if cy == 5:
            updates[pid] = ("departed_graduated", f"Super senior (class_year=5), not on {roster_year} roster")
            grad_count += 1
            continue

        # Senior not on roster → likely graduated
        if cy == 4:
            updates[pid] = ("departed_graduated", f"Senior (class_year=4), not on {roster_year} roster")
            grad_count += 1
            continue

        # Others not on roster → departed_other
        updates[pid] = ("departed_other", f"Not on {roster_year} roster (class_year={cy})")
        other_count += 1

    print(f"\n  Classified from roster cross-ref:")
    print(f"    Draft declarations: {draft_count}")
    print(f"    Graduated:         {grad_count}")
    print(f"    Other/unknown:     {other_count}")

    # ── Phase 4: Summary and Apply ───────────────────────────────────────
    print(f"\n{'=' * 80}")
    print(f"  SUMMARY — {len(updates)} DEPARTURES IDENTIFIED")
    print(f"{'=' * 80}")

    # By type
    type_counts = Counter(v[0] for v in updates.values())
    print(f"\n  By type:")
    for t in ["departed_transfer", "departed_draft", "departed_graduated", "departed_other"]:
        print(f"    {t:<25} {type_counts.get(t, 0):>5}")

    # By team
    team_dep_counts: dict[str, int] = Counter()
    for pid, (status, reason) in updates.items():
        p = players_by_id.get(pid)
        if p and p.get("team_id"):
            team_dep_counts[str(p["team_id"])] += 1

    print(f"\n  By team:")
    for tid in sorted(team_dep_counts.keys(), key=lambda x: -team_dep_counts[x]):
        tname = teams.get(tid, "?")
        total = len(players_by_team.get(tid, []))
        dep = team_dep_counts[tid]
        remaining = total - dep
        print(f"    {tname:<22} {dep:>3} departed / {total:>3} total → {remaining:>3} remaining")

    # Notable departures (> $500K)
    notable = []
    for pid, (status, reason) in updates.items():
        p = players_by_id.get(pid)
        if p and (p.get("cfo_valuation") or 0) > 500_000:
            notable.append((p, status, reason))
    notable.sort(key=lambda x: x[0].get("cfo_valuation", 0), reverse=True)

    if notable:
        print(f"\n  Notable departures (> $500K):")
        print(f"  {'NAME':<28} {'POS':<6} {'TEAM':<18} {'STATUS':<22} {'CFO VAL':>12}")
        print(f"  {'-' * 90}")
        for p, status, reason in notable[:25]:
            tname = teams.get(str(p.get("team_id", "")), "?")[:17]
            val = p.get("cfo_valuation") or 0
            print(f"  {p['name']:<28} {(p.get('position') or '?'):<6} {tname:<18} {status:<22} ${val:>10,}")

    # Override players skipped
    if override_skips:
        print(f"\n  OVERRIDE PLAYERS — manual review required ({len(override_skips)}):")
        for p, reason in override_skips:
            val = p.get("cfo_valuation") or 0
            tname = teams.get(str(p.get("team_id", "")), "?")
            print(f"    SKIPPED: {p['name']:<28} {tname:<18} ${val:>10,}  reason: {reason}")
        print(f"  These players were NOT auto-flagged. Update manually if confirmed departed.")

    # Apply
    if dry_run:
        print(f"\n  {'=' * 60}")
        print(f"  DRY RUN — no changes applied.")
        print(f"  To apply:")
        print(f"    1. Run migration: supabase/migrations/00004_roster_status.sql")
        print(f"    2. Run: python sync_roster_status.py")
        print(f"  {'=' * 60}")
    else:
        if not has_roster_status_column():
            print(f"\n  [ERROR] roster_status column does not exist!")
            print(f"  Run the migration first: supabase/migrations/00004_roster_status.sql")
            print(f"{'=' * 80}")
            return

        print(f"\n  Applying {len(updates)} status updates...")
        now = datetime.datetime.utcnow().isoformat()
        applied = 0
        errors = 0
        for pid, (status, reason) in updates.items():
            try:
                supabase.table("players").update({
                    "roster_status": status,
                    "last_updated": now,
                }).eq("id", pid).execute()
                applied += 1
            except Exception as exc:
                print(f"    [ERROR] {pid}: {exc}")
                errors += 1

        print(f"  Applied: {applied}, Errors: {errors}")

    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
