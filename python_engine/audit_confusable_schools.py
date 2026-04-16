"""
audit_confusable_schools.py
----------------------------
Proactive, READ-ONLY audit for confusable school pair misassignments
(OPERATIONS.md §5.18).

Cross-references Supabase player data against CFBD's authoritative data
for 10 confusable school groups (e.g. Texas / Texas A&M / Texas Tech).

Also cross-references against the On3 transfer portal CSV — players whose
DB team assignment matches their portal destination are excluded from
the mismatch report (portal is authoritative over CFBD/ESPN).

Usage:
    python audit_confusable_schools.py

Output: formatted report of mismatches, no database writes.
"""

import csv
import sys
import os
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

# ─── Environment ─────────────────────────────────────────────────────────────

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))

CFBD_API_KEY = os.getenv("CFBD_API_KEY")
if not CFBD_API_KEY:
    print("[FATAL] Missing CFBD_API_KEY in .env.local")
    sys.exit(1)

from supabase_client import supabase
from name_utils import normalize_name, normalize_name_stripped, fuzzy_match_player

# ─── Constants ───────────────────────────────────────────────────────────────

CFBD_BASE = "https://api.collegefootballdata.com"
CFBD_HEADERS = {"Authorization": f"Bearer {CFBD_API_KEY}", "Accept": "application/json"}
TEAM_DELAY = 1  # seconds between CFBD roster requests

RECRUIT_YEAR = 2026
ROSTER_YEAR = 2025
PAGE_SIZE = 1000

CONFUSABLE_GROUPS = [
    ["Oklahoma", "Oklahoma State"],
    ["Iowa", "Iowa State"],
    ["Florida", "Florida State"],
    ["Texas", "Texas A&M", "Texas Tech"],
    ["Arizona", "Arizona State"],
    ["Kansas", "Kansas State"],
    ["Michigan", "Michigan State"],
    ["Georgia", "Georgia Tech"],
    ["North Carolina", "NC State"],
    ["Mississippi State", "Ole Miss"],
]

# CFBD school names that differ from our university_name
SCHOOL_ALIASES = {
    "ole miss": "Ole Miss",
    "miami (fl)": "Miami",
    "miami": "Miami",
    "usc": "USC",
    "ucf": "UCF",
    "lsu": "LSU",
    "byu": "BYU",
    "smu": "SMU",
    "nc state": "NC State",
    "north carolina state": "NC State",
    "pitt": "Pittsburgh",
    "cal": "Cal",
    "california": "Cal",
}

PORTAL_CSV = os.path.join(os.path.dirname(__file__), "data", "on3_portal_2026.csv")


# ─── Helper: Portal CSV loading ─────────────────────────────────────────────

def load_portal_destinations():
    """
    Load On3 transfer portal CSV and build a lookup of
    {normalized_player_name: destination_school}.

    Only includes committed transfers with a non-empty destination.
    If a player appears multiple times, the last entry wins.
    """
    portal = {}
    if not os.path.exists(PORTAL_CSV):
        print(f"  [WARN] Portal CSV not found at {PORTAL_CSV} — skipping portal cross-reference")
        return portal

    with open(PORTAL_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("Player") or "").strip()
            dest = (row.get("Destination") or "").strip()
            if name and dest:
                portal[normalize_name(name)] = dest
    return portal


# ─── Helper: Team loading ───────────────────────────────────────────────────

def load_teams():
    """Load teams from Supabase. Returns (id_to_name, name_to_id) dicts."""
    resp = supabase.table("teams").select("id, university_name").execute()
    rows = resp.data or []
    id_to_name = {t["id"]: t["university_name"] for t in rows}
    name_to_id = {t["university_name"]: t["id"] for t in rows}
    return id_to_name, name_to_id


