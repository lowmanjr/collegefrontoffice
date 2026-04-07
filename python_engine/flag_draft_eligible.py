"""
flag_draft_eligible.py
-----------------------
Scrapes the Drafttek 2026 NFL Big Board (6 pages, 600 prospects) and
fuzzy-matches prospects against our players table to identify draft-eligible
athletes.

Outputs:
  1. Console report with match details and confidence scores.
  2. CSV report: python_engine/data/drafttek_matches.csv

Flags:
  --dry-run        Print matches and write CSV, do NOT update the database.
  --apply          Set nfl_draft_projection for matched players.
  --apply-status   Set roster_status='departed_draft' for matched active players.
                   Does NOT touch nfl_draft_projection, cfo_valuation, or overrides.
  --threshold N    Minimum combined match score (default 0.70).

Usage:
    python flag_draft_eligible.py                          # dry-run (default)
    python flag_draft_eligible.py --apply                  # write projections
    python flag_draft_eligible.py --apply-status           # flag active as departed
    python flag_draft_eligible.py --apply-status --dry-run # preview status changes
    python flag_draft_eligible.py --threshold 0.65         # lower match threshold
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import csv
import argparse
import time
import datetime
import unicodedata
import re
from difflib import SequenceMatcher

import requests
from bs4 import BeautifulSoup
from supabase_client import supabase

# ─── Constants ──────────────────────────────────────────────────────────────

BASE_URL = "https://www.drafttek.com/2026-NFL-Draft-Big-Board/Top-NFL-Draft-Prospects-2026-Page-{page}.asp"
PAGES = range(1, 7)  # Pages 1–6 (prospects 1–600)
REQUEST_DELAY = 1.5  # seconds between page fetches
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

CSV_OUT = os.path.join(os.path.dirname(__file__), "data", "drafttek_matches.csv")

DEFAULT_THRESHOLD = 0.70  # combined match score cutoff


# ─── Name normalization ─────────────────────────────────────────────────────

def norm(name: str) -> str:
    """Normalize a name for fuzzy comparison: NFKD → ASCII → lowercase → strip punctuation."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-z0-9 ]", "", ascii_name.lower())
    return " ".join(clean.split())


def fuzzy(a: str, b: str) -> float:
    """Fuzzy match score between two strings (0.0–1.0)."""
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


# ─── School name aliases ────────────────────────────────────────────────────
# Drafttek uses short school names; our DB uses full university names.

SCHOOL_ALIASES: dict[str, list[str]] = {
    "Alabama":       ["Alabama"],
    "Clemson":        ["Clemson"],
    "Florida":        ["Florida"],
    "Georgia":        ["Georgia"],
    "LSU":            ["LSU"],
    "Miami":          ["Miami", "Miami (FL)", "Miami (Fla.)"],
    "Michigan":       ["Michigan"],
    "Notre Dame":     ["Notre Dame"],
    "Ohio State":     ["Ohio State", "Ohio St."],
    "Oklahoma":       ["Oklahoma"],
    "Oregon":         ["Oregon"],
    "South Carolina": ["South Carolina"],
    "Tennessee":      ["Tennessee"],
    "Texas":          ["Texas"],
    "USC":            ["USC", "Southern California", "Southern Cal"],
    "Washington":     ["Washington"],
}


def build_school_norm_map(teams: dict[str, str]) -> dict[str, str]:
    """
    Build normalized-school-name → team_id lookup.
    Includes alias expansions so 'ohio state' matches our 'Ohio State' team.
    """
    mapping: dict[str, str] = {}
    for tid, tname in teams.items():
        mapping[norm(tname)] = tid
        # Add aliases
        for canonical, aliases in SCHOOL_ALIASES.items():
            if norm(canonical) == norm(tname):
                for alias in aliases:
                    mapping[norm(alias)] = tid
    return mapping


# ─── Scraping ───────────────────────────────────────────────────────────────

