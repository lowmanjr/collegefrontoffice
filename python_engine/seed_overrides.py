"""
seed_overrides.py
------------------
Seeds the nil_overrides table with known multi-year NIL deals for Blue Chip
players. Looks up each player's cfbd_id from the players table by name, then
upserts the deal record. The database auto-calculates annualized_value
(total_value / years) via a generated column.

Usage:
    python seed_overrides.py

Requirements:
    pip install supabase python-dotenv
"""

import os
import re
import difflib
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

# ---------------------------------------------------------------------------
# 2. KNOWN NIL OVERRIDE DATA
# ---------------------------------------------------------------------------

OVERRIDES = [
    {
        "name":        "Bryce Underwood",
        "team":        "Michigan",
        "position":    "QB",
        "total_value": 12_000_000,
        "years":       4,
        "source_name": "Front Office Sports",
        "source_url":  "https://frontofficesports.com/bryce-underwood-michigan-nil-deal/",
    },
    {
        "name":        "Arch Manning",
        "team":        "Texas",
        "position":    "QB",
        "total_value": 6_800_000,
        "years":       1,
        "source_name": "The Athletic",
        "source_url":  "https://www.nytimes.com/athletic/5856711/2024/10/18/arch-manning-texas-nil-valuation/",
    },
    {
        "name":        "Sam Leavitt",
        "team":        "LSU",
        "position":    "QB",
        "total_value": 6_000_000,
        "years":       2,
        "source_name": "On3",
        "source_url":  "https://www.on3.com/nil/news/sam-leavitt-lsu-tigers-football-transfer-portal-nil-deal/",
    },
]

# ---------------------------------------------------------------------------
# 3. NAME NORMALIZATION
# ---------------------------------------------------------------------------

_SUFFIXES = re.compile(r"\b(jr\.?|sr\.?|ii|iii|iv|v)\b", re.IGNORECASE)
_PUNCT    = re.compile(r"[^\w\s]")


def normalize_name(name: str) -> str:
    name = name.lower()
    name = _SUFFIXES.sub("", name)
    name = _PUNCT.sub("", name)
    return " ".join(name.split())


# ---------------------------------------------------------------------------
# 4. PLAYER LOOKUP — resolve name → Supabase UUID
# ---------------------------------------------------------------------------

def fetch_player_index() -> dict[str, dict]:
    """
    Returns a dict of normalized_name → {id (UUID), name} for all College
    Athletes. No cfbd_id filter — we only need the UUID for the upsert.
    """
    PAGE_SIZE   = 1000
    all_players: list[dict] = []
    offset      = 0

    while True:
        resp = (
            supabase.table("players")
            .select("id, name")
            .eq("player_tag", "College Athlete")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = resp.data or []
        if not batch:
            break
        all_players.extend(batch)
        offset += PAGE_SIZE

    index: dict[str, dict] = {}
    for p in all_players:
        norm = normalize_name(p["name"])
        index[norm] = p

    print(f"  Player index built — {len(index)} College Athletes.\n")
    return index


def resolve_player_id(target_name: str, index: dict[str, dict]) -> tuple[str | None, str | None]:
    """
    Exact match first, then fuzzy at 0.85 cutoff.
    Returns (uuid, matched_name) or (None, None).
    """
    norm = normalize_name(target_name)

    if norm in index:
        p = index[norm]
        return p["id"], p["name"]

    matches = difflib.get_close_matches(norm, list(index.keys()), n=1, cutoff=0.85)
    if matches:
        p = index[matches[0]]
        return p["id"], p["name"]

    return None, None


def fetch_team_id(team_name: str) -> str | None:
    """
    Looks up a team's UUID from the teams table by university_name.
    Returns the UUID string or None if not found.
    """
    resp = (
        supabase.table("teams")
        .select("id")
        .eq("university_name", team_name)
        .limit(1)
        .execute()
    )
    if resp.data:
        return resp.data[0]["id"]
    return None


def ghost_inject(entry: dict, index: dict[str, dict]) -> tuple[str | None, str | None]:
    """
    Ghost Injector: when a player cannot be resolved from the existing player
    index, fetch their team from Supabase, physically INSERT them into the
    players table, and return (new_uuid, name) so the nil_overrides upsert
    can proceed normally.
    """
    team_id = fetch_team_id(entry["team"])
    if team_id is None:
        print(f"  [GHOST]   '{entry['name']}' — team '{entry['team']}' not found. Cannot inject.")
        return None, None

    insert_payload = {
        "name":       entry["name"],
        "team_id":    team_id,
        "position":   entry.get("position", "ATH"),
        "player_tag": "College Athlete",
        "class_year": 3,
    }

    resp = supabase.table("players").insert(insert_payload).execute()
    if not resp.data:
        print(f"  [GHOST]   '{entry['name']}' — insert returned no data. Check RLS / schema.")
        return None, None

    new_id = resp.data[0]["id"]

    # Add to the in-memory index so duplicate entries in OVERRIDES resolve correctly.
    index[normalize_name(entry["name"])] = {"id": new_id, "name": entry["name"]}

    print(f"  [GHOST]   '{entry['name']}' injected into players table  (id: {new_id})")
    return new_id, entry["name"]


# ---------------------------------------------------------------------------
# 5. UPSERT
# ---------------------------------------------------------------------------

def seed_overrides(index: dict[str, dict]) -> None:
    print("=" * 65)
    print("Seeding nil_overrides table...")
    print("=" * 65)

    inserted = 0
    failed   = 0

    for entry in OVERRIDES:
        target_name = entry["name"]
        player_id, matched_name = resolve_player_id(target_name, index)

        if player_id is None:
            print(f"  [WARN]    '{target_name}' — not found in index. Attempting Ghost Inject...")
            player_id, matched_name = ghost_inject(entry, index)
            if player_id is None:
                failed += 1
                continue

        if matched_name != target_name:
            print(f"  [FUZZY]   '{target_name}' matched to '{matched_name}' in DB.")

        aav = entry["total_value"] // entry["years"]

        payload = {
            "player_id":   player_id,
            "total_value": entry["total_value"],
            "years":       entry["years"],
            "source_name": entry["source_name"],
            "source_url":  entry["source_url"],
        }

        supabase.table("nil_overrides").upsert(
            payload, on_conflict="player_id"
        ).execute()

        print(
            f"  [OK]      {target_name:<22}  "
            f"${entry['total_value']:>12,}  /  {entry['years']}yr  "
            f"->  AAV ${aav:,}"
        )
        inserted += 1

    print(f"\n{'=' * 65}")
    print(f"Seeding complete.  {inserted} upserted,  {failed} skipped.")
    print("=" * 65)


# ---------------------------------------------------------------------------
# 6. MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    print("Fetching player index from Supabase...")
    index = fetch_player_index()
    seed_overrides(index)


if __name__ == "__main__":
    main()
