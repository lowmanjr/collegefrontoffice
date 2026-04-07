"""
scrape_on3_teams.py
-------------------
Dynamically resolves On3 team keys from the __NEXT_DATA__ filter metadata,
then fetches per-team NIL roster pages and writes four social follower
columns to our Supabase players table.

JSON structure (confirmed via on3_data_dump.json):

  Team key map:
    props.pageProps.filters.teams[]          ← conference groups
      .teams[]
        .orgKey   → the team-key query param  (e.g. 9533 for Ohio State)
        .orgName  → "Ohio State"

  Per-team player list (same __NEXT_DATA__ shape as global rankings):
    props.pageProps.nilRankings.list[]
      .person.name                           → "Arch Manning"
      .valuation.followers                   → 512477  (integer)
      .valuation.socialValuations[]
          .socialType                        → "Instagram" | "TikTok" | "Twitter"
          .followers                         → 430362  (integer)

Usage:
    python scrape_on3_teams.py

Requirements:
    pip install supabase python-dotenv requests beautifulsoup4
"""

import os
import re
import json
import time
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

BASE_RANKINGS_URL = "https://www.on3.com/nil/rankings/player/college/football/"
TEAM_URL_TEMPLATE = BASE_RANKINGS_URL + "?team-key={org_key}"
TEAM_DELAY        = 3   # seconds between team requests

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

def normalise(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-z0-9 ]", "", ascii_name.lower())
    return " ".join(clean.split())