def scrape_page(page_num: int) -> list[dict]:
    """
    Scrape a single Drafttek Big Board page.
    Returns list of dicts: {rank, name, school, position}.
    """
    url = BASE_URL.format(page=page_num)
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        resp.raise_for_status()
    except Exception as exc:
        print(f"  [ERROR] Failed to fetch page {page_num}: {exc}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", class_="player-info")
    if not table:
        print(f"  [WARN] No player-info table found on page {page_num}")
        return []

    prospects: list[dict] = []
    rows = table.find_all("tr")

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 5:
            continue

        # Extract text from each cell
        rank_text = cells[0].get_text(strip=True)
        # cells[1] = CNG (change indicator — skip)
        name_text = cells[2].get_text(strip=True)
        school_text = cells[3].get_text(strip=True)
        pos_text = cells[4].get_text(strip=True)

        # Validate rank is numeric (skip header row)
        try:
            rank = int(rank_text)
        except ValueError:
            continue

        if not name_text:
            continue

        prospects.append({
            "rank": rank,
            "name": name_text,
            "school": school_text,
            "position": pos_text.upper().strip(),
        })

    return prospects


def scrape_all_pages() -> list[dict]:
    """Scrape all 6 pages of the Drafttek Big Board."""
    all_prospects: list[dict] = []

    for page_num in PAGES:
        print(f"  Scraping page {page_num}/6...")
        prospects = scrape_page(page_num)
        all_prospects.extend(prospects)
        print(f"    Found {len(prospects)} prospects")

        if page_num < max(PAGES):
            time.sleep(REQUEST_DELAY)

    return all_prospects


# ─── Database fetching ──────────────────────────────────────────────────────

def fetch_teams() -> dict[str, str]:
    """Returns {team_id: university_name}."""
    resp = supabase.table("teams").select("id, university_name").execute()
    return {t["id"]: t["university_name"] for t in (resp.data or [])}


