"""
explore_cfbd_api.py
--------------------
Step 1B: Explore CFBD API endpoints and response structure.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))

CFBD_API_KEY = os.getenv("CFBD_API_KEY")
if not CFBD_API_KEY:
    raise EnvironmentError("CFBD_API_KEY not found in .env.local")

BASE_URL = "https://api.collegefootballdata.com"
HEADERS  = {"Authorization": f"Bearer {CFBD_API_KEY}"}

# Sample cfbd_ids from Step 1A
SAMPLE_QB_ID = 5297799   # Kolton Stover, QB
SAMPLE_WR_ID = 5081820   # David Adolph, WR


def get(path: str, params: dict = None) -> tuple[int, any]:
    """Make a GET request, return (status_code, json_or_error)."""
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.get(url, headers=HEADERS, params=params or {}, timeout=20)
        print(f"  Status: {resp.status_code}  URL: {resp.url}")
        if resp.status_code == 200:
            return resp.status_code, resp.json()
        else:
            return resp.status_code, resp.text[:500]
    except Exception as e:
        return 0, str(e)


def show_sample(data, label: str, max_items: int = 3):
    """Print the first few items of a response and all field names."""
    print(f"\n--- {label} ---")
    if isinstance(data, list):
        print(f"  Total items: {len(data)}")
        if data:
            print(f"  Fields: {list(data[0].keys())}")
            print(f"  First {min(max_items, len(data))} items:")
            for item in data[:max_items]:
                print(f"    {json.dumps(item, indent=None)}")
    elif isinstance(data, dict):
        print(f"  Fields: {list(data.keys())}")
        print(f"  Value: {json.dumps(data, indent=2)[:500]}")
    else:
        print(f"  Response: {str(data)[:500]}")


def main():
    print("=" * 70)
    print("CFBD API EXPLORATION")
    print("=" * 70)

    # ── 1. GET /stats/categories ───────────────────────────────────────────────
    print("\n[1] GET /stats/categories")
    code, data = get("/stats/categories")
    show_sample(data, "stat categories", max_items=50)

    # ── 2. GET /stats/player/season?year=2025 with cfbd_id ────────────────────
    print("\n[2] GET /stats/player/season?year=2025 (QB player)")
    code, data = get("/stats/player/season", {"year": 2025, "playerId": SAMPLE_QB_ID})
    show_sample(data, f"QB stats year=2025 (playerId={SAMPLE_QB_ID})", max_items=10)

    # ── 3. GET /stats/player/season?year=2024 with same cfbd_id ───────────────
    print("\n[3] GET /stats/player/season?year=2024 (QB player)")
    code, data = get("/stats/player/season", {"year": 2024, "playerId": SAMPLE_QB_ID})
    show_sample(data, f"QB stats year=2024 (playerId={SAMPLE_QB_ID})", max_items=10)

    # ── 4. Bulk fetch — all players, no filter ─────────────────────────────────
    print("\n[4] GET /stats/player/season?year=2025 (bulk — no playerId filter)")
    code, data = get("/stats/player/season", {"year": 2025})
    if isinstance(data, list) and data:
        show_sample(data, "bulk stats year=2025", max_items=5)
        # Show all unique categories
        categories = sorted(set(item.get("category", "") for item in data))
        stat_types = sorted(set(item.get("statType", "") for item in data))
        print(f"\n  Unique categories ({len(categories)}): {categories}")
        print(f"  Unique statTypes ({len(stat_types)}): {stat_types}")

        # Show category+statType combos
        combos = sorted(set(
            f"{item.get('category','')}.{item.get('statType','')}"
            for item in data
        ))
        print(f"\n  All category.statType combos ({len(combos)}):")
        for c in combos:
            print(f"    {c}")
    else:
        print(f"  Response: {str(data)[:500]}")
        # Try 2024
        print("\n  Trying year=2024 instead...")
        code, data = get("/stats/player/season", {"year": 2024})
        if isinstance(data, list) and data:
            show_sample(data, "bulk stats year=2024", max_items=5)
            categories = sorted(set(item.get("category", "") for item in data))
            stat_types = sorted(set(item.get("statType", "") for item in data))
            print(f"\n  Unique categories ({len(categories)}): {categories}")
            print(f"  Unique statTypes ({len(stat_types)}): {stat_types}")

            combos = sorted(set(
                f"{item.get('category','')}.{item.get('statType','')}"
                for item in data
            ))
            print(f"\n  All category.statType combos ({len(combos)}):")
            for c in combos:
                print(f"    {c}")

    # ── 5. GET /player/usage?year=2025 ────────────────────────────────────────
    print("\n[5] GET /player/usage?year=2025")
    code, data = get("/player/usage", {"year": 2025})
    show_sample(data, "player usage year=2025", max_items=3)

    print("\n" + "=" * 70)
    print("CFBD API exploration complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
