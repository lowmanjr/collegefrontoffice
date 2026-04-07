"""
sync_depth_charts.py
--------------------
Scrapes OurLads NCAA football depth charts using verified 2026 URLs and sets
is_on_depth_chart = True for matched College Athletes in our Supabase database.

Usage:
    python sync_depth_charts.py

Requirements:
    pip install supabase python-dotenv requests beautifulsoup4
"""

import os
import time
import difflib
import unicodedata
import re
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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

REQUEST_DELAY = 2  # seconds between requests

# ---------------------------------------------------------------------------
# 2. HARDCODED URL MAP (verified 2026 OurLads URLs)
#    Key: normalised university_name as stored in our `teams` table
# ---------------------------------------------------------------------------

OURLADS_HARDCODED_MAP: dict[str, str] = {
    "ohio state":    "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/ohio-state/91533",
    "georgia":       "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/georgia/90590",
    "alabama":       "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/alabama/89923",
    "texas":         "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/texas/92016",
    "oregon":        "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/oregon/91625",
    "michigan":      "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/michigan/91119",
    "usc":           "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/usc/92269",
    "washington":    "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/washington/92453",
    "lsu":           "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/lsu/90981",
    "tennessee":     "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/tennessee/91993",
    "oklahoma":      "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/oklahoma/91556",
    "florida":       "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/florida/90498",
    "south carolina":"https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/south-carolina/91832",
    "miami":         "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/miami/91073",
    "clemson":       "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/clemson/90314",
    "notre dame":    "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/notre-dame/91487",
}

# ---------------------------------------------------------------------------
# 3. HELPERS
# ---------------------------------------------------------------------------

def normalise(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-z0-9 ]", "", ascii_name.lower())
    return " ".join(clean.split())

_IGNORE_TOKENS = {"rs", "sr", "jr", "fr", "so", "tr", "gr"}

def parse_ourlads_name(raw: str) -> str | None:
    """
    OurLads format: "Lastname, Firstname RS SR"
    Returns a normalised "firstname lastname" string, or None if unparseable.
    """
    raw = raw.strip()
    if not raw:
        return None

    if "," in raw:
        last_part, rest = raw.split(",", 1)
        last_name  = last_part.strip()
        first_name = ""
        for token in rest.split():
            if token.upper() not in _IGNORE_TOKENS:
                first_name = token
                break
        if not first_name:
            return None
        return normalise(f"{first_name} {last_name}")
    else:
        return normalise(raw)

