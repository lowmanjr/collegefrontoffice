"""
validate_valuations.py
-----------------------
Comprehensive post-valuation validation. Catches position configuration bugs,
formula runaways, rank inversions, and data integrity issues.

Exit code 0 if all checks pass, 1 if any CRITICAL issues found.

Usage:
    python validate_valuations.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import datetime
from collections import defaultdict
from supabase_client import supabase
from calculate_cfo_valuations import POSITION_BASE_VALUES, DEFAULT_BASE_VALUE

# ─── Data fetch ──────────────────────────────────────────────────────────────

def fetch_all_players():
    all_p = []
    offset = 0
    while True:
        resp = supabase.table("players").select(
            "id, name, position, team_id, player_tag, roster_status, "
            "is_on_depth_chart, depth_chart_rank, cfo_valuation, is_override"
        ).range(offset, offset + 999).execute()
        batch = resp.data or []
        all_p.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return all_p


def fetch_overrides():
    resp = supabase.table("nil_overrides").select("player_id, annualized_value").execute()
    return {str(r["player_id"]): r.get("annualized_value", 0) for r in (resp.data or [])}


def fetch_teams():
    resp = supabase.table("teams").select("id, university_name").execute()
    return {t["id"]: t["university_name"] for t in (resp.data or [])}


# ─── Report tracking ────────────────────────────────────────────────────────

class Report:
    def __init__(self):
        self.criticals = []
        self.warnings = []
        self.infos = []
        self.passes = []
        self.has_critical = False

    def critical_pass(self, msg):
        self.passes.append(("CRITICAL", msg))

    def critical_fail(self, msg, details=None):
        self.criticals.append((msg, details or []))
        self.has_critical = True

    def warn_pass(self, msg):
        self.passes.append(("WARNING", msg))

    def warn_fail(self, msg, details=None):
        self.warnings.append((msg, details or []))

    def info(self, msg):
        self.infos.append(msg)

    def print_report(self):
        now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"\n{'=' * 70}")
        print(f"  CFO VALUATION VALIDATION REPORT")
        print(f"  Run: {now}")
        print(f"{'=' * 70}")

        print(f"\n  CRITICAL ISSUES (must fix):")
        for level, msg in self.passes:
            if level == "CRITICAL":
                print(f"  [PASS] {msg}")
        for msg, details in self.criticals:
            print(f"  [FAIL] {msg}")
            for d in details[:10]:
                print(f"    - {d}")
            if len(details) > 10:
                print(f"    ... and {len(details) - 10} more")

        print(f"\n  WARNINGS (review):")
        for level, msg in self.passes:
            if level == "WARNING":
                print(f"  [PASS] {msg}")
        for msg, details in self.warnings:
            print(f"  [WARN] {msg}")
            for d in details[:10]:
                print(f"    - {d}")
            if len(details) > 10:
                print(f"    ... and {len(details) - 10} more")

        print(f"\n  INFO:")
        for msg in self.infos:
            print(f"  {msg}")

        status = "FAIL - CRITICAL ISSUES FOUND" if self.has_critical else "PASS - All critical checks passed"
        print(f"\n  {'=' * 70}")
        print(f"  STATUS: {status}")
        print(f"  Criticals: {len(self.criticals)}, Warnings: {len(self.warnings)}")
        print(f"  {'=' * 70}\n")


# ─── Category 1: Position Configuration ─────────────────────────────────────

def check_position_config(players, report, teams):
    valued = [p for p in players if p.get("cfo_valuation") is not None]
    positions_in_db = set(p.get("position") for p in valued if p.get("position"))
    known = set(POSITION_BASE_VALUES.keys())
    missing = positions_in_db - known

    if missing:
        details = []
        for pos in sorted(missing):
            count = sum(1 for p in valued if p.get("position") == pos)
            details.append(f"Position '{pos}': {count} valued players using ${DEFAULT_BASE_VALUE:,} default")
        report.critical_fail(f"{len(missing)} position(s) NOT in POSITION_BASE_VALUES", details)
    else:
        report.critical_pass("All valued positions mapped in POSITION_BASE_VALUES")

    # Position mapping info
    all_positions = sorted(set(p.get("position", "NULL") for p in players if p.get("position")))
    mapping_lines = []
    for pos in all_positions:
        base = POSITION_BASE_VALUES.get(pos, DEFAULT_BASE_VALUE)
        flag = "" if pos in known else " ** UNMAPPED (default)"
        mapping_lines.append(f"{pos}: ${base:,}{flag}")
    report.info("Position mapping: " + ", ".join(mapping_lines))


# ─── Category 2: Sanity Ceilings ────────────────────────────────────────────

def check_sanity_ceilings(players, report, teams):
    algo = [p for p in players if p.get("cfo_valuation") and not p.get("is_override")]

    # Kicker/punter above $250K
    high_kickers = [p for p in algo if p.get("position") in ("K", "PK", "P")
                    and p["cfo_valuation"] > 250_000]
    if high_kickers:
        details = [f"{p['name']} ({teams.get(p.get('team_id',''),'?')}, {p['position']}): ${p['cfo_valuation']:,}"
                   for p in sorted(high_kickers, key=lambda x: -x["cfo_valuation"])]
        report.warn_fail(f"{len(high_kickers)} kicker/punter above $250K", details)
    else:
        report.warn_pass("No kicker/punter above $250K")

    # Any player above $5M
    high_5m = [p for p in algo if p["cfo_valuation"] > 5_000_000]
    if high_5m:
        details = [f"{p['name']} ({teams.get(p.get('team_id',''),'?')}): ${p['cfo_valuation']:,}"
                   for p in high_5m]
        report.warn_fail(f"{len(high_5m)} non-override player above $5M", details)
    else:
        report.warn_pass("No non-override player above $5M")

    # Non-QB above $3M
    high_nonqb = [p for p in algo if p["cfo_valuation"] > 3_000_000
                  and p.get("position") != "QB"]
    if high_nonqb:
        details = [f"{p['name']} ({teams.get(p.get('team_id',''),'?')}, {p['position']}): ${p['cfo_valuation']:,}"
                   for p in high_nonqb]
        report.warn_fail(f"{len(high_nonqb)} non-QB non-override above $3M", details)
    else:
        report.warn_pass("No non-QB non-override above $3M")

    # Top 5 non-override
    top5 = sorted(algo, key=lambda x: -x["cfo_valuation"])[:5]
    report.info("Top 5 algorithmic valuations:")
    for i, p in enumerate(top5, 1):
        team = teams.get(p.get("team_id", ""), "?")
        report.info(f"  {i}. {p['name']} ({team}, {p.get('position','?')}): ${p['cfo_valuation']:,}")


# ─── Category 3: Rank Inversions ────────────────────────────────────────────

def check_rank_inversions(players, report, teams):
    # Group non-override DC players by (team_id, position)
    groups = defaultdict(list)
    for p in players:
        if (p.get("is_on_depth_chart") and p.get("depth_chart_rank") and
                p.get("cfo_valuation") and not p.get("is_override") and p.get("position")):
            key = (p.get("team_id"), p.get("position"))
            groups[key].append(p)

    inversions = []
    for (tid, pos), group in groups.items():
        ranked = sorted(group, key=lambda x: x["depth_chart_rank"])
        for i in range(len(ranked)):
            for j in range(i + 1, len(ranked)):
                if ranked[j]["cfo_valuation"] > ranked[i]["cfo_valuation"]:
                    team = teams.get(tid, "?")
                    inversions.append(
                        f"{team} {pos}: {ranked[i]['name']} (rank {ranked[i]['depth_chart_rank']}, "
                        f"${ranked[i]['cfo_valuation']:,}) < {ranked[j]['name']} "
                        f"(rank {ranked[j]['depth_chart_rank']}, ${ranked[j]['cfo_valuation']:,})"
                    )

    if inversions:
        report.warn_fail(f"{len(inversions)} rank inversions found", inversions)
    else:
        report.warn_pass("No rank inversions found")


# ─── Category 4: Data Integrity ─────────────────────────────────────────────

def check_data_integrity(players, overrides, report, teams):
    # is_override=true but no nil_overrides row
    override_players = [p for p in players if p.get("is_override")]
    orphan_overrides = [p for p in override_players if str(p["id"]) not in overrides]
    if orphan_overrides:
        details = [f"{p['name']} ({teams.get(p.get('team_id',''),'?')}): is_override=true, no nil_overrides row"
                   for p in orphan_overrides]
        report.critical_fail(f"{len(orphan_overrides)} orphan override(s)", details)
    else:
        report.critical_pass("All is_override=true players have nil_overrides rows")

    # nil_overrides row but is_override=false
    player_map = {str(p["id"]): p for p in players}
    stale_overrides = []
    for pid in overrides:
        p = player_map.get(pid)
        if p and not p.get("is_override"):
            stale_overrides.append(
                f"{p['name']} ({teams.get(p.get('team_id',''),'?')}): nil_overrides exists but is_override=false"
            )
    if stale_overrides:
        report.critical_fail(f"{len(stale_overrides)} stale override(s)", stale_overrides)
    else:
        report.critical_pass("All nil_overrides rows have is_override=true on player")

    # On DC but NULL valuation (non-override)
    dc_null = [p for p in players if p.get("is_on_depth_chart") and p.get("cfo_valuation") is None
               and not p.get("is_override") and p.get("player_tag") == "College Athlete"]
    if dc_null:
        details = [f"{p['name']} ({teams.get(p.get('team_id',''),'?')}, {p.get('position','?')})"
                   for p in dc_null[:10]]
        report.warn_fail(f"{len(dc_null)} on-DC player(s) with NULL valuation", details)
    else:
        report.warn_pass("All on-DC College Athletes have valuations")

    # NOT on DC but has valuation (non-override, College Athlete)
    off_dc_val = [p for p in players if not p.get("is_on_depth_chart")
                  and p.get("cfo_valuation") is not None and not p.get("is_override")
                  and p.get("player_tag") == "College Athlete"]
    if off_dc_val:
        details = [f"{p['name']} ({teams.get(p.get('team_id',''),'?')}): ${p['cfo_valuation']:,}"
                   for p in sorted(off_dc_val, key=lambda x: -x["cfo_valuation"])[:10]]
        report.warn_fail(f"{len(off_dc_val)} off-DC College Athlete(s) with valuation", details)
    else:
        report.warn_pass("No off-DC College Athletes with valuations")

    # Duplicate names on same team
    name_team = defaultdict(list)
    for p in players:
        if p.get("team_id") and p.get("name"):
            name_team[(p["name"], p["team_id"])].append(p)
    dupes = {k: v for k, v in name_team.items() if len(v) > 1}
    if dupes:
        details = [f"{name} on {teams.get(tid, '?')}: {len(recs)} records"
                   for (name, tid), recs in list(dupes.items())[:10]]
        report.warn_fail(f"{len(dupes)} duplicate name(s) on same team", details)
    else:
        report.warn_pass("No duplicate names on same team")

    # NULL position for valued players
    null_pos = [p for p in players if p.get("cfo_valuation") and not p.get("position")]
    if null_pos:
        details = [f"{p['name']} ({teams.get(p.get('team_id',''),'?')}): val=${p['cfo_valuation']:,}"
                   for p in null_pos]
        report.warn_fail(f"{len(null_pos)} valued player(s) with NULL position", details)
    else:
        report.warn_pass("All valued players have a position")


# ─── Category 5: Distribution Sanity ────────────────────────────────────────

def check_distribution(players, report, teams):
    valued = [p for p in players if p.get("cfo_valuation") and not p.get("is_override")]

    # By position stats
    pos_vals = defaultdict(list)
    for p in valued:
        pos = p.get("position", "?")
        pos_vals[pos].append(p["cfo_valuation"])

    report.info(f"Total valued players: {len(valued) + sum(1 for p in players if p.get('is_override') and p.get('cfo_valuation'))}")
    report.info(f"Total overrides: {sum(1 for p in players if p.get('is_override'))}")

    total_val = sum(p.get("cfo_valuation", 0) for p in players if p.get("cfo_valuation"))
    report.info(f"Total roster value: ${total_val:,}")

    report.info("Avg valuation by position (algorithmic only):")
    skewed = []
    for pos in sorted(pos_vals.keys()):
        vals = pos_vals[pos]
        avg = sum(vals) // len(vals)
        base = POSITION_BASE_VALUES.get(pos, DEFAULT_BASE_VALUE)
        ratio = avg / base if base else 0
        flag = ""
        if ratio > 2.0:
            flag = " ** HIGH"
            skewed.append(f"{pos}: avg ${avg:,} is {ratio:.1f}x base ${base:,}")
        elif ratio < 0.5:
            flag = " ** LOW"
            skewed.append(f"{pos}: avg ${avg:,} is {ratio:.1f}x base ${base:,}")
        report.info(f"  {pos:<5} n={len(vals):>4}  avg=${avg:>10,}  base=${base:>10,}  ratio={ratio:.2f}x{flag}")

    if skewed:
        report.warn_fail(f"{len(skewed)} position(s) with skewed avg vs base", skewed)
    else:
        report.warn_pass("All position averages within 0.5-2.0x of base")


# ─── Category 6: Override Health ─────────────────────────────────────────────

def check_overrides(players, overrides, report, teams):
    override_players = [p for p in players if p.get("is_override") and p.get("cfo_valuation")]
    report.info(f"Override count: {len(override_players)}")

    # List all overrides
    for p in sorted(override_players, key=lambda x: -x["cfo_valuation"]):
        team = teams.get(p.get("team_id", ""), "?")
        report.info(f"  {p['name']:<30} {team:<20} ${p['cfo_valuation']:,}")

    # Suspiciously low
    low = [p for p in override_players if p["cfo_valuation"] < 50_000]
    if low:
        details = [f"{p['name']}: ${p['cfo_valuation']:,}" for p in low]
        report.warn_fail(f"{len(low)} override(s) below $50K", details)
    else:
        report.warn_pass("No overrides below $50K")

    # Suspiciously high
    high = [p for p in override_players if p["cfo_valuation"] > 10_000_000]
    if high:
        details = [f"{p['name']}: ${p['cfo_valuation']:,}" for p in high]
        report.warn_fail(f"{len(high)} override(s) above $10M", details)
    else:
        report.warn_pass("No overrides above $10M")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("Loading data...")
    players = fetch_all_players()
    overrides = fetch_overrides()
    teams = fetch_teams()
    print(f"  {len(players):,} players, {len(overrides)} overrides, {len(teams)} teams\n")

    report = Report()

    check_position_config(players, report, teams)
    check_sanity_ceilings(players, report, teams)
    check_rank_inversions(players, report, teams)
    check_data_integrity(players, overrides, report, teams)
    check_distribution(players, report, teams)
    check_overrides(players, overrides, report, teams)

    report.print_report()
    sys.exit(1 if report.has_critical else 0)


if __name__ == "__main__":
    main()