def resolve_school_name(cfbd_name, name_to_id):
    """
    Map a CFBD school name to our DB university_name.

    4-tier strategy: direct → lowercase → alias → partial substring.
    Returns the matched university_name string, or None.
    """
    if not cfbd_name:
        return None

    # 1. Direct match
    if cfbd_name in name_to_id:
        return cfbd_name

    # 2. Case-insensitive match
    lower = cfbd_name.lower().strip()
    for db_name in name_to_id:
        if db_name.lower() == lower:
            return db_name

    # 3. Alias lookup
    if lower in SCHOOL_ALIASES:
        alias_target = SCHOOL_ALIASES[lower]
        if alias_target in name_to_id:
            return alias_target

    # 4. Partial substring match (both directions)
    for db_name in name_to_id:
        if lower in db_name.lower() or db_name.lower() in lower:
            return db_name

    return None


# ─── Helper: CFBD API fetches ───────────────────────────────────────────────

def fetch_all_cfbd_recruits():
    """
    Fetch all 2026 HS recruits from CFBD in a single API call.
    Returns list of dicts with 'name', 'school', 'position', 'stars'.
    """
    url = f"{CFBD_BASE}/recruiting/players?year={RECRUIT_YEAR}&classification=HighSchool"
    try:
        r = requests.get(url, headers=CFBD_HEADERS, timeout=60)
        if r.status_code == 401:
            print("[FATAL] 401 Unauthorized — check CFBD_API_KEY in .env.local")
            sys.exit(1)
        r.raise_for_status()
        raw = r.json()
    except requests.RequestException as exc:
        print(f"[API ERROR] Failed to fetch CFBD recruits: {exc}")
        return []

    recruits = []
    for rec in raw:
        name = (rec.get("name") or "").strip()
        school = (rec.get("committedTo") or "").strip()
        if not name:
            continue
        recruits.append({
            "name": name,
            "school_raw": school,
            "position": rec.get("position") or "?",
            "stars": rec.get("stars") or 0,
        })
    return recruits


def fetch_cfbd_roster(team_name):
    """
    Fetch CFBD roster for one team. Returns list of dicts with 'name', 'school'.
    """
    url = f"{CFBD_BASE}/roster?team={requests.utils.quote(team_name)}&year={ROSTER_YEAR}"
    try:
        r = requests.get(url, headers=CFBD_HEADERS, timeout=30)
        if r.status_code == 401:
            print("[FATAL] 401 Unauthorized — check CFBD_API_KEY in .env.local")
            sys.exit(1)
        r.raise_for_status()
        raw = r.json()
    except requests.RequestException as exc:
        print(f"  [API ERROR] Failed to fetch roster for {team_name}: {exc}")
        return None  # None signals error (vs empty list which means 0 players)

    entries = []
    for p in raw:
        first = (p.get("first_name") or p.get("firstName") or "").strip()
        last = (p.get("last_name") or p.get("lastName") or "").strip()
        full_name = f"{first} {last}".strip() if (first or last) else (p.get("name") or "").strip()
        if not full_name:
            continue
        entries.append({
            "name": full_name,
            "school": team_name,
        })
    return entries


# ─── Helper: Supabase player fetch ──────────────────────────────────────────

def fetch_db_players_for_teams(team_ids):
    """
    Paginated fetch of active players for a set of team_ids.
    Returns (hs_recruits, college_athletes) tuple of lists.
    """
    all_players = []
    for tid in team_ids:
        offset = 0
        while True:
            resp = (
                supabase.table("players")
                .select("id, name, position, star_rating, player_tag, team_id, roster_status")
                .eq("team_id", tid)
                .eq("roster_status", "active")
                .range(offset, offset + PAGE_SIZE - 1)
                .execute()
            )
            batch = resp.data or []
            all_players.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

    hs = [p for p in all_players if p.get("player_tag") == "High School Recruit"]
    ca = [p for p in all_players if p.get("player_tag") == "College Athlete"]
    return hs, ca


# ─── Core audit logic ───────────────────────────────────────────────────────

