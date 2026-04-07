"""
scrape_nfl_draft.py
--------------------
Scrapes the Tankathon 2026 NFL Big Board and writes nfl_draft_projection
ranks back to our Supabase players table for any College Athlete whose
name fuzzy-matches a top-100 prospect.

Confirmed Tankathon DOM structure (inspected 2026-04-01):
  Row  : <div class="mock-row nfl" data-pos="...">
  Rank : <div class="mock-row-pick-number">1</div>
  Name : <div class="mock-row-name">Arvell Reese</div>

Architecture:
  Pass 1 — Fetch big board HTML, parse top-100 players into a dict
            keyed by normalized name → integer rank.
  Pass 2 — Fetch all College Athletes from Supabase, fuzzy-match names
            against the draft board, and update nfl_draft_projection.

Usage:
    python scrape_nfl_draft.py

Requirements:
    pip install supabase python-dotenv requests beautifulsoup4
"""

import os
import re
import difflib
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

DRAFT_URL    = "https://www.tankathon.com/nfl/big_board"
FUZZY_CUTOFF = 0.85
TOP_N        = 100

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://www.google.com/",
}

# ---------------------------------------------------------------------------
# 2. NAME NORMALIZATION
# ---------------------------------------------------------------------------

_SUFFIXES = re.compile(r"\b(jr\.?|sr\.?|ii|iii|iv|v)\b", re.IGNORECASE)
_PUNCT    = re.compile(r"[^\w\s]")


def normalize_name(name: str) -> str:
    """
    Lowercase, strip punctuation and generational suffixes, collapse whitespace.
      "Shedeur Sanders Jr." → "shedeur sanders"
      "Travis Hunter II"    → "travis hunter"
    """
    name = name.lower()
    name = _SUFFIXES.sub("", name)
    name = _PUNCT.sub("", name)
    return " ".join(name.split())


# ---------------------------------------------------------------------------
# 3. PASS 1 — SCRAPE THE TANKATHON BIG BOARD
# ---------------------------------------------------------------------------

def fetch_draft_board() -> dict[str, int]:
    """
    Fetch the Tankathon big board and return a dict of
    normalized_name → draft_rank for the top-100 prospects.

    Raises SystemExit with a clear message if blocked or unparseable.
    """
    print(f"Fetching 2026 NFL Big Board from Tankathon...")

    try:
        resp = requests.get(DRAFT_URL, headers=HEADERS, timeout=20)
    except requests.RequestException as exc:
        raise SystemExit(f"[ERROR] Network request failed: {exc}")

    if resp.status_code == 403:
        raise SystemExit(
            "[BLOCKED] Tankathon returned 403 Forbidden.\n"
            "Try running again — transient blocks usually clear on retry.\n"
            "If it persists, save the page from your browser (Ctrl+S) and\n"
            "set LOCAL_HTML_PATH at the bottom of this script to that file."
        )
    if resp.status_code != 200:
        raise SystemExit(f"[ERROR] HTTP {resp.status_code} — could not fetch big board.")

    soup = BeautifulSoup(resp.text, "html.parser")

    # Confirmed selectors from live DOM inspection (2026-04-01):
    #   <div class="mock-row nfl" data-pos="LB/EDGE">
    #     <div class="mock-row-pick-number">1</div>
    #     <div class="mock-row-player">
    #       <a href="/nfl/players/...">
    #         <div class="mock-row-name">Arvell Reese</div>
    #       </a>
    #     </div>
    #   </div>
    rows = soup.select("div.mock-row.nfl")

    if not rows:
        raise SystemExit(
            "[ERROR] No player rows found (selector: div.mock-row.nfl).\n"
            "Tankathon may have changed their DOM. Inspect the page and\n"
            "update the selector in fetch_draft_board()."
        )

    draft_board: dict[str, int] = {}

    for row in rows:
        rank_tag = row.select_one("div.mock-row-pick-number")
        name_tag = row.select_one("div.mock-row-name")

        if not rank_tag or not name_tag:
            continue

        try:
            rank = int(re.sub(r"\D", "", rank_tag.get_text()))
        except (ValueError, TypeError):
            continue

        if rank < 1 or rank > TOP_N:
            continue

        name = name_tag.get_text(strip=True)
        if not name:
            continue

        norm = normalize_name(name)
        if norm and rank not in draft_board.values():
            draft_board[norm] = rank

    if not draft_board:
        raise SystemExit(
            "[ERROR] Rows were found but no rank/name pairs could be extracted.\n"
            "The inner element classes may have changed — check mock-row-pick-number\n"
            "and mock-row-name against the live page source."
        )

    print(f"  {len(draft_board)} prospects parsed from top {TOP_N}.")
    print("  Top 5 entries:")
    for norm, rank in sorted(draft_board.items(), key=lambda x: x[1])[:5]:
        print(f"    #{rank:>3}  {norm}")
    print()

    return draft_board


