"""
Scrapes 247Sports basketball composite rankings for 2026 class,
extracts name/position/composite/school, filters to 4-star+ (≥0.8900),
and outputs:
  1. data/basketball_recruits_2026.csv  (for ingest_bball_recruits.py)
  2. RECRUITS_2026 Python list           (for build_bball_recruit_csvs.py)

Usage:
    python parse_raw_247_recruits.py              # scrape + write CSV
    python parse_raw_247_recruits.py --dry-run    # scrape + print only
"""

import csv
import os
import re
import sys
import time
import unicodedata

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

MAX_PAGES = 10
MIN_COMPOSITE = 0.8900
DEFAULT_YEAR = 2026

POSITION_MAP = {
    "PG": "PG", "SG": "SG", "SF": "SF", "PF": "PF", "C": "C",
    "CG": "PG", "GF": "SF", "FC": "PF", "G": "SG", "F": "SF",
}

SCHOOL_TO_SLUG = {
    "Kansas": "kansas", "Duke": "duke", "Arkansas": "arkansas",
    "Arizona": "arizona", "USC": "usc", "Missouri": "missouri",
    "BYU": "byu", "Ohio State": "ohio-state", "Maryland": "maryland",
    "Miami": "miami", "Michigan": "michigan", "Houston": "houston",
    "Michigan State": "michigan-state", "UConn": "uconn",
    "Alabama": "alabama", "Texas": "texas",
    "Oklahoma State": "oklahoma-state", "Texas Tech": "texas-tech",
    "North Carolina": "north-carolina", "Oregon": "oregon",
    "Baylor": "baylor", "Pittsburgh": "pittsburgh",
    "Indiana": "indiana", "Purdue": "purdue", "Gonzaga": "gonzaga",
    "Villanova": "villanova", "Tennessee": "tennessee",
    "Georgia Tech": "georgia-tech", "UCLA": "ucla",
    "Memphis": "memphis", "Illinois": "illinois",
    "Iowa State": "iowa-state", "Florida State": "florida-state",
    "West Virginia": "west-virginia",
    "Mississippi State": "mississippi-state", "Texas A&M": "texas-am",
    "Vanderbilt": "vanderbilt", "South Carolina": "south-carolina",
    "Oklahoma": "oklahoma", "Creighton": "creighton",
    "NC State": "nc-state", "Notre Dame": "notre-dame",
    "Wake Forest": "wake-forest", "Stanford": "stanford",
    "Nebraska": "nebraska", "Northwestern": "northwestern",
    "Xavier": "xavier", "Boston College": "boston-college",
    "Kentucky": "kentucky", "Iowa": "iowa", "Marquette": "marquette",
    "LSU": "lsu", "Arizona State": "arizona-state",
    "Clemson": "clemson", "SMU": "smu", "Butler": "butler",
    "DePaul": "depaul", "Colorado": "colorado",
    "Georgetown": "georgetown", "Ole Miss": "ole-miss",
    "Minnesota": "minnesota", "San Diego State": "san-diego-state",
    "Seton Hall": "seton-hall", "St. John's": "st-johns",
    "Syracuse": "syracuse", "Virginia": "virginia",
    "Virginia Tech": "virginia-tech", "Cal": "cal",
    "Penn State": "penn-state", "Rutgers": "rutgers",
    "UCF": "ucf", "TCU": "tcu", "Cincinnati": "cincinnati",
    "Kansas State": "kansas-state", "Utah": "utah",
    "Wisconsin": "wisconsin", "Florida": "florida",
    "Auburn": "auburn", "Georgia": "georgia",
    "Providence": "providence",
    # Aliases
    "N/A": "", "California": "cal", "Connecticut": "uconn",
    "Miami (FL)": "miami",
}

def csv_path(year: int) -> str:
    return os.path.join(os.path.dirname(__file__), "data", f"basketball_recruits_{year}.csv")