def audit_group(group, cfbd_recruits_all, id_to_name, name_to_id, portal_destinations):
    """
    Audit one confusable school group.

    Returns (hs_mismatches, ca_mismatches, portal_excluded, api_errors) where
    each mismatch/exclusion is a dict with 'name', 'position', 'stars',
    'db_school', 'cfbd_school'.
    """
    group_label = " / ".join(group)
    api_errors = 0
    portal_excluded = []

    # Resolve team_ids for this group
    group_team_ids = {}
    for school in group:
        tid = name_to_id.get(school)
        if tid:
            group_team_ids[school] = tid
        else:
            print(f"  [WARN] School '{school}' not found in teams table — skipping")

    if not group_team_ids:
        return [], [], 0

    id_set = set(group_team_ids.values())
    group_schools_lower = {s.lower(): s for s in group_team_ids}

    # ── CFBD HS Recruits for this group ──────────────────────────────────
    cfbd_hs_pool = []
    for rec in cfbd_recruits_all:
        resolved = resolve_school_name(rec["school_raw"], name_to_id)
        if resolved and resolved in group_team_ids:
            cfbd_hs_pool.append({
                "name": rec["name"],
                "school": resolved,
                "position": rec["position"],
                "stars": rec["stars"],
            })

    # ── CFBD Rosters for this group ──────────────────────────────────────
    cfbd_roster_pool = []
    for school in group_team_ids:
        roster = fetch_cfbd_roster(school)
        if roster is None:
            api_errors += 1
        else:
            cfbd_roster_pool.extend(roster)
        time.sleep(TEAM_DELAY)

    # ── DB players for this group ────────────────────────────────────────
    db_hs, db_ca = fetch_db_players_for_teams(id_set)

    # ── Cross-reference: HS Recruits ─────────────────────────────────────
    hs_mismatches = []
    for db_player in db_hs:
        db_school = id_to_name.get(db_player["team_id"], "?")
        if not cfbd_hs_pool:
            continue
        match = fuzzy_match_player(db_player["name"], cfbd_hs_pool, threshold=0.85)
        if match:
            cfbd_school = match.player["school"]
            if cfbd_school != db_school:
                entry = {
                    "name": db_player["name"],
                    "position": db_player.get("position") or "?",
                    "stars": db_player.get("star_rating") or 0,
                    "db_school": db_school,
                    "cfbd_school": cfbd_school,
                    "match_method": match.method,
                    "match_score": match.score,
                }
                # Portal cross-reference: if portal confirms DB school, exclude
                norm = normalize_name(db_player["name"])
                portal_dest = portal_destinations.get(norm)
                if portal_dest and portal_dest == db_school:
                    portal_excluded.append(entry)
                else:
                    hs_mismatches.append(entry)

    # ── Cross-reference: College Athletes ────────────────────────────────
    ca_mismatches = []
    for db_player in db_ca:
        db_school = id_to_name.get(db_player["team_id"], "?")
        if not cfbd_roster_pool:
            continue
        match = fuzzy_match_player(db_player["name"], cfbd_roster_pool, threshold=0.85)
        if match:
            cfbd_school = match.player["school"]
            if cfbd_school != db_school:
                entry = {
                    "name": db_player["name"],
                    "position": db_player.get("position") or "?",
                    "stars": db_player.get("star_rating") or 0,
                    "db_school": db_school,
                    "cfbd_school": cfbd_school,
                    "match_method": match.method,
                    "match_score": match.score,
                }
                # Portal cross-reference: if portal confirms DB school, exclude
                norm = normalize_name(db_player["name"])
                portal_dest = portal_destinations.get(norm)
                if portal_dest and portal_dest == db_school:
                    portal_excluded.append(entry)
                else:
                    ca_mismatches.append(entry)

    return hs_mismatches, ca_mismatches, portal_excluded, api_errors


# ─── Output formatting ──────────────────────────────────────────────────────

def star_str(stars):
    if stars and stars > 0:
        return f"{stars}\u2605"
    return ""