def safe_get(url: str) -> requests.Response | None:
    """GET with error handling. Returns None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 403:
            print(f"  [403 Blocked] {url}")
            return None
        resp.raise_for_status()
        return resp
    except requests.RequestException as exc:
        print(f"  [ERROR] {exc}")
        return None

# ---------------------------------------------------------------------------
# 4. FETCH DB
# ---------------------------------------------------------------------------

print("Fetching teams from Supabase...")
teams_resp = supabase.table("teams").select("id, university_name").execute()
teams = teams_resp.data or []
print(f"  {len(teams)} team(s) found.\n")

print("Fetching College Athletes from Supabase...")
all_players = []
start = 0
step  = 1000

while True:
    response = (
        supabase.table("players")
        .select("id, name, team_id")
        .eq("player_tag", "College Athlete")
        .range(start, start + step - 1)
        .execute()
    )
    data = response.data
    if not data:
        break
    all_players.extend(data)
    start += step

print(f"  {len(all_players)} College Athlete(s) found.\n")

# ---------------------------------------------------------------------------
# 5. SCRAPE EACH TEAM'S DEPTH CHART & UPDATE
# ---------------------------------------------------------------------------

total_matched = 0

print("=" * 65)
for team in teams:
    team_id   = team["id"]
    team_name = team["university_name"]
    norm_name = normalise(team_name)

    print(f"\n[{team_name}]")

    depth_url = OURLADS_HARDCODED_MAP.get(norm_name)
    if not depth_url:
        print(f"  [SKIP] No OurLads URL mapped for '{team_name}'.")
        continue

    print(f"  URL: {depth_url}")

    # ── Fetch depth chart page ───────────────────────────────────────────
    page_resp = safe_get(depth_url)
    if not page_resp:
        time.sleep(REQUEST_DELAY)
        continue

    time.sleep(REQUEST_DELAY)

    # ── Parse player names with depth chart ordering ───────────────────
    # OurLads depth charts are HTML tables. Each row represents a position
    # group (e.g. QB, RB, WR1, etc.). Within each row, the cells list
    # players in order: 1st string (starter), 2nd string (backup), etc.
    # We parse this order to assign depth_chart_rank.
    soup = BeautifulSoup(page_resp.text, "html.parser")

    depth_chart_names: list[str] = []
    # name → rank within its position row (1 = starter, 2 = backup, ...)
    name_to_rank: dict[str, int] = {}

    for tr in soup.select("tr"):
        tds = tr.select("td")
        col_index = 0
        for td in tds:
            a_tag = td.find("a")
            if not a_tag:
                col_index += 1
                continue
            parsed = parse_ourlads_name(a_tag.get_text(strip=True))
            if parsed:
                depth_chart_names.append(parsed)
                # Column position within the row determines rank:
                # First player cell = starter (1), second = backup (2), etc.
                if parsed not in name_to_rank:
                    name_to_rank[parsed] = col_index
            col_index += 1

    # Deduplicate while preserving order
    depth_chart_names = list(dict.fromkeys(depth_chart_names))
    print(f"  Parsed {len(depth_chart_names)} name(s) from depth chart.")

    if not depth_chart_names:
        print("  No player names parsed — skipping update.")
        continue

    # ── Isolate this team's players ──────────────────────────────────────
    team_players = [p for p in all_players if str(p.get("team_id")) == str(team_id)]
    team_db_map  = {normalise(p["name"]): p["id"] for p in team_players}

    # ── 1-to-1 matching (scraped name → DB player) ───────────────────────
    matched_ids: set[str] = set()

    for scraped_name in depth_chart_names:
        player_id = team_db_map.get(scraped_name)

        if player_id:
            matched_ids.add(player_id)
            continue

        fuzzy = difflib.get_close_matches(scraped_name, team_db_map.keys(), n=1, cutoff=0.85)
        if fuzzy:
            print(f"    [Fuzzy] '{scraped_name}' matched DB '{fuzzy[0]}'")
            matched_ids.add(team_db_map[fuzzy[0]])

    # ── Batch update with depth_chart_rank ──────────────────────────────
    for player_id in matched_ids:
        # Look up the rank for this player by finding which scraped name matched
        rank = None
        for scraped_name, pid in [(s, team_db_map.get(s)) for s in depth_chart_names]:
            if pid == player_id:
                rank = name_to_rank.get(scraped_name)
                break
        # Also check fuzzy matches
        if rank is None:
            for scraped_name in depth_chart_names:
                if scraped_name in name_to_rank:
                    fuzzy = difflib.get_close_matches(scraped_name, [normalise(p["name"]) for p in team_players if p["id"] == player_id], n=1, cutoff=0.85)
                    if fuzzy:
                        rank = name_to_rank[scraped_name]
                        break

        update_data = {"is_on_depth_chart": True}
        if rank is not None:
            # Convert column index to 1-based rank (add 1 since col_index is 0-based)
            update_data["depth_chart_rank"] = rank + 1
        supabase.table("players").update(update_data).eq("id", player_id).execute()

    print(f"  [{team_name}] found {len(matched_ids)} player(s) on depth chart.")
    total_matched += len(matched_ids)

# ---------------------------------------------------------------------------
# 6. SUMMARY
# ---------------------------------------------------------------------------

print("\n" + "=" * 65)
print(f"Sync complete.  Total players marked on depth chart: {total_matched}")