def make_espn_id(year: int, name: str) -> str:
    slug = re.sub(r"[^a-z0-9]", "_", name.lower().strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return f"hs{year}_{slug}"


def composite_to_stars(composite: float) -> int:
    if composite >= 0.9900:
        return 5
    if composite >= 0.8900:
        return 4
    return 3


def scrape_page(url: str) -> list[dict]:
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    recruits = []
    for item in soup.select(".rankings-page__list-item"):
        try:
            # Name
            name_el = (
                item.select_one(".recruit .rankings-page__name-link")
                or item.select_one("a.rankings-page__name-link")
            )
            if not name_el:
                continue
            name = name_el.get_text(strip=True)

            # Position
            pos_el = item.select_one(".position")
            raw_pos = pos_el.get_text(strip=True) if pos_el else "SF"
            position = POSITION_MAP.get(raw_pos.upper(), raw_pos.upper())

            # Composite score
            score_el = item.select_one(".score")
            if not score_el:
                continue
            composite = float(score_el.get_text(strip=True))

            # Committed school (from .img-link img alt)
            school = ""
            img_link = item.select_one(".img-link img")
            if img_link:
                school = img_link.get("alt", "")
            if not school:
                status_img = item.select_one(".status img")
                if status_img:
                    alt = status_img.get("alt", "")
                    if alt and alt != name:
                        school = alt

            recruits.append({
                "name": name,
                "position": position,
                "composite": composite,
                "school_raw": school,
            })
        except Exception as e:
            print(f"  [WARN] Parse error: {e}")
            continue

    return recruits


def main():
    dry_run = "--dry-run" in sys.argv

    # Parse --year flag
    year = DEFAULT_YEAR
    for i, arg in enumerate(sys.argv):
        if arg == "--year" and i + 1 < len(sys.argv):
            year = int(sys.argv[i + 1])

    print(f"Scraping {year} basketball recruits from 247Sports...\n")

    # Scrape all pages
    all_recruits: list[dict] = []
    for page_num in range(1, MAX_PAGES + 1):
        url = (
            f"https://247sports.com/Season/{year}-Basketball/"
            f"CompositeRecruitRankings/?InstitutionGroup=HighSchool"
            f"&Page={page_num}"
        )
        print(f"Page {page_num}: {url}")
        try:
            page = scrape_page(url)
            if not page:
                print(f"  Page {page_num} empty — stopping.")
                break
            all_recruits.extend(page)
            print(f"  Got {len(page)} recruits (total: {len(all_recruits)})")
            time.sleep(2.0)
        except Exception as e:
            print(f"  [ERROR] {e}")
            break

    print(f"\nScraped {len(all_recruits)} total recruits")

    # Filter to 4-star+
    qualified = [r for r in all_recruits if r["composite"] >= MIN_COMPOSITE]
    print(f"Qualified (≥{MIN_COMPOSITE}): {len(qualified)}")

    # Map schools
    unmatched_schools: set[str] = set()
    for r in qualified:
        raw = r["school_raw"]
        if raw in SCHOOL_TO_SLUG:
            r["slug"] = SCHOOL_TO_SLUG[raw]
        elif not raw:
            r["slug"] = ""
        else:
            unmatched_schools.add(raw)
            r["slug"] = ""
        r["stars"] = composite_to_stars(r["composite"])
        r["espn_id"] = make_espn_id(year, r["name"])

    # Stats
    five_star = [r for r in qualified if r["stars"] == 5]
    four_star = [r for r in qualified if r["stars"] == 4]
    committed = [r for r in qualified if r["slug"]]
    uncommitted = [r for r in qualified if not r["slug"]]

    print(f"\n5-star: {len(five_star)}, 4-star: {len(four_star)}")
    print(f"Committed to tracked school: {len(committed)}")
    print(f"Uncommitted / outside universe: {len(uncommitted)}")

    if unmatched_schools:
        print(f"\nUnmatched schools (outside 82-team universe):")
        for s in sorted(unmatched_schools):
            print(f"  {s}")

    # Print Python list for build_bball_recruit_csvs.py
    print(f"\n# ── RECRUITS_{year} ({len(qualified)} entries) ──")
    print(f"RECRUITS_{year} = [")
    for r in qualified:
        name_escaped = r["name"].replace('"', '\\"')
        print(f'    ("{name_escaped}",{" " * max(1, 30 - len(name_escaped))}"{r["position"]}", {r["composite"]:.4f}, "{r["slug"]}"),')
    print("]")

    # Write CSV
    out_path = csv_path(year)
    if not dry_run:
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "espn_athlete_id", "player_name", "star_rating",
                "composite_score", "position_247", "committed_school_slug",
                "hs_grad_year",
            ])
            for r in qualified:
                writer.writerow([
                    r["espn_id"], r["name"], r["stars"],
                    r["composite"], r["position"], r["slug"], year,
                ])
        print(f"\nWrote {len(qualified)} rows to {out_path}")
    else:
        print("\n(Dry run — CSV not written)")


if __name__ == "__main__":
    main()