def print_group_report(group, hs_mismatches, ca_mismatches, portal_excluded):
    group_label = " / ".join(group)
    print(f"\n=== GROUP: {group_label} ===")

    if not hs_mismatches and not ca_mismatches and not portal_excluded:
        print("  (no mismatches found)")
        return

    # HS Recruits
    print(f"  HS Recruit mismatches ({len(hs_mismatches)}):")
    if hs_mismatches:
        for m in hs_mismatches:
            stars = star_str(m["stars"])
            stars_part = f", {stars}" if stars else ""
            print(
                f"    - {m['name']} ({m['position']}{stars_part}): "
                f"DB says {m['db_school']}, CFBD says {m['cfbd_school']}  "
                f"[{m['match_method']}, {m['match_score']:.2f}]"
            )
    else:
        print("    (none)")

    # College Athletes
    print(f"  College Athlete mismatches ({len(ca_mismatches)}):")
    if ca_mismatches:
        for m in ca_mismatches:
            stars = star_str(m["stars"])
            stars_part = f", {stars}" if stars else ""
            print(
                f"    - {m['name']} ({m['position']}{stars_part}): "
                f"DB says {m['db_school']}, CFBD says {m['cfbd_school']}  "
                f"[{m['match_method']}, {m['match_score']:.2f}]"
            )
    else:
        print("    (none)")

    # Portal-verified exclusions
    if portal_excluded:
        print(f"  Excluded — portal-verified ({len(portal_excluded)}):")
        for m in portal_excluded:
            stars = star_str(m["stars"])
            stars_part = f", {stars}" if stars else ""
            print(
                f"    - {m['name']} ({m['position']}{stars_part}): "
                f"DB says {m['db_school']}, CFBD says {m['cfbd_school']} "
                f"→ portal confirms {m['db_school']}"
            )


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    print("=" * 70)
    print("  CONFUSABLE SCHOOL PAIR AUDIT")
    print(f"  Run: {run_ts}")
    print(f"  CFBD recruit year: {RECRUIT_YEAR}, roster year: {ROSTER_YEAR}")
    print("=" * 70)

    # Load teams
    print("\nLoading teams from Supabase...")
    id_to_name, name_to_id = load_teams()
    print(f"  {len(id_to_name)} teams loaded")

    # Load portal destinations (authoritative source for team assignments)
    print("Loading On3 transfer portal CSV...")
    portal_destinations = load_portal_destinations()
    print(f"  {len(portal_destinations)} committed transfers loaded")

    # Fetch all CFBD HS recruits (single API call)
    print(f"Fetching CFBD {RECRUIT_YEAR} HS recruits...")
    cfbd_recruits = fetch_all_cfbd_recruits()
    print(f"  {len(cfbd_recruits)} recruits fetched")

    # Audit each group
    total_hs = 0
    total_ca = 0
    total_excluded = 0
    total_api_errors = 0
    groups_audited = 0

    print(f"\nAuditing {len(CONFUSABLE_GROUPS)} confusable groups...")
    print(f"(fetching CFBD rosters with {TEAM_DELAY}s delay between calls)\n")

    for group in CONFUSABLE_GROUPS:
        group_label = " / ".join(group)
        print(f"  Checking: {group_label} ...", end=" ", flush=True)

        hs_mm, ca_mm, excluded, errs = audit_group(
            group, cfbd_recruits, id_to_name, name_to_id, portal_destinations
        )

        total_hs += len(hs_mm)
        total_ca += len(ca_mm)
        total_excluded += len(excluded)
        total_api_errors += errs
        groups_audited += 1

        found = len(hs_mm) + len(ca_mm)
        excl_note = f", {len(excluded)} portal-verified" if excluded else ""
        err_note = f" ({errs} API error(s))" if errs else ""
        print(f"{found} mismatch(es){excl_note}{err_note}")

        print_group_report(group, hs_mm, ca_mm, excluded)

    # Summary
    total_review = total_hs + total_ca
    print()
    print("=" * 70)
    print("  SUMMARY")
    print(f"  Total groups audited:              {groups_audited}")
    print(f"  Total HS recruit mismatches:       {total_hs}")
    print(f"  Total college athlete mismatches:   {total_ca}")
    print(f"  Total players to review:           {total_review}")
    print(f"  Excluded (portal-verified):        {total_excluded}")
    if total_api_errors:
        print(f"  CFBD API errors:                   {total_api_errors}")
    print("=" * 70)


if __name__ == "__main__":
    main()
