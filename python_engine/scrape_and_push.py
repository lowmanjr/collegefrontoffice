import os
import uuid
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

URL = "https://247sports.com/Season/2025-Football/CompositeRecruitRankings/"

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

TARGET_COUNT = 50

# ---------------------------------------------------------------------------
# C.F.O. Valuation Algorithm V1.0 (Section 4 of CLAUDE.md)
# ---------------------------------------------------------------------------

BASE_RATES = {5: 100_000, 4: 50_000, 3: 25_000}

POSITIONAL_MULTIPLIERS = {
    "QB":   2.5,
    "LT":   1.5,
    "EDGE": 1.5,
    "WR":   1.2,
    "CB":   1.2,
    "DT":   1.2,
}


def derive_star_rating(composite_score: float) -> int:
    if composite_score >= 0.9830:
        return 5
    if composite_score >= 0.8900:
        return 4
    return 3


def calculate_cfo_valuation(star_rating: int, position: str) -> int:
    """Experience multiplier is always 1.0 for High School recruits."""
    base = BASE_RATES[star_rating]
    pos_mult = POSITIONAL_MULTIPLIERS.get(position.upper(), 1.0)
    return int(base * pos_mult * 1.0)


# ---------------------------------------------------------------------------
# Scraping helpers
# ---------------------------------------------------------------------------

def safe_text(tag, selector: str, attr: str | None = None) -> str:
    """Return stripped text (or attribute) from a CSS-selected child, or ''."""
    el = tag.select_one(selector)
    if el is None:
        return ""
    if attr:
        return (el.get(attr) or "").strip()
    return el.get_text(strip=True)


def parse_composite_score(raw: str) -> float | None:
    """Turn strings like '0.9985', '99.85', or '9985' into a 0–1 float."""
    try:
        val = float(raw.replace(",", "").strip())
        if val > 1:          # e.g. 99.85 → 0.9985
            val = val / 100
        return round(val, 4)
    except (ValueError, AttributeError):
        return None


def scrape_players(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("li.rankings-page__list-item")
    print(f"  Found {len(items)} list items on page.")

    players: list[dict] = []

    for item in items:
        if len(players) >= TARGET_COUNT:
            break

        # --- Name ---
        name = (
            safe_text(item, ".rankings-page__name-link")
            or safe_text(item, ".name a")
            or safe_text(item, "a.rankings-page__name-link")
        )
        if not name:
            continue  # skip ads / header rows

        # --- Position ---
        position = (
            safe_text(item, ".position")
            or safe_text(item, ".recruit-position")
            or safe_text(item, ".pos")
        ).upper()
        if not position:
            position = "ATH"

        # Normalise common variants
        position = position.replace("OT", "LT").replace("DE", "EDGE").replace("DL", "DT")

        # --- Composite score ---
        raw_score = (
            safe_text(item, ".score")
            or safe_text(item, ".composite-score")
            or safe_text(item, ".rankings-page__composite-score")
        )
        composite_score = parse_composite_score(raw_score)
        if composite_score is None:
            print(f"  Warning: could not parse composite score for '{name}' (raw='{raw_score}'). Skipping.")
            continue

        # --- High school ---
        high_school = (
            safe_text(item, ".school-name")
            or safe_text(item, ".rankings-page__school-name")
            or "Unknown"
        )

        star_rating = derive_star_rating(composite_score)
        cfo_valuation = calculate_cfo_valuation(star_rating, position)

        players.append({
            "id":               str(uuid.uuid4()),
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
    # --- Supabase ---
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))
    url  = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key  = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not url or not key:
        raise EnvironmentError("Missing Supabase credentials in .env.local")
    supabase: Client = create_client(url, key)

    # --- Fetch page ---
    print(f"Fetching {URL} ...")
    response = requests.get(URL, headers=HEADERS, timeout=20)
    print(f"  HTTP {response.status_code}")

    if response.status_code == 403:
        raise RuntimeError(
            "403 Forbidden — 247Sports blocked the request.\n"
            "Try running the script again in a few seconds, or open the URL in a browser first."
        )
    response.raise_for_status()

    # Small polite delay
    time.sleep(1)

    # --- Parse ---
    print("Parsing HTML ...")
    players = scrape_players(response.text)

    if not players:
        # Debug dump so you can inspect what the page actually returned
        debug_path = os.path.join(os.path.dirname(__file__), "debug_page.html")
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(response.text)
        raise RuntimeError(
            "No players were parsed from the page.\n"
            f"The raw HTML has been saved to {debug_path} for inspection.\n"
            "The site may have changed its markup — check the selectors in scrape_players()."
        )

    print(f"  Parsed {len(players)} players.")

    # --- Preview ---
    df = pd.DataFrame(players)
    print("\nSample (top 5):")
    print(
        df[["name", "position", "star_rating", "composite_score", "cfo_valuation"]]
        .head()
        .to_string(index=False)
    )

    # --- Push to Supabase ---
    print(f"\nInserting {len(players)} records into 'players' table ...")
    result = supabase.table("players").insert(players).execute()
    print(f"\nSuccess: {len(result.data)} real recruits inserted into Supabase.")


if __name__ == "__main__":
    main()
