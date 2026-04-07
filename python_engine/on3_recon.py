"""
on3_recon.py
------------
Reconnaissance script: fetches the On3 NIL rankings page and extracts the
raw data embedded in the __NEXT_DATA__ <script> tag, then writes it to
on3_data_dump.json for inspection.

Usage:
    python on3_recon.py

Requirements:
    pip install requests beautifulsoup4
"""

import json
import requests
from bs4 import BeautifulSoup

URL = "https://www.on3.com/nil/rankings/player/college/football/"

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

OUTPUT_FILE = "on3_data_dump.json"

# ---------------------------------------------------------------------------
# 1. FETCH
# ---------------------------------------------------------------------------

print(f"Fetching {URL} ...")
resp = requests.get(URL, headers=HEADERS, timeout=20)
print(f"  Status: {resp.status_code}")
resp.raise_for_status()

# ---------------------------------------------------------------------------
# 2. EXTRACT
# ---------------------------------------------------------------------------

soup = BeautifulSoup(resp.text, "html.parser")
tag  = soup.find("script", id="__NEXT_DATA__", type="application/json")

if not tag or not tag.string:
    print("\n[ERROR] Could not find <script id=\"__NEXT_DATA__\"> in the response.")
    print("On3 may be blocking the request or rendering this page client-side only.")
    raise SystemExit(1)

# ---------------------------------------------------------------------------
# 3. PARSE
# ---------------------------------------------------------------------------

data = json.loads(tag.string)

# ---------------------------------------------------------------------------
# 4. DUMP
# ---------------------------------------------------------------------------

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# ---------------------------------------------------------------------------
# 5. LOG
# ---------------------------------------------------------------------------

print(f"\n[SUCCESS] __NEXT_DATA__ extracted and saved to '{OUTPUT_FILE}'.")
print(f"  Top-level keys: {list(data.keys())}")
print(f"\nOpen '{OUTPUT_FILE}' and inspect the structure to find the player list.")
