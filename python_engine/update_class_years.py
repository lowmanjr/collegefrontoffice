"""
update_class_years.py
----------------------
Populates the class_year (text) column for every player in Supabase.

College Athletes (have a cfbd_id):
  Hit CFBD /roster once per team → build a dict of cfbd_id → year label.
  CFBD returns year as an integer:  1=FR  2=SO  3=JR  4=SR  5=GR (graduate)
  Write that label directly to class_year.

High School Recruits (no cfbd_id / tagged 'High School Recruit'):
  Use the integer recruiting class already stored in class_year
  (written there by enrich_class_years.py) to pick a label:
    2025      → 'HS_SR'   (graduating seniors)
    2026+     → 'HS_JR'   (committed juniors)
    null/other → 'HS_SR'  (safe default)

Usage:
    python update_class_years.py

Requirements:
    pip install supabase python-dotenv requests
"""

import os
import time
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# 1. SETUP
# ---------------------------------------------------------------------------

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))

SUPABASE_URL      = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise EnvironmentError("Missing Supabase credentials in .env.local")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

CFBD_API_KEY = os.getenv("CFBD_API_KEY")
if not CFBD_API_KEY:
    raise EnvironmentError("Missing CFBD_API_KEY in .env.local")

CFBD_HEADERS   = {"Authorization": f"Bearer {CFBD_API_KEY}", "Accept": "application/json"}
CFBD_YEAR      = 2025
CFBD_ROSTER_URL = "https://api.collegefootballdata.com/roster"
TEAM_DELAY     = 1  # seconds between CFBD requests

# CFBD integer year → our class_year label
CFBD_YEAR_MAP: dict[int, str] = {
    1: "FR",
    2: "SO",
    3: "JR",
    4: "SR",
    5: "GR",  # graduate / 5th-year
}

# ---------------------------------------------------------------------------
# 2. PASS 1 — BUILD CFBD YEAR DICT
# ---------------------------------------------------------------------------

def fetch_teams() -> list[str]:
    print("Fetching teams from Supabase...")
    resp = supabase.table("teams").select("university_name").execute()
    names = [row["university_name"] for row in (resp.data or [])]
    print(f"  {len(names)} team(s) loaded.\n")
    return names


def build_cfbd_year_dict(team_names: list[str]) -> dict[int, str]:
    """
    Fetch CFBD /roster for each team and return a dict of:
        cfbd_id (int) → class_year label (str)
    """
    year_dict: dict[int, str] = {}
    api_errors = 0

    print("=" * 65)
    print(f"Fetching CFBD rosters (year={CFBD_YEAR})...")
    print("=" * 65)

    for team_name in team_names:
        print(f"  [{team_name}]... ", end="", flush=True)

        try:
            r = requests.get(
                CFBD_ROSTER_URL,
                headers=CFBD_HEADERS,
                params={"year": CFBD_YEAR, "team": team_name},
                timeout=20,
            )
            if r.status_code == 401:
                print("\n[ERROR] 401 Unauthorized — check CFBD_API_KEY in .env.local.")
                raise SystemExit(1)
            r.raise_for_status()
            players: list[dict] = r.json()
        except requests.RequestException as exc:
            print(f"[ERROR] {exc}")
            api_errors += 1
            time.sleep(TEAM_DELAY)
            continue

        matched = 0
        for p in players:
            raw_id  = p.get("id")
            raw_year = p.get("year")
            if raw_id is None or raw_year is None:
                continue
            try:
                cfbd_id   = int(raw_id)
                year_int  = int(raw_year)
            except (TypeError, ValueError):
                continue
            label = CFBD_YEAR_MAP.get(year_int)
            if label:
                year_dict[cfbd_id] = label
                matched += 1

        print(f"{len(players)} players, {matched} with year labels  (dict total: {len(year_dict)})")
        time.sleep(TEAM_DELAY)

    print(f"\nCFBD fetch complete. {len(year_dict)} players in year dict.")
    if api_errors:
        print(f"  ({api_errors} team request(s) failed — those players will be skipped)")
    print()
    return year_dict


# ---------------------------------------------------------------------------
# 3. PASS 2 — FETCH ALL SUPABASE PLAYERS
# ---------------------------------------------------------------------------