def fetch_next_data(url: str) -> dict | None:
    """
    Fetch a URL and return the parsed __NEXT_DATA__ JSON dict.
    Returns None on any failure.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code in (403, 404):
            print(f"  [HTTP {resp.status_code}] {url}")
            return None
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  [ERROR] {exc}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    tag  = soup.find("script", id="__NEXT_DATA__", type="application/json")
    if not tag or not tag.string:
        print(f"  [WARN] __NEXT_DATA__ not found at {url}")
        return None

    return json.loads(tag.string)


def extract_socials(valuation: dict) -> dict[str, int]:
    """
    Pull total + per-platform follower counts from a valuation object.
    All counts are already integers in the On3 JSON.
    """
    result = {"total": 0, "ig": 0, "x": 0, "tiktok": 0}
    result["total"] = int(valuation.get("followers") or 0)

    for social in valuation.get("socialValuations") or []:
        platform  = (social.get("socialType") or "").lower()
        followers = int(social.get("followers") or 0)
        if platform == "instagram":
            result["ig"]     = followers
        elif platform == "twitter":
            result["x"]      = followers
        elif platform == "tiktok":
            result["tiktok"] = followers

    return result


# ---------------------------------------------------------------------------
# 3. FETCH SUPABASE TEAMS
# ---------------------------------------------------------------------------

print("Fetching teams from Supabase...")
teams_resp = supabase.table("teams").select("id, university_name").execute()
sb_teams   = teams_resp.data or []
print(f"  {len(sb_teams)} team(s) found: {[t['university_name'] for t in sb_teams]}\n")

if not sb_teams:
    print("No teams in database. Exiting.")
    raise SystemExit(0)

# ---------------------------------------------------------------------------
# 4. BUILD THE ON3 TEAM-KEY MAP (The Rosetta Stone)
# ---------------------------------------------------------------------------

print(f"Fetching On3 filter metadata from {BASE_RANKINGS_URL} ...")
page1_data = fetch_next_data(BASE_RANKINGS_URL)

if not page1_data:
    print("[ERROR] Could not load On3 rankings page. Exiting.")
    raise SystemExit(1)

# Traverse: props.pageProps.filters.teams (list of conference groups)
# Guard each level against On3 returning a non-dict value mid-chain.
_p1_props     = page1_data.get("props")
_p1_pp        = _p1_props.get("pageProps") if isinstance(_p1_props, dict) else None
_p1_filters   = _p1_pp.get("filters") if isinstance(_p1_pp, dict) else None
_p1_teams     = _p1_filters.get("teams") if isinstance(_p1_filters, dict) else None
conference_groups = _p1_teams if isinstance(_p1_teams, list) else []

# Flatten all teams into one dict: normalised_name -> org_key
on3_key_map: dict[str, int]  = {}   # normalise(orgName) → orgKey
on3_name_map: dict[str, str] = {}   # normalise(orgName) → display orgName

for group in conference_groups:
    for team in group.get("teams", []):
        org_key  = team.get("orgKey")
        org_name = (team.get("orgName") or "").strip()
        if org_key and org_name:
            key = normalise(org_name)
            on3_key_map[key]  = org_key
            on3_name_map[key] = org_name

print(f"  {len(on3_key_map)} On3 teams found in filter metadata.\n")

# ---------------------------------------------------------------------------
# 5. MATCH SUPABASE TEAMS → ON3 ORG KEYS
# ---------------------------------------------------------------------------

on3_keys = list(on3_key_map.keys())

team_key_assignments: list[dict] = []   # { id, university_name, org_key }

print("Resolving On3 team keys for Supabase teams...")
for team in sb_teams:
    norm = normalise(team["university_name"])
    org_key    = on3_key_map.get(norm)
    match_type = "exact"

    if org_key is None:
        fuzzy = difflib.get_close_matches(norm, on3_keys, n=1, cutoff=0.75)
        if fuzzy:
            matched_key = fuzzy[0]
            org_key     = on3_key_map[matched_key]
            match_type  = f'fuzzy → "{on3_name_map[matched_key]}"'

    if org_key:
        print(f"  [RESOLVED] {team['university_name']} → orgKey {org_key} ({match_type})")
        team_key_assignments.append({
            "id":              team["id"],
            "university_name": team["university_name"],
            "org_key":         org_key,
        })
    else:
        print(f"  [NO MATCH] {team['university_name']} — skipping.")

print(f"\n{len(team_key_assignments)}/{len(sb_teams)} teams resolved.\n")

if not team_key_assignments:
    print("No teams could be matched. Exiting.")
    raise SystemExit(1)

# ---------------------------------------------------------------------------
# 6. PER-TEAM SCRAPE & UPDATE
# ---------------------------------------------------------------------------

grand_updated = 0
grand_skipped = 0

print("=" * 65)

for team_entry in team_key_assignments:
    team_id   = team_entry["id"]
    team_name = team_entry["university_name"]
    org_key   = team_entry["org_key"]
    url       = TEAM_URL_TEMPLATE.format(org_key=org_key)

    print(f"\n[{team_name}]  org_key={org_key}")
    print(f"  Fetching {url} ...")

    team_data = fetch_next_data(url)
    if not team_data:
        print(f"  [SKIP] Could not load data for {team_name}.")
        time.sleep(TEAM_DELAY)
        continue

    # Extract player list from the team-filtered rankings page
    # Guard every level: On3 occasionally returns a boolean for pageProps or
    # nilRankings when the team has no ranked data, causing AttributeError.
    _props      = team_data.get("props")
    _page_props = _props.get("pageProps") if isinstance(_props, dict) else None
    _nil        = _page_props.get("nilRankings") if isinstance(_page_props, dict) else None
    _list       = _nil.get("list") if isinstance(_nil, dict) else None
    item_list   = _list if isinstance(_list, list) else []

    if not item_list:
        print(f"  [SKIP] No players found in On3 response for {team_name}.")
        time.sleep(TEAM_DELAY)
        continue

    # Build on3 name → socials dict for this team's page
    on3_team_data: dict[str, dict[str, int]] = {}
    for item in item_list:
        name      = (item.get("person") or {}).get("name", "").strip()
        valuation = item.get("valuation") or {}
        if name:
            on3_team_data[normalise(name)] = extract_socials(valuation)

    print(f"  On3 returned {len(on3_team_data)} player(s) for this team.")

    # Fetch Supabase players for this specific team
    sb_resp    = supabase.table("players").select("id, name").eq("team_id", team_id).execute()
    sb_players = sb_resp.data or []
    print(f"  Supabase has {len(sb_players)} player(s) on this roster.")

    if not sb_players:
        time.sleep(TEAM_DELAY)
        continue

    on3_player_keys = list(on3_team_data.keys())
    team_updated    = 0
    team_unmatched: list[str] = []

    for player in sb_players:
        key   = normalise(player["name"])
        entry = on3_team_data.get(key)
        match_type = "exact"

        if entry is None:
            fuzzy = difflib.get_close_matches(key, on3_player_keys, n=1, cutoff=0.85)
            if fuzzy:
                matched_key = fuzzy[0]
                entry       = on3_team_data[matched_key]
                match_type  = f'fuzzy → "{matched_key}"'

        if entry is not None:
            supabase.table("players").update({
                "total_followers":  entry["total"],
                "ig_followers":     entry["ig"],
                "x_followers":      entry["x"],
                "tiktok_followers": entry["tiktok"],
            }).eq("id", player["id"]).execute()

            print(
                f"    [UPDATED] {player['name']} ({match_type})  "
                f"total={entry['total']:,}  ig={entry['ig']:,}  "
                f"x={entry['x']:,}  tiktok={entry['tiktok']:,}"
            )
            team_updated += 1
            time.sleep(0.1)
        else:
            team_unmatched.append(player["name"])

    grand_updated += team_updated
    grand_skipped += len(team_unmatched)

    print(f"  → Updated: {team_updated}  |  Unmatched: {len(team_unmatched)}")
    if team_unmatched:
        for name in sorted(team_unmatched):
            print(f"      — {name}")

    time.sleep(TEAM_DELAY)

# ---------------------------------------------------------------------------
# 7. SUMMARY
# ---------------------------------------------------------------------------

print(f"\n{'=' * 65}")
print(f"All teams processed.")
print(f"  Total players updated   : {grand_updated}")
print(f"  Total players unmatched : {grand_skipped}")
