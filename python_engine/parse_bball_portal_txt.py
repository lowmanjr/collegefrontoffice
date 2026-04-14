"""
Parses python_engine/data/on3_basketballportal_raw.txt (raw On3
portal copy-paste) and applies roster changes to basketball_players.

Replaces the scraping half of the portal pipeline with a manual
txt file approach — more reliable, no alias issues, full control.

Same three operations as sync_bball_roster_from_portal.py:
  A) Committed moves between our tracked schools
  B) Committed to non-tracked schools → departed_transfer
  C) Evaluating from our schools → portal_evaluating badge

Usage:
  python parse_bball_portal_txt.py --parse-only   # just show parsed records
  python parse_bball_portal_txt.py --dry-run       # preview DB changes
  python parse_bball_portal_txt.py                 # apply changes
"""

import argparse
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from supabase_client import supabase

DATA_FILE = os.path.join(os.path.dirname(__file__),
                         "data", "on3_basketballportal_raw.txt")

POSITION_MAP = {
    "PG": "PG", "SG": "SG", "SF": "SF", "PF": "PF", "C": "C",
    "CG": "SG", "G": "SG", "F": "SF", "GF": "SF", "FC": "PF",
}

# Maps On3 school name variants → our basketball_teams.university_name
SCHOOL_ALIASES: dict[str, str] = {
    "byu": "BYU",
    "byu cougars": "BYU",
    "kentucky": "Kentucky",
    "kentucky wildcats": "Kentucky",
    "uconn": "UConn",
    "uconn huskies": "UConn",
    "connecticut": "UConn",
    "connecticut huskies": "UConn",
    "duke": "Duke",
    "duke blue devils": "Duke",
    "kansas": "Kansas",
    "kansas jayhawks": "Kansas",
    "michigan": "Michigan",
    "michigan wolverines": "Michigan",
    "georgia": "Georgia",
    "georgia bulldogs": "Georgia",
    "san diego state": "San Diego State",
    "san diego state aztecs": "San Diego State",
    "sdsu": "San Diego State",
    "providence": "Providence",
    "providence friars": "Providence",
    "louisville": "Louisville",
    "louisville cardinals": "Louisville",
    "oregon": "Oregon",
    "oregon ducks": "Oregon",
    "miami": "Miami",
    "miami hurricanes": "Miami",
    "miami (fl)": "Miami",
    "tennessee": "Tennessee",
    "tennessee volunteers": "Tennessee",
}

# Prevent false positives on exact-match collisions
SCHOOL_NON_MATCHES = {
    # Kansas / Arkansas overlap ("kansas" is a substring of "arkansas")
    "kansas state", "kansas state wildcats",
    "arkansas", "arkansas razorbacks",
    "arkansas-little rock", "little rock trojans",
    "arkansas-pine bluff", "arkansas pine bluff golden lions",
    "arkansas state", "arkansas state red wolves",
    "central arkansas", "central arkansas bears",
    "missouri-kansas city", "missouri-kansas city kangaroos",
    # Duke / Dukes overlap
    "james madison", "james madison dukes",
    "duquesne", "duquesne dukes",
    # Kentucky overlap
    "eastern kentucky", "eastern kentucky colonels",
    "western kentucky", "western kentucky hilltoppers",
    "northern kentucky", "northern kentucky norse",
    # Georgia overlap
    "west georgia", "west georgia wolves",
    "georgia tech", "georgia state", "georgia southern",
    # Tennessee overlap
    "tennessee state", "tennessee tech",
    "east tennessee", "east tennessee state",
    "middle tennessee", "middle tennessee blue raiders",
    # Michigan overlap
    "michigan state", "northern michigan", "western michigan",
    "eastern michigan", "central michigan",
    # Miami overlap
    "miami (oh)", "miami ohio", "miami redhawks",
    # Oregon overlap
    "oregon state", "oregon state beavers",
    # Connecticut overlap
    "central connecticut", "central connecticut state",
}

NAME_ALIASES: dict[str, str] = {
    "somto cyril": "somtochukwu cyril",
    "rob wright": "robert wright iii",
    "kennard davis": "kennard davis jr.",
    "richard barron": "rich barron",
    "jp estrella": "j.p. estrella",
    # add others as discovered
}

CLASS_YEARS = {
    "FR", "SO", "JR", "SR", "GR",
    "RS-FR", "RS-SO", "RS-JR", "RS-SR",
}


