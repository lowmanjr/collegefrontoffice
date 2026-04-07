"""
clean_duplicates.py
--------------------
Finds and removes duplicate College Athlete rows in Supabase.

Duplicates are identified by the composite key: team_id + normalized name.
Within each duplicate group, the row with the highest cfo_valuation is kept
(most complete profile). All others are deleted.

Usage:
    python clean_duplicates.py

Requirements:
    pip install supabase python-dotenv
"""

import os
import re
from collections import defaultdict
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
# 2. NAME NORMALIZATION
# ---------------------------------------------------------------------------

_SUFFIXES = re.compile(r"\b(jr\.?|sr\.?|ii|iii|iv|v)\b", re.IGNORECASE)
_PUNCT    = re.compile(r"[^\w\s]")


def normalize_name(name: str) -> str:
    name = name.lower()
    name = _SUFFIXES.sub("", name)
    name = _PUNCT.sub("", name)
    return " ".join(name.split())


# ---------------------------------------------------------------------------
# 3. FETCH
# ---------------------------------------------------------------------------

def fetch_players() -> list[dict]:
    PAGE_SIZE   = 1000
    all_players: list[dict] = []
    offset      = 0

    print("Fetching College Athletes from Supabase...")
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, team_id, cfo_valuation")
            .eq("player_tag", "College Athlete")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = resp.data or []
        if not batch:
            break
        all_players.extend(batch)
        print(f"  Fetched {len(all_players)} players so far...")
        offset += PAGE_SIZE

    print(f"  Done. {len(all_players)} total player(s) fetched.\n")
    return all_players


# ---------------------------------------------------------------------------
# 4. GROUP & IDENTIFY DUPLICATES
# ---------------------------------------------------------------------------

def find_duplicates(players: list[dict]) -> list[list[dict]]:
    """
    Group players by (team_id, normalized_name).
    Returns only groups that contain more than one row.
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)

    for player in players:
        team_id = player.get("team_id") or "__no_team__"
        norm    = normalize_name(player.get("name") or "")
        key     = (team_id, norm)
        groups[key].append(player)

    return [group for group in groups.values() if len(group) > 1]


# ---------------------------------------------------------------------------
# 5. DELETE
# ---------------------------------------------------------------------------

def delete_duplicates(duplicate_groups: list[list[dict]]) -> int:
    """
    For each duplicate group, keep the row with the highest cfo_valuation
    and delete the rest. Returns the total number of rows deleted.
    """
    ids_to_delete: list[str] = []

    print("=" * 65)
    print("Duplicate groups found:")
    print("=" * 65)

    for group in duplicate_groups:
        # Best profile first: highest cfo_valuation wins ties by insertion order
        group.sort(key=lambda p: p.get("cfo_valuation") or 0, reverse=True)

        keep   = group[0]
        purge  = group[1:]

        print(
            f"  KEEP   id={keep['id']}  "
            f"name='{keep['name']}'  val=${keep.get('cfo_valuation') or 0:,}"
        )
        for dup in purge:
            print(
                f"  DELETE id={dup['id']}  "
                f"name='{dup['name']}'  val=${dup.get('cfo_valuation') or 0:,}"
            )
            ids_to_delete.append(dup["id"])
        print()

    if not ids_to_delete:
        return 0

    # Delete in chunks of 100 to stay well under URL length limits
    CHUNK_SIZE = 100
    deleted    = 0

    print(f"Deleting {len(ids_to_delete)} duplicate row(s) in chunks of {CHUNK_SIZE}...")
    for i in range(0, len(ids_to_delete), CHUNK_SIZE):
        chunk = ids_to_delete[i : i + CHUNK_SIZE]
        supabase.table("players").delete().in_("id", chunk).execute()
        deleted += len(chunk)
        print(f"  Deleted {deleted} / {len(ids_to_delete)}...")

    return deleted


# ---------------------------------------------------------------------------
# 6. MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    players = fetch_players()
    if not players:
        print("No College Athletes found. Exiting.")
        return

    duplicate_groups = find_duplicates(players)

    if not duplicate_groups:
        print("No duplicates found. Database is clean.")
        return

    total_dupes = sum(len(g) - 1 for g in duplicate_groups)
    print(f"Found {len(duplicate_groups)} duplicate group(s) — {total_dupes} row(s) to delete.\n")

    deleted = delete_duplicates(duplicate_groups)

    print("=" * 65)
    print(f"Cleanup complete. {deleted} duplicate row(s) deleted.")
    print("=" * 65)


if __name__ == "__main__":
    main()
