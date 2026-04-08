"""
Expand the database from 16 teams to all 68 Power 4 teams.
Creates team records, sets market multipliers, generates slugs, and sets logo URLs.

Usage: python expand_to_power4.py [--dry-run]
"""

import logging
import sys
import re
import unicodedata
from supabase_client import supabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Verified ESPN IDs (April 2026) ──────────────────────────────────────────

POWER_4_TEAMS = {
    "SEC": {
        333: "Alabama", 8: "Arkansas", 2: "Auburn", 57: "Florida",
        61: "Georgia", 96: "Kentucky", 99: "LSU", 344: "Mississippi State",
        142: "Missouri", 201: "Oklahoma", 145: "Ole Miss",
        2579: "South Carolina", 2633: "Tennessee", 251: "Texas",
        245: "Texas A&M", 238: "Vanderbilt",
    },
    "Big Ten": {
        356: "Illinois", 84: "Indiana", 2294: "Iowa", 120: "Maryland",
        130: "Michigan", 127: "Michigan State", 135: "Minnesota",
        158: "Nebraska", 77: "Northwestern", 194: "Ohio State",
        2483: "Oregon", 213: "Penn State", 2509: "Purdue", 164: "Rutgers",
        26: "UCLA", 30: "USC", 264: "Washington", 275: "Wisconsin",
    },
    "Big 12": {
        12: "Arizona", 9: "Arizona State", 239: "Baylor", 252: "BYU",
        2132: "Cincinnati", 38: "Colorado", 248: "Houston",
        66: "Iowa State", 2305: "Kansas", 2306: "Kansas State",
        197: "Oklahoma State", 2628: "TCU", 2641: "Texas Tech",
        2116: "UCF", 254: "Utah", 277: "West Virginia",
    },
    "ACC": {
        103: "Boston College", 25: "Cal", 228: "Clemson",
        150: "Duke", 52: "Florida State", 59: "Georgia Tech",
        97: "Louisville", 2390: "Miami", 152: "NC State",
        153: "North Carolina", 221: "Pittsburgh", 2567: "SMU",
        24: "Stanford", 183: "Syracuse", 258: "Virginia",
        259: "Virginia Tech", 154: "Wake Forest",
    },
    "Independent": {
        87: "Notre Dame",
    },
}

# ── Market Multipliers by tier ──────────────────────────────────────────────

MARKET_MULTIPLIERS = {
    "Alabama": 1.30, "Ohio State": 1.30, "Texas": 1.30, "Georgia": 1.25,
    "Michigan": 1.25, "Tennessee": 1.20, "LSU": 1.20, "Penn State": 1.20,
    "Oregon": 1.20, "USC": 1.20, "Notre Dame": 1.20, "Florida": 1.15,
    "Oklahoma": 1.15, "Clemson": 1.15, "Texas A&M": 1.15, "Miami": 1.10,
    "Auburn": 1.10, "Ole Miss": 1.10,
    "South Carolina": 1.05, "Arkansas": 1.05, "Wisconsin": 1.05,
    "Iowa": 1.05, "Michigan State": 1.05, "Florida State": 1.05,
    "Nebraska": 1.05, "UCLA": 1.05, "North Carolina": 1.05,
    "Colorado": 1.10, "Missouri": 1.05, "Kentucky": 1.00,
    "Louisville": 1.00, "Pittsburgh": 1.00, "Virginia Tech": 1.00,
    "Arizona State": 1.00, "Minnesota": 1.00, "Indiana": 1.00,
    "Mississippi State": 1.00, "Georgia Tech": 1.00, "Illinois": 1.00,
    "Maryland": 1.00, "BYU": 1.00, "Utah": 1.00, "Baylor": 1.00,
    "Oklahoma State": 1.00, "Iowa State": 1.00, "Kansas State": 1.00,
    "TCU": 1.00, "West Virginia": 1.00, "Washington": 1.05,
    "Vanderbilt": 0.95, "Wake Forest": 0.95, "Duke": 0.95,
    "Northwestern": 0.95, "Purdue": 0.95, "Rutgers": 0.95,
    "Stanford": 0.95, "Cal": 0.95, "Boston College": 0.95,
    "Syracuse": 0.95, "Virginia": 0.95, "NC State": 0.95,
    "SMU": 0.95, "Kansas": 0.95, "Cincinnati": 0.95,
    "Houston": 0.95, "UCF": 0.95, "Texas Tech": 0.95,
    "Arizona": 0.95,
}

DEFAULT_MULTIPLIER = 1.00
DEFAULT_CAP_SPACE = 20_500_000


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-")


def main():
    dry_run = "--dry-run" in sys.argv

    resp = supabase.table("teams").select("university_name").execute()
    existing_names = {t["university_name"] for t in (resp.data or [])}
    log.info(f"Existing teams in DB: {len(existing_names)}")

    created = 0
    updated = 0

    for conference, teams in POWER_4_TEAMS.items():
        for espn_id, name in teams.items():
            mm = MARKET_MULTIPLIERS.get(name, DEFAULT_MULTIPLIER)
            logo = f"https://a.espncdn.com/i/teamlogos/ncaa/500/{espn_id}.png"
            slug = slugify(name)

            if name in existing_names:
                if not dry_run:
                    supabase.table("teams").update({
                        "conference": conference,
                        "market_multiplier": mm,
                        "logo_url": logo,
                        "slug": slug,
                    }).eq("university_name", name).execute()
                updated += 1
                continue

            if dry_run:
                log.info(f"  [DRY RUN] CREATE: {name} ({conference}) espn={espn_id} mm={mm} slug={slug}")
            else:
                supabase.table("teams").insert({
                    "university_name": name,
                    "conference": conference,
                    "market_multiplier": mm,
                    "estimated_cap_space": DEFAULT_CAP_SPACE,
                    "active_payroll": 0,
                    "logo_url": logo,
                    "slug": slug,
                }).execute()

            created += 1

    log.info(f"Done. Created: {created}, Updated existing: {updated}")
    if dry_run:
        log.info("(Dry run — no changes written)")


if __name__ == "__main__":
    main()
