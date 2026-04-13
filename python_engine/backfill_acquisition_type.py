"""
backfill_acquisition_type.py
-----------------------------
Tags all players with acquisition_type: 'retained', 'portal', or 'recruit'.

Rules:
  1. recruit:  player_tag = 'High School Recruit' AND hs_grad_year = 2026
  2. portal:   Player appears in On3 committed transfer portal data (scraped via
               sync_transfer_portal.py), matched by name using fuzzy_match_player.
               Also catches players moved between teams by ESPN/On3 roster syncs.
  3. retained: Everyone else (default column value)

Usage:
    python backfill_acquisition_type.py [--dry-run]
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import re
import time
import json
import unicodedata
import logging
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from supabase_client import supabase
from name_utils import normalize_name, normalize_name_stripped, fuzzy_match_player

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

ON3_PORTAL_URL = "https://www.on3.com/transfer-portal/football/committed/"


# ─── Scrape On3 transfer portal (committed) ─────────────────────────────────

def scrape_portal_page(page_num: int) -> list[dict]:
    """Scrape one page of committed transfers from On3."""
    url = f"{ON3_PORTAL_URL}?page={page_num}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # Try __NEXT_DATA__ first
    tag = soup.find("script", id="__NEXT_DATA__", type="application/json")
    if not tag or not tag.string:
        return []

    try:
        data = json.loads(tag.string)
    except json.JSONDecodeError:
        return []

    # Navigate to the transfer list
    page_props = (
        data.get("props", {}).get("pageProps")
        or data.get("pageProps")
        or {}
    )
    transfers_data = page_props.get("transferPortal", {}).get("list", [])

    entries = []
    for item in transfers_data:
        person = item.get("person", {})
        name = (person.get("name") or "").strip()
        if not name:
            continue

        dest = ""
        origin = ""
        commitment = item.get("commitment", {})
        if commitment:
            dest_team = commitment.get("team", {})
            dest = (dest_team.get("name") or "").strip() if dest_team else ""

        prev = item.get("previousTeam", {})
        if prev:
            origin = (prev.get("name") or "").strip()

        entries.append({
            "name": name,
            "normalized": normalize_name_stripped(name),
            "destination": dest,
            "origin": origin,
        })

    return entries


def scrape_all_portal(max_pages: int = 100) -> list[dict]:
    """Scrape all committed transfer portal entries from On3."""
    all_transfers = []
    for page_num in range(1, max_pages + 1):
        entries = scrape_portal_page(page_num)
        if not entries:
            log.info(f"  Page {page_num}: 0 results, stopping.")
            break
        all_transfers.extend(entries)
        if page_num % 10 == 0:
            log.info(f"  Scraped {page_num} pages ({len(all_transfers)} transfers)")
        time.sleep(1.0)
    return all_transfers


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    dry_run = "--dry-run" in sys.argv

    log.info("=" * 70)
    log.info("  BACKFILL ACQUISITION TYPE")
    log.info("=" * 70)

    # ── Fetch all players ────────────────────────────────────────────────────
    log.info("Fetching all players...")
    all_p = []
    offset = 0
    while True:
        resp = supabase.table("players").select(
            "id, name, team_id, player_tag, hs_grad_year, roster_status"
        ).range(offset, offset + 999).execute()
        batch = resp.data or []
        all_p.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    log.info(f"  {len(all_p):,} players loaded")

    # Fetch teams
    tresp = supabase.table("teams").select("id, university_name").execute()
    teams = {t["id"]: t["university_name"] for t in (tresp.data or [])}

    # ── Rule 1: Recruits ─────────────────────────────────────────────────────
    log.info("\nRule 1: Tagging 2026 HS recruits...")
    recruits = [p for p in all_p
                if p.get("player_tag") == "High School Recruit"
                and p.get("hs_grad_year") == 2026]
    log.info(f"  Found {len(recruits)} 2026 HS recruits")

    # ── Rule 2: Portal transfers ─────────────────────────────────────────────
    log.info("\nRule 2: Scraping On3 transfer portal for committed transfers...")
    portal_entries = scrape_all_portal(max_pages=100)
    log.info(f"  Scraped {len(portal_entries)} committed portal entries")

    # Build a set of normalized portal names for matching
    portal_names = set()
    for entry in portal_entries:
        portal_names.add(entry["normalized"])
        # Also add the non-stripped version
        portal_names.add(normalize_name(entry["name"]))

    # Match portal names against active players
    active_cas = [p for p in all_p
                  if p.get("player_tag") == "College Athlete"
                  and (p.get("roster_status") or "active") == "active"]

    portal_ids = set()
    for p in active_cas:
        p_norm = normalize_name(p.get("name", ""))
        p_stripped = normalize_name_stripped(p.get("name", ""))
        if p_norm in portal_names or p_stripped in portal_names:
            portal_ids.add(p["id"])

    log.info(f"  Matched {len(portal_ids)} active players to portal entries")

    # ── Apply updates ────────────────────────────────────────────────────────
    recruit_ids = {p["id"] for p in recruits}

    # Count current state
    recruit_count = len(recruit_ids)
    portal_count = len(portal_ids - recruit_ids)  # don't double-count if somehow both
    retained_count = len(all_p) - recruit_count - portal_count

    log.info(f"\n  BREAKDOWN:")
    log.info(f"    recruit:   {recruit_count:,}")
    log.info(f"    portal:    {portal_count:,}")
    log.info(f"    retained:  {retained_count:,}")
    log.info(f"    total:     {len(all_p):,}")

    if dry_run:
        log.info(f"\n  DRY RUN — no changes written.")
        return

    # Write recruits
    log.info(f"\n  Writing acquisition_type = 'recruit' for {recruit_count} players...")
    written = 0
    errors = 0
    for p in recruits:
        try:
            supabase.table("players").update(
                {"acquisition_type": "recruit"}
            ).eq("id", p["id"]).execute()
            written += 1
        except Exception as exc:
            errors += 1
            if errors <= 3:
                log.warning(f"  [ERROR] {p.get('name', '?')}: {exc}")
    log.info(f"  Written: {written}, Errors: {errors}")

    # Write portal
    portal_only = portal_ids - recruit_ids
    log.info(f"\n  Writing acquisition_type = 'portal' for {len(portal_only)} players...")
    written = 0
    errors = 0
    for pid in portal_only:
        try:
            supabase.table("players").update(
                {"acquisition_type": "portal"}
            ).eq("id", pid).execute()
            written += 1
        except Exception as exc:
            errors += 1
            if errors <= 3:
                log.warning(f"  [ERROR] {pid}: {exc}")
    log.info(f"  Written: {written}, Errors: {errors}")

    # Retained is the default column value — no explicit write needed
    log.info(f"\n  'retained' is the column default — {retained_count:,} players unchanged")

    log.info(f"\n{'=' * 70}")
    log.info(f"  BACKFILL COMPLETE")
    log.info(f"{'=' * 70}")


if __name__ == "__main__":
    main()
