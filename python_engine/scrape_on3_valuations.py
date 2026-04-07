"""
scrape_on3_valuations.py
------------------------
Pulls NIL valuations from On3's player rankings page and writes them to the
on3_valuation column in our Supabase players table.

Data source confirmed via on3_data_dump.json:
  Page 1  → __NEXT_DATA__ → props.pageProps.nilRankings.list
  Page N  → /_next/data/{buildId}/nil/rankings/player/nil-valuations.json?page={N}
           → pageProps.nilRankings.list   (no outer "props" wrapper)

Each list item:
  item["person"]["name"]         → "Arch Manning"
  item["valuation"]["valuation"] → 5440974   (integer, already in dollars)

Usage:
    python scrape_on3_valuations.py

Requirements:
    pip install supabase python-dotenv requests beautifulsoup4
"""

import os
import re
import time
import json
import difflib
import unicodedata
import requests
from bs4 import BeautifulSoup
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

BASE_URL   = "https://www.on3.com/nil/rankings/player/nil-valuations/"
PAGES      = 10
PAGE_DELAY = 2  # seconds between paginated requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}

# ---------------------------------------------------------------------------
# 2. HELPERS
# ---------------------------------------------------------------------------

def parse_valuation(text) -> int:
    """
    Convert a valuation string or number to a plain integer.

    Handles:
      '$1.2M'   → 1200000
      '$850K'   → 850000
      '$95,000' → 95000
      5440974   → 5440974   (already an int/float, pass through)
      None / '' → 0
    """
    if text is None:
        return 0
    if isinstance(text, (int, float)):
        return int(text)
    text = str(text).strip()
    if not text:
        return 0
    # Strip dollar signs and commas
    cleaned = text.replace("$", "").replace(",", "").strip()
    # Handle M / K suffixes (case-insensitive)
    match = re.match(r"^([\d.]+)\s*([MmKk]?)$", cleaned)
    if match:
        number = float(match.group(1))
        suffix = match.group(2).upper()
        if suffix == "M":
            return int(number * 1_000_000)
        if suffix == "K":
            return int(number * 1_000)
        return int(number)
    return 0


def normalise(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-z0-9 ]", "", ascii_name.lower())
    return " ".join(clean.split())


def extract_list(page_data: dict) -> list[dict]:
    """
    Return the nilRankings list from either:
      - a full __NEXT_DATA__ payload  (props.pageProps.nilRankings.list)
      - a paginated /_next/data/ response  (pageProps.nilRankings.list)
    """
    page_props = (
        page_data.get("props", {}).get("pageProps")  # page 1
        or page_data.get("pageProps")                 # pages 2-N
        or {}
    )
    return page_props.get("nilRankings", {}).get("list") or []


# ---------------------------------------------------------------------------
# 3. FETCH PAGE 1 VIA __NEXT_DATA__ — also grabs the buildId
# ---------------------------------------------------------------------------

print(f"Fetching page 1 via __NEXT_DATA__: {BASE_URL}")
resp = requests.get(BASE_URL, headers=HEADERS, timeout=20)
print(f"  Status: {resp.status_code}")
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "html.parser")
tag  = soup.find("script", id="__NEXT_DATA__", type="application/json")

if not tag or not tag.string:
    print("[ERROR] __NEXT_DATA__ tag not found. On3 may be blocking the request.")
    raise SystemExit(1)

page1_json = json.loads(tag.string)
build_id   = page1_json.get("buildId", "")

if not build_id:
    print("[ERROR] buildId not found in __NEXT_DATA__. Cannot construct paginated URLs.")
    raise SystemExit(1)

print(f"  buildId: {build_id}")

# ---------------------------------------------------------------------------
# 4. BUILD on3_val_data FROM ALL PAGES
# ---------------------------------------------------------------------------

# on3_val_data maps normalised_name → on3_valuation (int, dollars)
on3_val_data: dict[str, int] = {}