def fetch_college_athletes() -> list[dict]:
    """Fetch all College Athletes with fields needed for matching."""
    all_players: list[dict] = []
    offset = 0
    PAGE = 1000
    while True:
        resp = (
            supabase.table("players")
            .select(
                "id, name, position, team_id, cfo_valuation, "
                "nfl_draft_projection, is_on_depth_chart, is_override, "
                "roster_status, class_year, star_rating"
            )
            .eq("player_tag", "College Athlete")
            .range(offset, offset + PAGE - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE
    return all_players


# ─── Matching ───────────────────────────────────────────────────────────────

def match_prospects(
    prospects: list[dict],
    players: list[dict],
    teams: dict[str, str],
    threshold: float,
) -> list[dict]:
    """
    Fuzzy-match Drafttek prospects against our players.
    Returns list of match dicts sorted by Drafttek rank.
    """
    school_map = build_school_norm_map(teams)

    # Pre-compute player data for matching
    player_index: list[tuple[str, str, str, dict]] = []
    for p in players:
        pname = norm(p.get("name") or "")
        tid = str(p.get("team_id") or "")
        school = norm(teams.get(tid, ""))
        pos = (p.get("position") or "").upper().strip()
        player_index.append((pname, school, pos, p))

    matches: list[dict] = []
    unmatched_on_our_teams: list[dict] = []

    for prospect in prospects:
        dt_name = prospect["name"]
        dt_school = prospect["school"]
        dt_pos = prospect["position"]
        dt_rank = prospect["rank"]

        # Check if this school is one of our tracked teams
        # Exact match first, then fuzzy fallback
        dt_school_tid = None
        dt_school_norm = norm(dt_school)
        if dt_school_norm in school_map:
            dt_school_tid = school_map[dt_school_norm]
        else:
            for s_norm, tid in school_map.items():
                if fuzzy(dt_school_norm, s_norm) >= 0.90:
                    dt_school_tid = tid
                    break

        # Only match prospects from our tracked teams
        if dt_school_tid is None:
            continue

        # Find best player match within that team
        best_match = None
        best_score = 0.0
        best_name_score = 0.0

        for pname, pschool, ppos, player in player_index:
            # Skip players not on this team
            if str(player.get("team_id") or "") != dt_school_tid:
                continue

            name_score = fuzzy(dt_name, player.get("name", ""))
            pos_bonus = 0.05 if dt_pos == ppos else 0.0

            # For same-team matching, name is the primary signal
            combined = name_score + pos_bonus

            if combined > best_score:
                best_score = combined
                best_name_score = name_score
                best_match = player

        if best_match and best_score >= threshold:
            team_name = teams.get(str(best_match.get("team_id", "")), "?")
            matches.append({
                "drafttek_rank": dt_rank,
                "drafttek_name": dt_name,
                "drafttek_school": dt_school,
                "drafttek_position": dt_pos,
                "player_id": str(best_match["id"]),
                "player_name": best_match.get("name", "?"),
                "player_team": team_name,
                "player_position": (best_match.get("position") or "?").upper(),
                "cfo_valuation": best_match.get("cfo_valuation"),
                "current_roster_status": best_match.get("roster_status") or "active",
                "current_draft_projection": best_match.get("nfl_draft_projection"),
                "is_override": best_match.get("is_override", False),
                "class_year": best_match.get("class_year"),
                "match_confidence": round(best_score, 3),
                "name_score": round(best_name_score, 3),
            })
        else:
            unmatched_on_our_teams.append({
                "rank": dt_rank,
                "name": dt_name,
                "school": dt_school,
                "position": dt_pos,
                "best_score": round(best_score, 3),
            })

    matches.sort(key=lambda m: m["drafttek_rank"])

    if unmatched_on_our_teams:
        print(f"\n  Unmatched prospects from our teams ({len(unmatched_on_our_teams)}):")
        for u in unmatched_on_our_teams[:15]:
            print(f"    #{u['rank']:<4} {u['name']:<28} {u['school']:<18} {u['position']:<5} best={u['best_score']:.2f}")
        if len(unmatched_on_our_teams) > 15:
            print(f"    ... and {len(unmatched_on_our_teams) - 15} more")

    return matches


# ─── CSV output ─────────────────────────────────────────────────────────────

def write_csv(matches: list[dict]) -> None:
    """Write match results to CSV."""
    os.makedirs(os.path.dirname(CSV_OUT), exist_ok=True)

    fieldnames = [
        "drafttek_rank", "drafttek_name", "drafttek_school", "drafttek_position",
        "player_name", "player_team", "player_position", "cfo_valuation",
        "current_roster_status", "current_draft_projection",
        "is_override", "class_year", "match_confidence",
    ]

    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(matches)

    print(f"\n  CSV written: {CSV_OUT} ({len(matches)} rows)")


# ─── Database updates ──────────────────────────────────────────────────────

def apply_updates(matches: list[dict]) -> tuple[int, int]:
    """
    Set nfl_draft_projection for matched players.
    Override players are skipped (logged for manual review).
    Returns (applied, skipped).
    """
    now = datetime.datetime.utcnow().isoformat()
    applied = 0
    skipped = 0

    for m in matches:
        pid = m["player_id"]

        # Never auto-update override players
        if m.get("is_override"):
            skipped += 1
            continue

        update_data: dict = {
            "nfl_draft_projection": m["drafttek_rank"],
            "last_updated": now,
        }

        try:
            supabase.table("players").update(update_data).eq("id", pid).execute()
            applied += 1
        except Exception as exc:
            print(f"    [ERROR] {m['player_name']}: {exc}")

    return applied, skipped


# ─── Roster status updates ─────────────────────────────────────────────────

def apply_status_updates(matches: list[dict], dry_run: bool) -> tuple[int, int, int]:
    """
    Set roster_status='departed_draft' for matched players that are currently
    active. Does NOT touch nfl_draft_projection or cfo_valuation.
    Skips override players entirely.
    Returns (applied, skipped_override, skipped_already_departed).
    """
    # Filter to actionable players: currently active and not an override
    actionable: list[dict] = []
    skipped_override = 0
    skipped_departed = 0

    for m in matches:
        status = m.get("current_roster_status") or "active"
        if m.get("is_override"):
            skipped_override += 1
            continue
        if status != "active":
            skipped_departed += 1
            continue
        actionable.append(m)

    # ── Preview ──────────────────────────────────────────────────────────
    mode_label = "DRY RUN" if dry_run else "LIVE"
    print(f"\n{'=' * 90}")
    print(f"  ROSTER STATUS UPDATE — {mode_label}")
    print(f"  active → departed_draft")
    print(f"{'=' * 90}")

    if not actionable:
        print(f"\n  No active players to update.")
        print(f"  (Skipped: {skipped_override} overrides, {skipped_departed} already departed)")
        return 0, skipped_override, skipped_departed

    print(f"\n  Players to update: {len(actionable)}")
    print(f"  Skipped (override): {skipped_override}")
    print(f"  Skipped (already departed): {skipped_departed}")

    header = f"{'RK':<5} {'PLAYER':<28} {'TEAM':<18} {'POS':<6} {'CFO VAL':>12} {'CONF':>6} {'STATUS CHANGE':<28}"
    divider = "─" * len(header)
    print(f"\n  {header}")
    print(f"  {divider}")

    for m in actionable:
        val = m.get("cfo_valuation")
        val_s = f"${val:>10,}" if val else f"{'—':>11}"
        print(
            f"  {m['drafttek_rank']:<5} "
            f"{m['player_name']:<28} "
            f"{m['player_team']:<18} "
            f"{m['player_position']:<6} "
            f"{val_s} "
            f"{m['match_confidence']:>5.2f} "
            f"active → departed_draft"
        )

    print(f"  {divider}")

    if dry_run:
        print(f"\n  DRY RUN — no changes written.")
        print(f"  To apply: python flag_draft_eligible.py --apply-status")
        return 0, skipped_override, skipped_departed

    # ── Write ────────────────────────────────────────────────────────────
    # Use row-by-row .update().eq() — NOT upsert, which would try to INSERT
    # partial rows and hit NOT NULL constraints on columns like `name`.
    now = datetime.datetime.utcnow().isoformat()
    applied = 0
    errors = 0

    for m in actionable:
        try:
            supabase.table("players").update({
                "roster_status": "departed_draft",
                "last_updated": now,
            }).eq("id", m["player_id"]).execute()
            applied += 1
        except Exception as exc:
            print(f"    [ERROR] {m['player_name']}: {exc}")
            errors += 1

    print(f"\n  Updated: {applied}, Errors: {errors}")

    return applied, skipped_override, skipped_departed


# ─── Summary report ─────────────────────────────────────────────────────────

def print_summary(matches: list[dict], apply: bool) -> None:
    if not matches:
        print("\n  No matches found.")
        return

    header = f"{'RK':<5} {'DRAFTTEK NAME':<28} {'SCHOOL':<18} {'POS':<6} {'OUR MATCH':<28} {'CONF':>5} {'CFO VAL':>12} {'STATUS':<18}"
    divider = "─" * len(header)

    print(f"\n{'=' * len(header)}")
    print(f"  DRAFTTEK 2026 BIG BOARD — MATCHED PROSPECTS")
    print(f"{'=' * len(header)}")
    print(f"  {header}")
    print(f"  {divider}")

    override_matches: list[dict] = []

    for m in matches:
        val = m.get("cfo_valuation")
        val_s = f"${val:>10,}" if val else f"{'—':>11}"
        status = m["current_roster_status"]
        flag = " *" if m.get("is_override") else ""

        print(
            f"  {m['drafttek_rank']:<5} "
            f"{m['drafttek_name']:<28} "
            f"{m['drafttek_school']:<18} "
            f"{m['drafttek_position']:<6} "
            f"{m['player_name']:<28} "
            f"{m['match_confidence']:>5.2f} "
            f"{val_s} "
            f"{status:<18}{flag}"
        )

        if m.get("is_override"):
            override_matches.append(m)

    print(f"  {divider}")
    print(f"  Total matches: {len(matches)}")

    # Breakdown
    from collections import Counter
    pos_counts = Counter(m["drafttek_position"] for m in matches)
    team_counts = Counter(m["player_team"] for m in matches)

    print(f"\n  By position:")
    for pos, cnt in sorted(pos_counts.items(), key=lambda x: -x[1]):
        print(f"    {pos:<6} {cnt}")

    print(f"\n  By team:")
    for team, cnt in sorted(team_counts.items(), key=lambda x: -x[1]):
        print(f"    {team:<22} {cnt}")

    # High-value prospects
    high_val = [m for m in matches if (m.get("cfo_valuation") or 0) > 500_000]
    high_val.sort(key=lambda m: m.get("cfo_valuation") or 0, reverse=True)
    if high_val:
        print(f"\n  High-value draft prospects (> $500K CFO Valuation):")
        for m in high_val[:15]:
            val = m.get("cfo_valuation") or 0
            print(
                f"    #{m['drafttek_rank']:<4} {m['player_name']:<28} "
                f"{m['player_team']:<18} ${val:>10,}"
            )

    # Override warnings
    if override_matches:
        print(f"\n  OVERRIDE PLAYERS — manual review required ({len(override_matches)}):")
        for m in override_matches:
            val = m.get("cfo_valuation") or 0
            print(
                f"    SKIPPED: #{m['drafttek_rank']:<4} {m['player_name']:<28} "
                f"{m['player_team']:<18} ${val:>10,}"
            )
        print(f"  * Override players are NOT auto-updated. Review and update manually if needed.")

    if not apply:
        print(f"\n  {'=' * 60}")
        print(f"  DRY RUN — no database changes applied.")
        print(f"  To apply: python flag_draft_eligible.py --apply")
        print(f"  {'=' * 60}")


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scrape Drafttek 2026 Big Board and match against our players"
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Write nfl_draft_projection to DB",
    )
    parser.add_argument(
        "--apply-status", action="store_true",
        help="Set roster_status='departed_draft' for matched active players "
             "(does NOT touch nfl_draft_projection or cfo_valuation)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview changes without writing to DB (default when no --apply* flag)",
    )
    parser.add_argument(
        "--threshold", type=float, default=DEFAULT_THRESHOLD,
        help=f"Minimum combined match score (default {DEFAULT_THRESHOLD})",
    )
    args = parser.parse_args()

    # If no action flag is set, it's an implicit dry-run
    is_dry_run = args.dry_run or (not args.apply and not args.apply_status)

    mode_parts = []
    if args.apply:
        mode_parts.append("projections")
    if args.apply_status:
        mode_parts.append("roster status")
    if is_dry_run:
        mode = "DRY RUN"
    elif mode_parts:
        mode = "LIVE — " + " + ".join(mode_parts)
    else:
        mode = "DRY RUN"

    print("=" * 80)
    print(f"  DRAFTTEK 2026 BIG BOARD SCRAPER ({mode})")
    print("=" * 80)

    # ── Fetch our data ──────────────────────────────────────────────────────
    print("\n  Loading teams and players from Supabase...")
    teams = fetch_teams()
    players = fetch_college_athletes()
    active = [p for p in players if (p.get("roster_status") or "active") == "active"]
    print(f"  Teams: {len(teams)}")
    print(f"  College athletes: {len(players)} ({len(active)} active)")

    # ── Scrape Drafttek ─────────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  SCRAPING DRAFTTEK 2026 BIG BOARD")
    print(f"{'─' * 70}")

    prospects = scrape_all_pages()
    print(f"\n  Total prospects scraped: {len(prospects)}")

    if not prospects:
        print("  [ERROR] No prospects scraped. Exiting.")
        return

    # Filter to our tracked schools
    school_map = build_school_norm_map(teams)
    our_school_prospects = []
    for p in prospects:
        p_school_norm = norm(p["school"])
        if p_school_norm in school_map:
            our_school_prospects.append(p)
            continue
        for s_norm in school_map:
            if fuzzy(p_school_norm, s_norm) >= 0.90:
                our_school_prospects.append(p)
                break
    print(f"  Prospects from our {len(teams)} tracked teams: {len(our_school_prospects)}")

    # ── Match ───────────────────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print(f"  MATCHING (threshold={args.threshold})")
    print(f"{'─' * 70}")

    matches = match_prospects(prospects, players, teams, args.threshold)

    # ── Output ──────────────────────────────────────────────────────────────
    write_csv(matches)
    print_summary(matches, not is_dry_run)

    # ── Apply projections ───────────────────────────────────────────────────
    if args.apply and not is_dry_run and matches:
        print(f"\n  Applying {len(matches)} draft projection updates...")
        applied, skipped = apply_updates(matches)
        print(f"  Applied: {applied}, Skipped (overrides): {skipped}")

    # ── Apply roster status ─────────────────────────────────────────────────
    if args.apply_status and matches:
        applied, skip_ov, skip_dep = apply_status_updates(matches, is_dry_run)

    print(f"\n{'=' * 80}")


if __name__ == "__main__":
    main()
