"""
scrape_2026_recruits.py
───────────────────────
Fetches the 247Sports 2026 Composite Recruit Rankings, calculates a
C.F.O. Valuation for every player using the V1.0 algorithm, and upserts
the results into the Supabase `players` table.

Idempotent: uses uuid.uuid5() to derive a deterministic UUID from each
player's name, so running the script twice will upsert — not duplicate —
existing rows.

Run:
    python python_engine/scrape_2026_recruits.py
"""

import os
import time
import uuid
import requests
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

URL = "https://247sports.com/Season/2026-Football/CompositeRecruitRankings/"

# Realistic browser headers to avoid bot-detection (403) from 247Sports CDN
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

# Pages to scrape (each page returns ~50 players; 6 pages ≈ 300 players)
TOTAL_PAGES = 6

# Namespace for deterministic UUIDs — lets upsert deduplicate by player name
CFO_UUID_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

# ---------------------------------------------------------------------------
# C.F.O. Valuation Algorithm — V1.0  (mirrors CLAUDE.md Section 4)
# ---------------------------------------------------------------------------

BASE_RATES: dict[int, int] = {
    5: 100_000,
    4:  50_000,
    3:  25_000,
}

POSITIONAL_MULTIPLIERS: dict[str, float] = {
    "QB":   2.5,
    "LT":   1.5,
    "EDGE": 1.5,
    "WR":   1.2,
    "CB":   1.2,
    "DT":   1.2,
}

# Composite score thresholds used by 247Sports
def derive_star_rating(composite_score: float) -> int:
    if composite_score >= 0.9830:
        return 5
    if composite_score >= 0.8900:
        return 4
    return 3


def calculate_cfo_valuation(star_rating: int, position: str) -> int:
    """High School experience multiplier is always 1.0x."""
    base     = BASE_RATES.get(star_rating, 25_000)
    pos_mult = POSITIONAL_MULTIPLIERS.get(position.upper(), 1.0)
    return int(base * pos_mult * 1.0)


def player_uuid(name: str) -> str:
    """Deterministic UUID derived from the player's name.
    Same name → same UUID every run → upsert deduplicates correctly.
    """
    return str(uuid.uuid5(CFO_UUID_NAMESPACE, name.strip().lower()))


# ---------------------------------------------------------------------------
# Scraping helpers
# ---------------------------------------------------------------------------

def safe_text(tag, *selectors: str, attr: str | None = None) -> str:
    """Try each CSS selector in order; return the first non-empty result."""
    for selector in selectors:
        el = tag.select_one(selector)
        if el is None:
            continue
        value = (el.get(attr) or "").strip() if attr else el.get_text(strip=True)
        if value:
            return value
    return ""


def parse_composite_score(raw: str) -> float | None:
    """Normalise '0.9985', '99.85', or '9985' to a 0–1 float."""
    try:
        val = float(raw.replace(",", "").strip())
        if val > 1:          # e.g. 99.85 → 0.9985
            val = val / 100
        return round(val, 4)
    except (ValueError, AttributeError):
        return None


POSITION_ALIASES: dict[str, str] = {
    "OT":  "LT",
    "OL":  "LT",
    "DE":  "EDGE",
    "DL":  "DT",
    "SAF": "S",
    "DB":  "CB",
}


def normalise_position(raw: str) -> str:
    pos = raw.strip().upper()
    return POSITION_ALIASES.get(pos, pos) or "ATH"