# ---------------------------------------------------------------------------
# 4. PASS 2 — FETCH PLAYERS, FUZZY MATCH, UPDATE SUPABASE
# ---------------------------------------------------------------------------

def fetch_players() -> list[dict]:
    """Return all College Athletes from Supabase."""
    PAGE_SIZE   = 1000
    all_players: list[dict] = []
    offset      = 0

    print("Fetching College Athletes from Supabase...")
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, position")
            .eq("player_tag", "College Athlete")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    print(f"  {len(all_players)} player(s) fetched.\n")
    return all_players


def match_and_update(players: list[dict], draft_board: dict[str, int]) -> None:
    board_keys = list(draft_board.keys())
    updated  = 0
    no_match = 0

    print("=" * 65)
    print("Matching players against draft board and updating Supabase...")
    print("=" * 65)

    for player in players:
        name     = player.get("name") or ""
        position = (player.get("position") or "").strip().upper()
        norm     = normalize_name(name)

        if not norm:
            no_match += 1
            continue

        # Exact match first — avoids fuzzy false positives on short names
        if norm in draft_board:
            rank = draft_board[norm]
        else:
            matches = difflib.get_close_matches(norm, board_keys, n=1, cutoff=FUZZY_CUTOFF)
            if not matches:
                no_match += 1
                continue
            rank = draft_board[matches[0]]

        supabase.table("players").update(
            {"nfl_draft_projection": rank}
        ).eq("id", player["id"]).execute()

        print(f"  [UPDATED] {name:<30}  {position:<5}  → 2026 Draft Pick #{rank}")
        updated += 1

    print(f"\n{'=' * 65}")
    print(f"NFL Draft projection enrichment complete.")
    print(f"  Players updated     : {updated}")
    print(f"  No draft board match: {no_match}")
    print(f"  Total processed     : {len(players)}")


# ---------------------------------------------------------------------------
# 5. MAIN
# ---------------------------------------------------------------------------
# To use a locally saved HTML file instead of a live fetch (if Tankathon blocks):
#   1. Open https://www.tankathon.com/nfl/big_board in your browser
#   2. Ctrl+S → Save as "Web Page, Complete"
#   3. Set LOCAL_HTML_PATH to that file path, e.g.:
#        LOCAL_HTML_PATH = r"C:\Users\johng\Downloads\tankathon_bigboard.html"
LOCAL_HTML_PATH: str | None = None


def main() -> None:
    if LOCAL_HTML_PATH:
        print(f"Loading from local file: {LOCAL_HTML_PATH}\n")
        with open(LOCAL_HTML_PATH, "r", encoding="utf-8") as f:
            html = f.read()
        soup = BeautifulSoup(html, "html.parser")
        # Inline parse so we reuse the same confirmed selectors
        rows = soup.select("div.mock-row.nfl")
        draft_board: dict[str, int] = {}
        for row in rows:
            rank_tag = row.select_one("div.mock-row-pick-number")
            name_tag = row.select_one("div.mock-row-name")
            if not rank_tag or not name_tag:
                continue
            try:
                rank = int(re.sub(r"\D", "", rank_tag.get_text()))
            except (ValueError, TypeError):
                continue
            if rank < 1 or rank > TOP_N:
                continue
            name = name_tag.get_text(strip=True)
            norm = normalize_name(name)
            if norm and rank not in draft_board.values():
                draft_board[norm] = rank
        print(f"  {len(draft_board)} prospects loaded from file.\n")
    else:
        draft_board = fetch_draft_board()

    if not draft_board:
        print("Draft board is empty — nothing to match. Exiting.")
        return

    players = fetch_players()
    if not players:
        print("No College Athletes found in Supabase. Exiting.")
        return

    match_and_update(players, draft_board)


if __name__ == "__main__":
    main()
