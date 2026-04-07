"""
apply_overrides.py
-------------------
Reads approved overrides from python_engine/data/approved_overrides.csv and
applies them to the database:
  1. Inserts/updates nil_overrides rows
  2. Sets is_override = true on the player record

CSV format:
    player_name,total_value,years,annualized_value,source_name,source_url,verified
    - verified = "yes" means URL points to an actual article about this deal
    - verified = "no" or empty means On3 algorithmic valuation (not a reported deal)

Usage:
    python apply_overrides.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import csv
import datetime
import requests
from difflib import SequenceMatcher
from supabase_client import supabase

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "approved_overrides.csv")

GENERIC_URL_PATTERNS = ["/nil/rankings/", "/rankings/player/"]


def normalize(s):
    return (s or "").lower().strip().replace(".", "").replace("'", "").replace("-", " ")


def fuzzy_score(a, b):
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def validate_source_url(url, source_name):
    """Validate source URL format. Returns (is_valid, warning_msg)."""
    if not url:
        return False, "No source URL provided"
    if not url.startswith("https://"):
        return False, f"URL must start with https:// (got: {url[:50]})"
    for pattern in GENERIC_URL_PATTERNS:
        if pattern in url:
            return False, f"Generic rankings URL detected ({pattern})"
    return True, None


def verify_url_live(url: str) -> tuple[bool, str]:
    """HTTP check that URL actually resolves to 200. Returns (ok, message)."""
    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=10, allow_redirects=True)
        if resp.status_code == 200:
            return True, "200 OK"
        return False, f"HTTP {resp.status_code}"
    except requests.exceptions.RequestException as exc:
        return False, str(exc)[:60]


def fetch_all_players():
    all_p = []
    offset = 0
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, is_override")
            .range(offset, offset + 999)
            .execute()
        )
        batch = resp.data or []
        all_p.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return all_p


def find_player(name, players):
    """Find player by exact or fuzzy name match."""
    for p in players:
        if normalize(p["name"]) == normalize(name):
            return p

    best = None
    best_score = 0
    for p in players:
        score = fuzzy_score(name, p["name"])
        if score > best_score:
            best_score = score
            best = p

    if best and best_score >= 0.85:
        print(f"    [Fuzzy match] '{name}' -> '{best['name']}' (score: {best_score:.2f})")
        return best

    return None


def main():
    if not os.path.exists(CSV_PATH):
        print(f"No CSV found at {CSV_PATH}")
        print("Create it with columns: player_name,total_value,years,annualized_value,source_name,source_url,verified")
        return

    print("=" * 80)
    print("  APPLY OVERRIDES")
    print("=" * 80)

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r.get("player_name", "").strip()]

    print(f"  Read {len(rows)} override(s) from CSV.\n")

    if not rows:
        print("  No overrides to apply.")
        return

    players = fetch_all_players()
    now = datetime.datetime.utcnow().isoformat()

    created = 0
    updated = 0
    errors = 0
    skipped = 0
    source_warnings = 0

    for row in rows:
        name = row["player_name"].strip()
        total_value = int(row.get("total_value", 0) or 0)
        years = float(row.get("years", 1) or 1)
        annualized = int(row.get("annualized_value", 0) or 0)
        source_name = row.get("source_name", "").strip() or None
        source_url = row.get("source_url", "").strip() or None
        verified = (row.get("verified", "") or "").strip().lower()

        if not annualized:
            print(f"  [SKIP] {name}: no annualized_value")
            skipped += 1
            continue

        # Handle unverified sources: mark as algorithmic
        if verified != "yes":
            if source_name and "(algorithmic)" not in source_name:
                source_name = f"{source_name} (algorithmic)"

        # Validate source URL
        print(f"  Processing: {name} -- ${annualized:,}/yr")
        url_valid, url_warning = validate_source_url(source_url, source_name)
        if not url_valid:
            if source_url:
                print(f"    [WARNING] UNVERIFIED SOURCE: {url_warning}")
            source_url = None
            source_warnings += 1
        elif verified == "yes" and source_url:
            # Live-check verified URLs
            url_ok, url_msg = verify_url_live(source_url)
            if not url_ok:
                print(f"    [WARNING] URL VERIFICATION FAILED: {source_url[:60]} -> {url_msg}")
                source_url = None
                verified = "no"
                if source_name and "(algorithmic)" not in source_name:
                    source_name = f"{source_name} (algorithmic)"
                source_warnings += 1

        # Find player
        player = find_player(name, players)
        if not player:
            print(f"    [ERROR] Player not found: '{name}'")
            errors += 1
            continue

        pid = str(player["id"])

        # Check existing nil_overrides
        existing = supabase.table("nil_overrides").select("player_id, annualized_value").eq("player_id", pid).execute()
        existing_rows = existing.data or []

        if existing_rows:
            old_val = existing_rows[0]["annualized_value"]
            if old_val == annualized:
                print(f"    [SKIP] Already has override at ${annualized:,} -- no change needed.")
                skipped += 1
            else:
                supabase.table("nil_overrides").update({
                    "total_value": total_value,
                    "years": years,
                    "source_name": source_name,
                    "source_url": source_url,
                }).eq("player_id", pid).execute()
                print(f"    [UPDATED] nil_overrides: ${old_val:,} -> ${annualized:,}")
                updated += 1
        else:
            supabase.table("nil_overrides").insert({
                "player_id": pid,
                "name": name,
                "total_value": total_value,
                "years": years,
                "source_name": source_name,
                "source_url": source_url,
            }).execute()
            print(f"    [CREATED] nil_overrides: ${annualized:,}")
            created += 1

        # Set is_override = true
        if player.get("is_override") is not True:
            supabase.table("players").update({
                "is_override": True,
                "last_updated": now,
            }).eq("id", pid).execute()
            print(f"    [SET] is_override = true")
        else:
            print(f"    is_override already true")

    print(f"\n{'=' * 80}")
    print(f"  SUMMARY")
    print(f"{'=' * 80}")
    print(f"  Overrides created:  {created}")
    print(f"  Overrides updated:  {updated}")
    print(f"  Skipped (no change): {skipped}")
    print(f"  Errors:             {errors}")
    print(f"  Source warnings:    {source_warnings}")
    print(f"  Total processed:    {len(rows)}")
    print(f"\n  Next step: Run 'python calculate_cfo_valuations.py' to apply overrides to valuations.")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
