"""
ingest_tennessee_transfers.py
-------------------------------
Inserts Tennessee transfer-in players who appear on the Ourlads depth chart
but are not in our database.

Usage:
    python ingest_tennessee_transfers.py              # dry-run
    python ingest_tennessee_transfers.py --apply      # insert to DB
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import argparse
import re
import unicodedata

import requests
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from supabase_client import supabase

# ─── Helpers ────────────────────────────────────────────────────────────────

def norm(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-z0-9 ]", "", ascii_name.lower())
    return " ".join(clean.split())

_IGNORE = {"rs", "sr", "jr", "fr", "so", "tr", "gr"}

def parse_ourlads_name(raw: str) -> str | None:
    raw = raw.strip()
    if not raw:
        return None
    if "," not in raw:
        return norm(raw) or None
    last, rest = raw.split(",", 1)
    first = ""
    for tok in rest.split():
        if tok.split("/")[0].upper() not in _IGNORE:
            first = tok
            break
    if not first:
        return None
    return norm(f"{first} {last}")

def format_name(parsed_norm: str) -> str:
    """Convert normalized name back to Title Case for DB storage."""
    return " ".join(w.capitalize() for w in parsed_norm.split())

def parse_class_year(raw: str) -> int | None:
    tokens = set()
    for tok in raw.split():
        for part in tok.split("/"):
            tokens.add(part.upper())
    is_rs = "RS" in tokens
    if "GR" in tokens:
        return 5
    if "SR" in tokens:
        return 5 if (is_rs or "TR" in tokens) else 4
    if "JR" in tokens:
        return 4 if is_rs else 3
    if "SO" in tokens:
        return 3 if is_rs else 2
    if "FR" in tokens:
        return 2 if is_rs else 1
    return None

POS_MAP = {
    "WR-X": "WR", "WR-Z": "WR", "WR-SL": "WR", "WR-H": "WR",
    "LT": "OL", "LG": "OL", "C": "OL", "RG": "OL", "RT": "OL",
    "TE": "TE", "QB": "QB", "RB": "RB", "HB": "RB", "FB": "RB",
    "DE": "DE", "NT": "DL", "DT": "DL",
    "JACK": "DE", "LEO": "DE", "SAM": "LB",
    "MAC": "LB", "MIKE": "LB", "MLB": "LB", "WLB": "LB",
    "WILL": "LB", "MONEY": "LB",
    "LCB": "CB", "RCB": "CB", "NB": "DB",
    "SS": "S", "FS": "S",
    "PT": "P", "PK": "PK", "KO": "PK", "LS": "LS",
    "H": "QB", "PR": "WR", "KR": "RB",
    "LDE": "DE", "RDE": "DE", "LDT": "DL", "RDT": "DL",
}


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    dry_run = not args.apply
    mode = "DRY RUN" if dry_run else "LIVE"

    print("=" * 85)
    print(f"  INGEST TENNESSEE TRANSFERS ({mode})")
    print("=" * 85)

    # Get Tennessee team_id
    teams = supabase.table("teams").select("id, university_name").execute()
    tenn_id = next(t["id"] for t in teams.data if t["university_name"] == "Tennessee")

    # Fetch existing Tennessee players
    existing: list[dict] = []
    offset = 0
    while True:
        r = (supabase.table("players")
            .select("id, name")
            .eq("team_id", tenn_id)
            .eq("player_tag", "College Athlete")
            .range(offset, offset + 999)
            .execute())
        batch = r.data or []
        existing.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    existing_norms = {norm(p["name"]) for p in existing}
    print(f"\n  Existing Tennessee athletes: {len(existing)}")

    # Scrape Ourlads
    print("  Scraping Ourlads Tennessee depth chart...")
    url = "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/tennessee/91993"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    soup = BeautifulSoup(resp.text, "html.parser")

    scraped: list[dict] = []
    for tbody_id in ["ctl00_phContent_dcTBody", "ctl00_phContent_dcTBody2", "ctl00_phContent_dcTBody3"]:
        tbody = soup.find("tbody", id=tbody_id)
        if not tbody:
            continue
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue
            position = tds[0].get_text(strip=True)
            for slot, cell_idx in enumerate([2, 4, 6, 8], start=1):
                if cell_idx >= len(tds):
                    break
                a = tds[cell_idx].find("a")
                if not a:
                    continue
                href = a.get("href", "")
                raw = a.get_text(strip=True)
                if "/0" in href.split("/")[-1] or not raw:
                    continue
                parsed = parse_ourlads_name(raw)
                if parsed:
                    scraped.append({
                        "ourlads_pos": position,
                        "cfo_pos": POS_MAP.get(position, position),
                        "name_norm": parsed,
                        "name_display": format_name(parsed),
                        "raw_name": raw,
                        "rank": slot,
                        "class_year": parse_class_year(raw),
                    })

    # Deduplicate (keep best rank)
    best: dict[str, dict] = {}
    for s in scraped:
        if s["name_norm"] not in best or s["rank"] < best[s["name_norm"]]["rank"]:
            best[s["name_norm"]] = s

    # Find unmatched
    to_insert: list[dict] = []
    for name_n, entry in best.items():
        if name_n in existing_norms:
            continue
        matched = any(
            SequenceMatcher(None, name_n, en).ratio() >= 0.80
            for en in existing_norms
        )
        if not matched:
            to_insert.append(entry)

    print(f"  Ourlads players: {len(best)}, Unmatched (to insert): {len(to_insert)}")

    # Print the insert plan
    print(f"\n  {'Name':<25} {'Pos':<5} {'Rank':>4} {'Class':>5} {'Raw Ourlads':<35}")
    print(f"  {'─' * 78}")

    for p in sorted(to_insert, key=lambda x: (x["rank"], x["ourlads_pos"])):
        cls = str(p["class_year"]) if p["class_year"] else "—"
        print(f"  {p['name_display']:<25} {p['cfo_pos']:<5} {p['rank']:>4} {cls:>5} {p['raw_name']:<35}")

    if dry_run:
        print(f"\n  DRY RUN — {len(to_insert)} inserts NOT applied.")
        print(f"  To apply: python ingest_tennessee_transfers.py --apply")
    else:
        print(f"\n  Inserting {len(to_insert)} players...")
        inserted = 0
        errors = 0
        for p in to_insert:
            row = {
                "name": p["name_display"],
                "position": p["cfo_pos"],
                "team_id": tenn_id,
                "player_tag": "College Athlete",
                "roster_status": "active",
                "is_on_depth_chart": True,
                "depth_chart_rank": p["rank"],
                "is_public": True,
                "is_override": False,
            }
            if p["class_year"]:
                row["class_year"] = str(p["class_year"])
            try:
                supabase.table("players").insert(row).execute()
                inserted += 1
            except Exception as exc:
                print(f"    [ERROR] {p['name_display']}: {exc}")
                errors += 1
        print(f"  Inserted: {inserted}, Errors: {errors}")

    print(f"\n{'=' * 85}")


if __name__ == "__main__":
    main()
