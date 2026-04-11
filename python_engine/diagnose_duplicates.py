"""
diagnose_duplicates.py
-----------------------
Comprehensive duplicate player diagnostic across all 68 Power 4 teams.

Steps:
  1. Fetches all players with full diagnostic fields
  2. Groups by (team_id, normalized_name) to find duplicates
  3. Analyzes each pair to pick keeper vs stale record
  4. Generates a cleanup plan (UPDATE merges + DELETE statements)
  5. Outputs everything for manual review — does NOT execute

Usage:
    python diagnose_duplicates.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import re
import unicodedata
from collections import defaultdict
from supabase_client import supabase

# ─── Name normalization ─────────────────────────────────────────────────────

_SUFFIXES = re.compile(r"\b(jr\.?|sr\.?|ii|iii|iv|v)\b", re.IGNORECASE)


def normalize(name):
    if not name:
        return ""
    n = unicodedata.normalize("NFKD", name)
    n = n.encode("ascii", "ignore").decode("ascii")
    n = n.lower().strip()
    n = _SUFFIXES.sub("", n)
    n = n.replace(".", "").replace("'", "").replace("-", " ")
    return " ".join(n.split())


# ─── Data fetching ──────────────────────────────────────────────────────────

PLAYER_FIELDS = (
    "id, name, position, player_tag, roster_status, is_override, "
    "is_on_depth_chart, depth_chart_rank, cfo_valuation, espn_athlete_id, "
    "cfbd_id, star_rating, production_score, ea_rating, slug, "
    "total_followers, team_id, last_updated"
)


def fetch_all_players():
    all_p = []
    offset = 0
    print("Fetching all players from Supabase...")
    while True:
        resp = (
            supabase.table("players")
            .select(PLAYER_FIELDS)
            .range(offset, offset + 999)
            .execute()
        )
        batch = resp.data or []
        all_p.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    print(f"  {len(all_p)} players fetched.\n")
    return all_p


def fetch_teams():
    resp = supabase.table("teams").select("id, university_name").execute()
    return {t["id"]: t["university_name"] for t in (resp.data or [])}


def fetch_override_player_ids():
    """Return set of player_ids that have nil_overrides rows."""
    resp = supabase.table("nil_overrides").select("player_id").execute()
    return {str(r["player_id"]) for r in (resp.data or [])}


# ─── Duplicate detection ────────────────────────────────────────────────────

def find_duplicates(players):
    groups = defaultdict(list)
    for p in players:
        team_id = p.get("team_id") or "__no_team__"
        norm = normalize(p.get("name") or "")
        groups[(team_id, norm)].append(p)
    return {k: v for k, v in groups.items() if len(v) > 1}


# ─── Scoring: determine keeper vs stale ─────────────────────────────────────

def data_richness_score(p):
    """Score how much useful data a record has. Higher = more complete."""
    score = 0
    if p.get("is_override"):
        score += 1000  # override always wins
    if p.get("depth_chart_rank") is not None:
        score += 100
    if p.get("is_on_depth_chart"):
        score += 50
    if p.get("cfo_valuation") is not None and p.get("cfo_valuation", 0) > 0:
        score += 40
    if p.get("espn_athlete_id") is not None:
        score += 30
    if p.get("cfbd_id") is not None:
        score += 25
    if p.get("production_score") is not None and float(p.get("production_score", 0)) > 0:
        score += 20
    if p.get("ea_rating") is not None and int(p.get("ea_rating", 0)) > 0:
        score += 15
    if p.get("star_rating") is not None and int(p.get("star_rating", 0)) > 0:
        score += 10
    if p.get("total_followers") is not None and int(p.get("total_followers", 0)) > 0:
        score += 5
    if p.get("slug"):
        score += 5
    return score


def analyze_pair(group, override_pids):
    """
    Given a group of duplicate records, determine keeper and stale records.
    Returns list of (keeper, stale, reason, merge_fields) tuples.
    """
    # Sort by data richness descending
    scored = [(data_richness_score(p), p) for p in group]
    scored.sort(key=lambda x: x[0], reverse=True)

    keeper = scored[0][1]
    keeper_score = scored[0][0]
    results = []

    for stale_score, stale in scored[1:]:
        reasons = []

        # Determine why keeper wins
        if keeper.get("is_override") and not stale.get("is_override"):
            reasons.append("Keeper has is_override=true")
        if keeper.get("depth_chart_rank") and not stale.get("depth_chart_rank"):
            reasons.append("Keeper has depth_chart_rank")
        if (keeper.get("cfo_valuation") or 0) > 0 and not (stale.get("cfo_valuation") or 0):
            reasons.append("Keeper has valuation")
        if keeper.get("espn_athlete_id") and not stale.get("espn_athlete_id"):
            reasons.append("Keeper has espn_athlete_id")
        if keeper.get("cfbd_id") and not stale.get("cfbd_id"):
            reasons.append("Keeper has cfbd_id")
        if not reasons:
            reasons.append(f"Keeper richer ({keeper_score} vs {stale_score})")

        # Check if stale has any fields keeper is missing — need merge
        merge_fields = {}
        if stale.get("espn_athlete_id") and not keeper.get("espn_athlete_id"):
            merge_fields["espn_athlete_id"] = stale["espn_athlete_id"]
        if stale.get("cfbd_id") and not keeper.get("cfbd_id"):
            merge_fields["cfbd_id"] = stale["cfbd_id"]
        if stale.get("depth_chart_rank") and not keeper.get("depth_chart_rank"):
            merge_fields["depth_chart_rank"] = stale["depth_chart_rank"]
            merge_fields["is_on_depth_chart"] = True
        if stale.get("ea_rating") and not keeper.get("ea_rating"):
            merge_fields["ea_rating"] = stale["ea_rating"]
        if stale.get("production_score") and not keeper.get("production_score"):
            merge_fields["production_score"] = stale["production_score"]
        if stale.get("star_rating") and not keeper.get("star_rating"):
            merge_fields["star_rating"] = stale["star_rating"]
        if stale.get("slug") and not keeper.get("slug"):
            merge_fields["slug"] = stale["slug"]
        if (stale.get("total_followers") or 0) > (keeper.get("total_followers") or 0):
            merge_fields["total_followers"] = stale["total_followers"]

        results.append({
            "keeper": keeper,
            "stale": stale,
            "keeper_score": keeper_score,
            "stale_score": stale_score,
            "reason": "; ".join(reasons),
            "merge_fields": merge_fields,
        })

    return results


# ─── Formatting helpers ─────────────────────────────────────────────────────

def fmt_val(v):
    if v is None:
        return "NULL"
    return f"${v:,}"


def fmt_field(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return str(v)
    return str(v)


def print_player_detail(p, label, teams):
    team_name = teams.get(str(p.get("team_id", "")), "???")
    print(f"    [{label}] id={p['id']}")
    print(f"      name:             {p.get('name')}")
    print(f"      position:         {p.get('position')}")
    print(f"      player_tag:       {p.get('player_tag')}")
    print(f"      roster_status:    {p.get('roster_status')}")
    print(f"      is_override:      {p.get('is_override')}")
    print(f"      is_on_depth_chart:{p.get('is_on_depth_chart')}")
    print(f"      depth_chart_rank: {fmt_field(p.get('depth_chart_rank'))}")
    print(f"      cfo_valuation:    {fmt_val(p.get('cfo_valuation'))}")
    print(f"      espn_athlete_id:  {fmt_field(p.get('espn_athlete_id'))}")
    print(f"      cfbd_id:          {fmt_field(p.get('cfbd_id'))}")
    print(f"      star_rating:      {fmt_field(p.get('star_rating'))}")
    print(f"      production_score: {fmt_field(p.get('production_score'))}")
    print(f"      ea_rating:        {fmt_field(p.get('ea_rating'))}")
    print(f"      total_followers:  {fmt_field(p.get('total_followers'))}")
    print(f"      slug:             {fmt_field(p.get('slug'))}")
    print(f"      last_updated:     {p.get('last_updated', 'NULL')}")
    print(f"      team:             {team_name}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    teams = fetch_teams()
    players = fetch_all_players()
    override_pids = fetch_override_player_ids()

    dup_groups = find_duplicates(players)

    if not dup_groups:
        print("No duplicates found. Database is clean.")
        return

    total_dupes = sum(len(g) - 1 for g in dup_groups.values())

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 1 & 2: Diagnose all duplicates, grouped by team
    # ═══════════════════════════════════════════════════════════════════════

    print("=" * 90)
    print("  DUPLICATE PLAYER DIAGNOSTIC — ALL TEAMS")
    print("=" * 90)
    print(f"  Duplicate groups found: {len(dup_groups)}")
    print(f"  Stale records to clean: {total_dupes}")
    print()

    # Group duplicates by team for summary
    team_dup_counts = defaultdict(int)
    for (team_id, _), group in dup_groups.items():
        team_name = teams.get(str(team_id), "???")
        team_dup_counts[team_name] += len(group) - 1

    print("  DUPLICATES PER TEAM:")
    print("  " + "-" * 50)
    for team_name in sorted(team_dup_counts, key=team_dup_counts.get, reverse=True):
        print(f"    {team_name:<30} {team_dup_counts[team_name]} duplicate(s)")
    print()

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 3: Full details for every duplicate pair
    # ═══════════════════════════════════════════════════════════════════════

    all_decisions = []

    print("=" * 90)
    print("  DETAILED DUPLICATE ANALYSIS")
    print("=" * 90)

    for (team_id, norm_name), group in sorted(
        dup_groups.items(),
        key=lambda x: teams.get(str(x[0][0]), "")
    ):
        team_name = teams.get(str(team_id), "???")
        print(f"\n  --- {team_name}: \"{group[0].get('name')}\" ({len(group)} records) ---")

        decisions = analyze_pair(group, override_pids)
        for d in decisions:
            print_player_detail(d["keeper"], "KEEPER", teams)
            print_player_detail(d["stale"], "DELETE", teams)
            print(f"    Keeper score: {d['keeper_score']}  |  Stale score: {d['stale_score']}")
            print(f"    Reason: {d['reason']}")
            if d["merge_fields"]:
                print(f"    MERGE before delete: {d['merge_fields']}")
            else:
                print(f"    No merge needed — keeper has all useful data.")
            all_decisions.append({
                "team": team_name,
                "name": d["keeper"]["name"],
                "keeper_id": d["keeper"]["id"],
                "delete_id": d["stale"]["id"],
                "reason": d["reason"],
                "merge_fields": d["merge_fields"],
            })

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 4 & 5: Cleanup plan + SQL
    # ═══════════════════════════════════════════════════════════════════════

    print(f"\n\n{'=' * 90}")
    print("  CLEANUP PLAN SUMMARY")
    print(f"{'=' * 90}")
    print(f"\n  {'TEAM':<25} {'PLAYER':<28} {'ACTION':<10} {'REASON'}")
    print("  " + "-" * 88)

    for d in sorted(all_decisions, key=lambda x: x["team"]):
        action = "MERGE+DEL" if d["merge_fields"] else "DELETE"
        print(f"  {d['team']:<25} {d['name']:<28} {action:<10} {d['reason'][:50]}")

    # Safety check: verify no override records are being deleted
    override_deletes = [d for d in all_decisions if any(
        str(d["delete_id"]) in override_pids for _ in [1]
    )]
    if override_deletes:
        print(f"\n  *** WARNING: {len(override_deletes)} override record(s) flagged for deletion!")
        print("  *** Override records must NEVER be deleted. Review manually.")
        for od in override_deletes:
            print(f"      {od['team']}: {od['name']} (delete_id={od['delete_id']})")

    # Generate SQL
    print(f"\n\n{'=' * 90}")
    print("  SQL STATEMENTS (review before executing)")
    print(f"{'=' * 90}\n")

    print("-- ============================================================")
    print("-- CLEANUP DUPLICATES — Generated by diagnose_duplicates.py")
    print("-- Review each statement before running in Supabase SQL editor")
    print("-- ============================================================\n")

    print("BEGIN;\n")

    for d in all_decisions:
        name = d["name"]
        team = d["team"]
        print(f"-- {team}: {name}")

        if d["merge_fields"]:
            set_clauses = ", ".join(
                f"{k} = {repr(v)}" if isinstance(v, str) else f"{k} = {v}"
                for k, v in d["merge_fields"].items()
            )
            print(f"-- Merge useful fields from stale into keeper before deleting")
            print(f"UPDATE players SET {set_clauses}")
            print(f"  WHERE id = '{d['keeper_id']}';")

        print(f"DELETE FROM players WHERE id = '{d['delete_id']}';")
        print()

    print("-- Verify: should return 0 rows")
    print("""SELECT name, team_id, COUNT(*)
FROM players
WHERE player_tag = 'College Athlete'
GROUP BY team_id, name
HAVING COUNT(*) > 1;""")

    print("\nCOMMIT;\n")

    print(f"{'=' * 90}")
    print(f"  Total: {len(all_decisions)} record(s) to delete")
    merges = sum(1 for d in all_decisions if d["merge_fields"])
    print(f"  Merges needed: {merges}")
    print(f"  Pure deletes: {len(all_decisions) - merges}")
    print(f"\n  DO NOT EXECUTE until you have reviewed each decision above.")
    print(f"{'=' * 90}")


if __name__ == "__main__":
    main()