def fetch_all_players() -> list[dict]:
    """
    Returns all players with the columns needed to assign class_year:
      - College Athletes: need cfbd_id
      - HS Recruits: need existing class_year (integer recruiting year)
    """
    PAGE_SIZE   = 1000
    all_players: list[dict] = []
    offset      = 0

    print("Fetching all players from Supabase...")
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, player_tag, cfbd_id, class_year")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    print(f"  {len(all_players)} total player(s) fetched.\n")
    return all_players


# ---------------------------------------------------------------------------
# 4. CLASS YEAR ASSIGNMENT
# ---------------------------------------------------------------------------

def hs_label_from_recruit_year(raw_class_year) -> str:
    """
    Map an integer recruiting year stored in class_year to an HS label.
      2025      → 'HS_SR'
      2026+     → 'HS_JR'
      null/other → 'HS_SR' (default)
    """
    if raw_class_year is None:
        return "HS_SR"
    try:
        year_int = int(raw_class_year)
    except (TypeError, ValueError):
        return "HS_SR"
    return "HS_SR" if year_int <= 2025 else "HS_JR"


def assign_class_years(
    players: list[dict],
    cfbd_year_dict: dict[int, str],
) -> list[dict]:
    """
    Return a list of {'id': ..., 'class_year': ...} update payloads.
    Players that can't be resolved are skipped (no update written).
    """
    updates: list[dict] = []
    skipped = 0

    for player in players:
        tag     = (player.get("player_tag") or "").strip()
        raw_cid = player.get("cfbd_id")

        if tag == "College Athlete" and raw_cid is not None:
            # Deterministic CFBD lookup
            try:
                cfbd_id = int(raw_cid)
            except (TypeError, ValueError):
                skipped += 1
                continue
            label = cfbd_year_dict.get(cfbd_id)
            if label is None:
                skipped += 1
                continue

        elif tag == "High School Recruit" or raw_cid is None:
            # Use the integer recruiting year already in class_year
            label = hs_label_from_recruit_year(player.get("class_year"))

        else:
            skipped += 1
            continue

        updates.append({"id": player["id"], "class_year": label})

    return updates


# ---------------------------------------------------------------------------
# 5. SUPABASE UPDATE
# ---------------------------------------------------------------------------

def write_updates(updates: list[dict]) -> None:
    """
    Iterate through updates and write each class_year to Supabase.
    Prints a progress ticker every 200 rows.
    """
    errors = 0
    for i, row in enumerate(updates, start=1):
        try:
            supabase.table("players").update(
                {"class_year": row["class_year"]}
            ).eq("id", row["id"]).execute()
        except Exception as exc:
            print(f"  [ERROR] id={row['id']}: {exc}")
            errors += 1
            continue

        if i % 200 == 0:
            print(f"  {i} / {len(updates)} written...")

    return errors


# ---------------------------------------------------------------------------
# 6. MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    # Build CFBD lookup dict
    team_names    = fetch_teams()
    cfbd_year_dict = build_cfbd_year_dict(team_names) if team_names else {}

    # Fetch all players
    players = fetch_all_players()
    if not players:
        print("No players found. Exiting.")
        return

    # Assign labels
    updates = assign_class_years(players, cfbd_year_dict)

    if not updates:
        print("No class_year updates to write. Exiting.")
        return

    # Count by label for summary
    label_counts: dict[str, int] = {}
    for row in updates:
        label_counts[row["class_year"]] = label_counts.get(row["class_year"], 0) + 1

    print("=" * 65)
    print(f"Writing {len(updates)} class_year updates to Supabase...")
    print("=" * 65)

    errors = write_updates(updates)

    skipped = len(players) - len(updates)

    print(f"\n{'=' * 65}")
    print(f"Class year enrichment complete.")
    print(f"  Players updated     : {len(updates) - errors}")
    print(f"  Players skipped     : {skipped}  (no cfbd_id match / untagged)")
    print(f"  Errors              : {errors}")
    print(f"\n  Breakdown by label:")
    for label, count in sorted(label_counts.items()):
        print(f"    {label:<8}  {count:,}")
    print("=" * 65)


if __name__ == "__main__":
    main()