def scrape_players(html: str) -> list[dict]:
    soup  = BeautifulSoup(html, "html.parser")
    items = soup.select("li.rankings-page__list-item")
    print(f"  Found {len(items)} list items on the page.")

    players: list[dict] = []

    for item in items:
        # ── Name ──────────────────────────────────────────────────────────
        name = safe_text(
            item,
            ".rankings-page__name-link",
            "a.rankings-page__name-link",
            ".name a",
        )
        if not name:
            continue   # skip ads / header spacers

        # ── Position ──────────────────────────────────────────────────────
        position = normalise_position(
            safe_text(item, ".position", ".recruit-position", ".pos")
        )

        # ── Composite score ───────────────────────────────────────────────
        raw_score = safe_text(
            item,
            ".score",
            ".composite-score",
            ".rankings-page__composite-score",
        )
        composite_score = parse_composite_score(raw_score)
        if composite_score is None:
            print(f"  Warning: no composite score for '{name}' (raw='{raw_score}'). Skipping.")
            continue

        # ── High school ───────────────────────────────────────────────────
        high_school = safe_text(
            item,
            ".school-name",
            ".rankings-page__school-name",
        ) or "Unknown"

        star_rating   = derive_star_rating(composite_score)
        cfo_valuation = calculate_cfo_valuation(star_rating, position)

        players.append({
            "id":               player_uuid(name),   # deterministic → safe to upsert
            "name":             name,
            "high_school":      high_school,
            "position":         position,
            "star_rating":      star_rating,
            "experience_level": "High School",
            "composite_score":  composite_score,
            "cfo_valuation":    cfo_valuation,
        })

    return players


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # ── Supabase credentials ───────────────────────────────────────────────
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))
    supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not supabase_url or not supabase_key:
        raise EnvironmentError("Missing Supabase credentials in .env.local")
    supabase: Client = create_client(supabase_url, supabase_key)

    # ── Pagination loop ────────────────────────────────────────────────────
    all_players: list[dict] = []

    for page in range(1, TOTAL_PAGES + 1):
        current_url = f"{URL}?page={page}"
        print(f"\n[Page {page}/{TOTAL_PAGES}] Fetching {current_url} ...")

        resp = requests.get(current_url, headers=HEADERS, timeout=20)
        print(f"  HTTP {resp.status_code}")

        if resp.status_code == 403:
            raise RuntimeError(
                f"403 Forbidden on page {page} — 247Sports blocked the request.\n"
                "Wait a few seconds and try again, or open the URL in a browser first "
                "to warm the session cookies."
            )
        resp.raise_for_status()

        page_players = scrape_players(resp.text)

        if not page_players:
            debug_path = os.path.join(os.path.dirname(__file__), f"debug_2026_page{page}.html")
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(resp.text)
            print(
                f"  Warning: no players parsed on page {page}.\n"
                f"  Raw HTML saved to {debug_path} for inspection.\n"
                "  Stopping early — this page may be past the last available page."
            )
            break

        print(f"  Parsed {len(page_players)} players. (Running total: {len(all_players) + len(page_players)})")
        all_players.extend(page_players)

        # Polite delay between requests to avoid IP throttling
        if page < TOTAL_PAGES:
            time.sleep(2)

    # ── Guard ──────────────────────────────────────────────────────────────
    if not all_players:
        raise RuntimeError("No players were collected across any page. Check the debug HTML files.")

    # ── Preview ────────────────────────────────────────────────────────────
    df = pd.DataFrame(all_players)
    print(f"\nTotal collected: {len(all_players)} players.")
    print("\nSample (top 10):")
    print(
        df[["name", "position", "star_rating", "composite_score", "cfo_valuation"]]
        .head(10)
        .to_string(index=False)
    )

    # ── Batch upsert to Supabase ───────────────────────────────────────────
    # on_conflict="id" works because we use deterministic UUIDs derived from
    # player names — re-running the script updates existing rows rather than
    # inserting duplicates.
    print(f"\nUpserting {len(all_players)} records into 'players' table ...")
    result = (
        supabase.table("players")
        .upsert(all_players, on_conflict="id")
        .execute()
    )
    print(f"\nDone. {len(result.data)} rows upserted successfully.")

    # ── Summary by star rating ─────────────────────────────────────────────
    print("\nBreakdown by star rating:")
    print(df["star_rating"].value_counts().sort_index(ascending=False).to_string())


if __name__ == "__main__":
    main()