def process_list(items: list[dict], page_label: str) -> int:
    """Parse a list of ranking items into on3_val_data. Returns new entries added."""
    added = 0
    for item in items:
        name = (item.get("person") or {}).get("name", "").strip()
        if not name:
            continue
        raw_val = (item.get("valuation") or {}).get("valuation")
        val_int = parse_valuation(raw_val)
        key = normalise(name)
        if key not in on3_val_data:
            on3_val_data[key] = val_int
            added += 1
    return added


# Process page 1
p1_list  = extract_list(page1_json)
p1_added = process_list(p1_list, "1")
print(f"  Page 1: {p1_added} new player(s) parsed.  (dict total: {len(on3_val_data)})\n")

# Pages 2-N via the internal Next.js data API
for page_num in range(2, PAGES + 1):
    api_url = (
        f"https://www.on3.com/_next/data/{build_id}"
        f"/nil/rankings/player/nil-valuations.json"
        f"?page={page_num}"
    )
    print(f"  Page {page_num}/{PAGES}... ", end="", flush=True)

    try:
        r = requests.get(api_url, headers=HEADERS, timeout=20)
        if r.status_code == 404:
            print("[404] buildId may be stale. Stopping pagination.")
            break
        if r.status_code == 403:
            print("[403 Blocked] Stopping pagination.")
            break
        r.raise_for_status()
        page_json = r.json()
    except requests.RequestException as exc:
        print(f"[ERROR] {exc}")
        time.sleep(PAGE_DELAY)
        continue

    items = extract_list(page_json)
    added = process_list(items, str(page_num))
    print(f"{added} new player(s) parsed.  (dict total: {len(on3_val_data)})")
    time.sleep(PAGE_DELAY)

print(f"\nScrape complete. {len(on3_val_data)} unique players in on3_val_data.\n")

if not on3_val_data:
    print("No data collected. Exiting.")
    raise SystemExit(1)

# ---------------------------------------------------------------------------
# 5. FETCH ALL PLAYERS FROM SUPABASE (paginated)
# ---------------------------------------------------------------------------

def fetch_all_players() -> list[dict]:
    PAGE_SIZE = 1000
    all_players: list[dict] = []
    offset = 0

    print("Fetching all players from Supabase...")
    while True:
        resp = (
            supabase.table("players")
            .select("id, name")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    print(f"  {len(all_players)} players fetched.\n")
    return all_players


players = fetch_all_players()

# ---------------------------------------------------------------------------
# 6. MATCH & UPDATE
# ---------------------------------------------------------------------------

dict_keys = list(on3_val_data.keys())
updated   = 0
unmatched: list[str] = []

print("=" * 65)
print("Matching players and writing on3_valuation to Supabase...")
print("=" * 65)

for player in players:
    key       = normalise(player["name"])
    val_int   = on3_val_data.get(key)
    match_type = "exact"

    if val_int is None:
        fuzzy = difflib.get_close_matches(key, dict_keys, n=1, cutoff=0.85)
        if fuzzy:
            matched_key = fuzzy[0]
            val_int     = on3_val_data[matched_key]
            match_type  = f'fuzzy → "{matched_key}"'

    if val_int is not None:
        print(
            f"  [UPDATED] {player['name']} ({match_type})  "
            f"on3_valuation=${val_int:,}"
        )
        supabase.table("players").update(
            {"on3_valuation": val_int}
        ).eq("id", player["id"]).execute()
        updated += 1
        time.sleep(0.1)
    else:
        unmatched.append(player["name"])

# ---------------------------------------------------------------------------
# 7. SUMMARY
# ---------------------------------------------------------------------------

print(f"\n{'=' * 65}")
print(f"Enrichment complete.")
print(f"  Players updated   : {updated}")
print(f"  Players unmatched : {len(unmatched)}")
print(f"  Total players     : {len(players)}")

if unmatched:
    print(f"\nUnmatched players ({len(unmatched)}):")
    for name in sorted(unmatched):
        print(f"  — {name}")