def normalize_school(raw: str | None) -> str | None:
    """Strip Avatar suffix, resolve via SCHOOL_ALIASES."""
    if not raw:
        return None
    cleaned = re.sub(r"\s*Avatar\s*$", "", raw, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\d+\.?\d*%.*$", "", cleaned).strip()
    low = cleaned.lower().strip()
    if not low or low in SCHOOL_NON_MATCHES:
        return None
    return SCHOOL_ALIASES.get(low)


def is_team_avatar(line: str) -> bool:
    """True if line is a school Avatar line (not 'Default Avatar')."""
    return line.endswith("Avatar") and line != "Default Avatar"


def parse_portal_file(filepath: str) -> list[dict]:
    """Parse raw On3 portal txt into structured records."""
    with open(filepath, encoding="utf-8") as f:
        raw_lines = [l.strip() for l in f]

    # Keep only non-empty lines; track original positions
    lines = [l for l in raw_lines if l]

    # Find every "Default Avatar" — each marks one player block
    block_starts = [i for i, l in enumerate(lines) if l == "Default Avatar"]

    records: list[dict] = []
    for b, start in enumerate(block_starts):
        end = block_starts[b + 1] if b + 1 < len(block_starts) else len(lines)
        block = lines[start:end]

        if len(block) < 4:
            continue

        # block[0] = "Default Avatar"
        pos_raw = block[1].upper().strip()
        position = POSITION_MAP.get(pos_raw)

        player_name = block[2].strip()
        if player_name.upper() in CLASS_YEARS or player_name == "Claim Profile":
            continue

        # Scan block for status
        status = None
        status_idx = None
        for j, line in enumerate(block):
            if line == "Committed":
                status = "committed"
                status_idx = j
                break
            elif line in ("Entered", "Expected"):
                status = "evaluating"
                status_idx = j
                break

        if status is None or status_idx is None:
            continue

        # Extract team Avatar lines after status
        origin_raw = None
        dest_raw = None

        if status == "committed":
            # First two school Avatar lines after "Committed"
            avatars: list[str] = []
            for k in range(status_idx + 1, len(block)):
                if is_team_avatar(block[k]):
                    avatars.append(block[k])
                    if len(avatars) == 2:
                        break
            origin_raw = avatars[0] if len(avatars) >= 1 else None
            dest_raw = avatars[1] if len(avatars) >= 2 else None
        else:
            # First school Avatar line after status (skip date line)
            for k in range(status_idx + 1, min(status_idx + 8, len(block))):
                if is_team_avatar(block[k]):
                    origin_raw = block[k]
                    break

        records.append({
            "player_name": player_name,
            "position": position,
            "status": status,
            "origin_school_raw": origin_raw,
            "dest_school_raw": dest_raw,
            "origin_canonical": normalize_school(origin_raw),
            "dest_canonical": normalize_school(dest_raw),
        })

    return records


# ── DB helpers ──────────────────────────────────────────────────────

def load_teams() -> tuple[dict[str, dict], dict[str, str]]:
    """Returns (by_name, id→university_name)."""
    rows = supabase.table("basketball_teams") \
        .select("id, university_name, market_multiplier").execute().data
    by_name = {t["university_name"]: t for t in rows}
    id_to_name = {t["id"]: t["university_name"] for t in rows}
    return by_name, id_to_name


def find_player(name: str, team_id: str) -> dict | None:
    normalized = NAME_ALIASES.get(name.lower().strip(), name.lower().strip())
    result = supabase.table("basketball_players") \
        .select("id, name, team_id, cfo_valuation, is_override, "
                "acquisition_type, roster_status") \
        .eq("team_id", team_id) \
        .eq("roster_status", "active") \
        .execute()
    for p in result.data:
        if p["name"].lower().strip() == normalized:
            return p
    return None


# ── Operations ──────────────────────────────────────────────────────

def apply_portal_changes(records: list[dict],
                         teams_by_name: dict[str, dict],
                         id_to_name: dict[str, str],
                         dry_run: bool = False) -> None:
    moved = departed = flagged = not_found = 0

    # ── A: Committed moves between our tracked schools ──
    print("=== A: Committed moves between our schools ===")
    for r in records:
        if r["status"] != "committed":
            continue
        if not r["origin_canonical"] or not r["dest_canonical"]:
            continue

        origin_team = teams_by_name.get(r["origin_canonical"])
        dest_team = teams_by_name.get(r["dest_canonical"])
        if not origin_team or not dest_team:
            continue

        player = find_player(r["player_name"], origin_team["id"])
        if not player:
            print(f"  NOT FOUND: {r['player_name']} at {r['origin_canonical']}")
            not_found += 1
            continue

        if player.get("is_override"):
            print(f"  SKIP (override): {r['player_name']}")
            continue

        val = f"${player.get('cfo_valuation') or 0:,}"
        print(f"  MOVE: {r['player_name']:28s} | "
              f"{r['origin_canonical']} -> {r['dest_canonical']} | {val}")

        if not dry_run:
            supabase.table("basketball_players").update({
                "team_id": dest_team["id"],
                "acquisition_type": "portal",
            }).eq("id", player["id"]).execute()
        moved += 1

    # ── B: Committed to non-tracked schools ──
    print()
    print("=== B: Departed to non-tracked schools ===")
    for r in records:
        if r["status"] != "committed":
            continue
        if not r["origin_canonical"]:
            continue
        if r["dest_canonical"]:
            continue  # handled in A

        origin_team = teams_by_name.get(r["origin_canonical"])
        if not origin_team:
            continue

        player = find_player(r["player_name"], origin_team["id"])
        if not player:
            print(f"  NOT FOUND: {r['player_name']} at {r['origin_canonical']}")
            not_found += 1
            continue

        dest_display = r["dest_school_raw"] or "unknown"
        dest_display = re.sub(r"\s*Avatar\s*$", "", dest_display).strip()
        print(f"  DEPART: {r['player_name']:28s} | "
              f"{r['origin_canonical']} -> {dest_display}")

        if not dry_run:
            supabase.table("basketball_players").update({
                "roster_status": "departed_transfer",
            }).eq("id", player["id"]).execute()
        departed += 1

    # ── C: Evaluating — flag as In Portal ──
    print()
    print("=== C: Evaluating — flag as In Portal ===")
    for r in records:
        if r["status"] != "evaluating":
            continue
        if not r["origin_canonical"]:
            continue

        origin_team = teams_by_name.get(r["origin_canonical"])
        if not origin_team:
            continue

        player = find_player(r["player_name"], origin_team["id"])
        if not player:
            not_found += 1
            continue

        print(f"  PORTAL: {r['player_name']:28s} | "
              f"{r['origin_canonical']} (evaluating)")

        if not dry_run:
            supabase.table("basketball_players").update({
                "acquisition_type": "portal_evaluating",
            }).eq("id", player["id"]).execute()
        flagged += 1

    print()
    print(f"Summary: {moved} moved, {departed} departed, "
          f"{flagged} flagged, {not_found} not found")
    if dry_run:
        print("DRY RUN — no changes written")


# ── Main ────────────────────────────────────────────────────────────

def main(dry_run: bool = False, parse_only: bool = False) -> None:
    print(f"Reading {DATA_FILE}...")
    records = parse_portal_file(DATA_FILE)

    committed = [r for r in records if r["status"] == "committed"]
    evaluating = [r for r in records if r["status"] == "evaluating"]
    print(f"Parsed {len(records)} portal entries")
    print(f"  Committed:  {len(committed)}")
    print(f"  Evaluating: {len(evaluating)}")
    print()

    # Show parsed records with school resolution
    print("=== PARSED RECORDS (involving our schools) ===")
    for r in records:
        has_origin = r["origin_canonical"] is not None
        has_dest = r["dest_canonical"] is not None
        if not has_origin and not has_dest:
            continue  # skip [NEITHER] in summary view

        tag = (
            "[BOTH OURS]" if has_origin and has_dest else
            "[ORIGIN OURS]" if has_origin else
            "[DEST OURS]"
        )
        origin = r["origin_canonical"] or f"[{r['origin_school_raw']}]"
        dest = r["dest_canonical"] or (
            f"[{r['dest_school_raw']}]" if r["dest_school_raw"] else "—"
        )
        status_tag = r["status"][:4]
        print(f"  {tag:14s} [{status_tag}] "
              f"{r['player_name']:28s} | {str(r['position'] or '?'):4s} | "
              f"{origin:20s} -> {dest}")

    # Count categories
    both = sum(1 for r in records
               if r["origin_canonical"] and r["dest_canonical"])
    origin_only = sum(1 for r in records
                      if r["origin_canonical"] and not r["dest_canonical"])
    dest_only = sum(1 for r in records
                    if not r["origin_canonical"] and r["dest_canonical"])
    neither = sum(1 for r in records
                  if not r["origin_canonical"] and not r["dest_canonical"])
    print()
    print(f"School resolution: {both} [BOTH OURS], "
          f"{origin_only} [ORIGIN OURS], {dest_only} [DEST OURS], "
          f"{neither} [NEITHER]")

    if parse_only:
        return

    print()
    teams_by_name, id_to_name = load_teams()
    apply_portal_changes(records, teams_by_name, id_to_name,
                         dry_run=dry_run)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--parse-only", action="store_true",
                        help="Only parse and display, no DB operations")
    args = parser.parse_args()
    main(dry_run=args.dry_run, parse_only=args.parse_only)
