"""
sync_ourlads_depth_charts.py
-----------------------------
Scrapes Ourlads NCAA depth charts for all 16 tracked teams and updates
is_on_depth_chart + depth_chart_rank in the players table.

For each team:
  1. Fetch the Ourlads depth chart page.
  2. Parse every position group row.  Each row has 11 cells:
       [pos_label] [jersey] [player1] [jersey] [player2] [jersey] [player3]
       [jersey] [player4] [jersey] [departed_player]
     Active players are at cell indices 2, 4, 6, 8 → ranks 1–4.
     Cell 10 is the "departed" column — always skipped.
  3. Fuzzy-match each scraped name against our College Athletes on that team.
  4. Set is_on_depth_chart = True + depth_chart_rank for matched players.
     Players NOT found on Ourlads get is_on_depth_chart = False.
     Override players (is_override = True) are NEVER touched.

Usage:
    python sync_ourlads_depth_charts.py                     # dry-run (default)
    python sync_ourlads_depth_charts.py --apply             # write to DB
    python sync_ourlads_depth_charts.py --team georgia      # single team
    python sync_ourlads_depth_charts.py --team georgia --apply

Requirements:
    pip install supabase python-dotenv requests beautifulsoup4
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import argparse
import datetime
import re
import time
import unicodedata
from difflib import SequenceMatcher

import requests
from bs4 import BeautifulSoup
from supabase_client import supabase

# ─── Constants ──────────────────────────────────────────────────────────────

REQUEST_DELAY = 1.5
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Verified 2026 Ourlads URLs for all 68 Power 4 teams.
# Key = university_name (lowercase, as stored in teams table).
OURLADS_URLS: dict[str, str] = {
    # SEC
    "alabama":          "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/alabama/89923",
    "arkansas":         "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/arkansas/89992",
    "auburn":           "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/auburn/90061",
    "florida":          "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/florida/90498",
    "georgia":          "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/georgia/90590",
    "kentucky":         "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/kentucky/90866",
    "lsu":              "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/lsu/90981",
    "mississippi state":"https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/mississippi-state/91211",
    "missouri":         "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/missouri/91234",
    "oklahoma":         "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/oklahoma/91556",
    "ole miss":         "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/ole-miss/91602",
    "south carolina":   "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/south-carolina/91832",
    "tennessee":        "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/tennessee/91993",
    "texas":            "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/texas/92016",
    "texas a&m":        "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/texas-am/92039",
    "vanderbilt":       "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/vanderbilt/92361",
    # Big Ten
    "illinois":         "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/illinois/90705",
    "indiana":          "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/indiana/90728",
    "iowa":             "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/iowa/90751",
    "maryland":         "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/maryland/91027",
    "michigan":         "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/michigan/91119",
    "michigan state":   "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/michigan-state/91142",
    "minnesota":        "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/minnesota/91188",
    "nebraska":         "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/nebraska/91303",
    "northwestern":     "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/northwestern/91464",
    "ohio state":       "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/ohio-state/91533",
    "oregon":           "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/oregon/91625",
    "penn state":       "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/penn-state/91671",
    "purdue":           "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/purdue/91717",
    "rutgers":          "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/rutgers/91763",
    "ucla":             "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/ucla/92223",
    "usc":              "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/usc/92269",
    "washington":       "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/washington/92453",
    "wisconsin":        "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/wisconsin/92545",
    # Big 12
    "arizona":          "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/arizona/89946",
    "arizona state":    "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/arizona-state/89969",
    "baylor":           "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/baylor/90107",
    "byu":              "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/brigham-young/90222",
    "cincinnati":       "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/cincinnati/90291",
    "colorado":         "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/colorado/90337",
    "houston":          "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/houston/90659",
    "iowa state":       "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/iowa-state/90774",
    "kansas":           "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/kansas/90797",
    "kansas state":     "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/kansas-state/90820",
    "oklahoma state":   "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/oklahoma-state/91579",
    "tcu":              "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/tcu/91947",
    "texas tech":       "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/texas-tech/92062",
    "ucf":              "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/central-florida/92200",
    "utah":             "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/utah/92292",
    "west virginia":    "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/west-virginia/92499",
    # ACC
    "boston college":    "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/boston-college/90153",
    "cal":              "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/california/90245",
    "clemson":          "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/clemson/90314",
    "duke":             "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/duke/90406",
    "florida state":    "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/florida-state/90544",
    "georgia tech":     "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/georgia-tech/90613",
    "louisville":       "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/louisville/90958",
    "miami":            "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/miami/91073",
    "nc state":         "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/nc-state/91280",
    "north carolina":   "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/north-carolina/91395",
    "pittsburgh":       "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/pittsburgh/91694",
    "smu":              "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/smu/91809",
    "stanford":         "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/stanford/91901",
    "syracuse":         "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/syracuse/91924",
    "virginia":         "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/virginia/92384",
    "virginia tech":    "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/virginia-tech/92407",
    "wake forest":      "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/wake-forest/92430",
    # Independent
    "notre dame":       "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/notre-dame/91487",
}

# Class-year / suffix tokens to strip from Ourlads names.
_IGNORE_TOKENS = {"rs", "sr", "jr", "fr", "so", "tr", "gr"}


# ─── Name helpers ───────────────────────────────────────────────────────────

def norm(name: str) -> str:
    """Normalize for fuzzy comparison: NFKD → ASCII → lowercase → alpha+space only."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^a-z0-9 ]", "", ascii_name.lower())
    return " ".join(clean.split())


def parse_ourlads_name(raw: str) -> str | None:
    """
    Ourlads format: "Lastname, Firstname RS SR" or "Lastname, Firstname JR/TR"
    Returns normalized "firstname lastname", or None if empty/unparseable.
    """
    raw = raw.strip()
    if not raw:
        return None

    if "," not in raw:
        return norm(raw) or None

    last_part, rest = raw.split(",", 1)
    last_name = last_part.strip()

    # First non-suffix token after the comma is the first name.
    first_name = ""
    for token in rest.split():
        # Handle "JR/TR" style combined tokens
        base = token.split("/")[0]
        if base.upper() not in _IGNORE_TOKENS:
            first_name = token
            break

    if not first_name:
        return None

    return norm(f"{first_name} {last_name}")


def fuzzy(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


# ─── Scraping ───────────────────────────────────────────────────────────────

def scrape_depth_chart(url: str) -> list[dict]:
    """
    Scrape a single Ourlads depth chart page.
    Returns list of {position, name, rank} dicts for ACTIVE players only.
    Departed players (cell index 10) are excluded.
    """
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        print(f"    [ERROR] {exc}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # Three tbody sections: offense, defense, special teams.
    tbody_ids = [
        "ctl00_phContent_dcTBody",
        "ctl00_phContent_dcTBody2",
        "ctl00_phContent_dcTBody3",
    ]

    entries: list[dict] = []

    for tbody_id in tbody_ids:
        tbody = soup.find("tbody", id=tbody_id)
        if not tbody:
            continue

        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue

            position = tds[0].get_text(strip=True)

            # Active player cells are at indices 2, 4, 6, 8.
            # Cell 10 is the departed column — skip it.
            # Each player cell contains an <a> tag with the name.
            player_indices = [2, 4, 6, 8]

            for slot, cell_idx in enumerate(player_indices, start=1):
                if cell_idx >= len(tds):
                    break

                a_tag = tds[cell_idx].find("a")
                if not a_tag:
                    continue

                href = a_tag.get("href", "")
                raw_name = a_tag.get_text(strip=True)

                # Skip empty slots (href points to /player//0 or name is blank).
                if "/0" in href.split("/")[-1] or not raw_name:
                    continue

                parsed = parse_ourlads_name(raw_name)
                if parsed:
                    entries.append({
                        "position": position,
                        "name": parsed,
                        "raw_name": raw_name,
                        "rank": slot,
                    })

    return entries


# ─── Database ───────────────────────────────────────────────────────────────

def fetch_teams() -> dict[str, str]:
    """Returns {team_id: university_name}."""
    resp = supabase.table("teams").select("id, university_name").execute()
    return {t["id"]: t["university_name"] for t in (resp.data or [])}


def fetch_college_athletes() -> list[dict]:
    """Fetch all College Athletes with fields needed for matching + updating."""
    all_players: list[dict] = []
    offset = 0
    PAGE = 1000
    while True:
        resp = (
            supabase.table("players")
            .select(
                "id, name, position, team_id, is_on_depth_chart, "
                "depth_chart_rank, is_override, roster_status, cfo_valuation"
            )
            .eq("player_tag", "College Athlete")
            .range(offset, offset + PAGE - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE
    return all_players


# ─── Matching ───────────────────────────────────────────────────────────────

def match_team_depth_chart(
    scraped: list[dict],
    team_players: list[dict],
    threshold: float = 0.80,
) -> tuple[dict[str, int], list[dict]]:
    """
    Match scraped Ourlads entries against DB players for one team.

    Returns:
        matched: {player_id: best_rank}  — best (lowest) rank across all appearances.
        unmatched: list of scraped entries that didn't match any DB player.
    """
    # Build lookup: norm_name → player dict
    db_index: dict[str, dict] = {}
    for p in team_players:
        db_index[norm(p["name"])] = p

    matched: dict[str, int] = {}      # player_id → best rank
    matched_names: dict[str, str] = {}  # player_id → scraped raw name (for display)
    unmatched: list[dict] = []

    # Deduplicate scraped entries: a player may appear multiple times (e.g. QB + H).
    # Keep the entry with the BEST (lowest) rank per unique name.
    best_by_name: dict[str, dict] = {}
    for entry in scraped:
        name = entry["name"]
        if name not in best_by_name or entry["rank"] < best_by_name[name]["rank"]:
            best_by_name[name] = entry

    for name, entry in best_by_name.items():
        # Exact match first
        if name in db_index:
            pid = str(db_index[name]["id"])
            if pid not in matched or entry["rank"] < matched[pid]:
                matched[pid] = entry["rank"]
                matched_names[pid] = entry["raw_name"]
            continue

        # Fuzzy match
        best_score = 0.0
        best_player = None
        for db_name, player in db_index.items():
            score = SequenceMatcher(None, name, db_name).ratio()
            if score > best_score:
                best_score = score
                best_player = player

        if best_player and best_score >= threshold:
            pid = str(best_player["id"])
            if pid not in matched or entry["rank"] < matched[pid]:
                matched[pid] = entry["rank"]
                matched_names[pid] = entry["raw_name"]
        else:
            unmatched.append(entry)

    return matched, unmatched


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scrape Ourlads depth charts and update is_on_depth_chart + depth_chart_rank"
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Write changes to DB (default is dry-run)",
    )
    parser.add_argument(
        "--team", type=str, default=None,
        help="Run for a single team only (e.g. --team georgia)",
    )
    args = parser.parse_args()

    dry_run = not args.apply
    mode = "DRY RUN" if dry_run else "LIVE"

    print("=" * 80)
    print(f"  OURLADS DEPTH CHART SYNC ({mode})")
    print("=" * 80)

    # ── Load DB data ────────────────────────────────────────────────────────
    print("\n  Loading teams and players...")
    teams = fetch_teams()
    players = fetch_college_athletes()
    active_players = [p for p in players if (p.get("roster_status") or "active") == "active"]
    print(f"  Teams: {len(teams)}")
    print(f"  College athletes: {len(players)} ({len(active_players)} active)")

    # Build team_id → university_name and reverse lookups.
    team_name_to_id: dict[str, str] = {}
    for tid, tname in teams.items():
        team_name_to_id[tname.lower()] = tid

    # ── Determine which teams to process ────────────────────────────────────
    if args.team:
        team_filter = args.team.strip().lower()
        urls_to_run = {k: v for k, v in OURLADS_URLS.items() if k == team_filter}
        if not urls_to_run:
            print(f"\n  [ERROR] Team '{args.team}' not found in OURLADS_URLS.")
            print(f"  Available: {', '.join(sorted(OURLADS_URLS.keys()))}")
            return
    else:
        urls_to_run = OURLADS_URLS

    # ── Collect all updates across teams ─────────────────────────────────────
    # on_dc: player_id → rank (players confirmed on depth chart)
    # off_dc: set of player_ids to mark OFF depth chart
    all_on_dc: dict[str, int] = {}
    all_team_player_ids: set[str] = set()  # all players on teams we processed

    override_ids = {str(p["id"]) for p in players if p.get("is_override") is True}

    summary_rows: list[tuple[str, int, int, int, int]] = []

    print(f"\n{'=' * 80}")

    for team_key, url in urls_to_run.items():
        team_id = team_name_to_id.get(team_key)
        if not team_id:
            print(f"\n  [{team_key.title()}] SKIP — not in teams table")
            continue

        display_name = teams[team_id]
        print(f"\n  [{display_name}]")
        print(f"    URL: {url}")

        # ── Scrape ──────────────────────────────────────────────────────────
        scraped = scrape_depth_chart(url)
        # Count unique position groups.
        positions_scraped = len({e["position"] for e in scraped})
        print(f"    Scraped: {len(scraped)} player slots across {positions_scraped} position groups")

        if not scraped:
            print("    [WARN] No data scraped — skipping.")
            summary_rows.append((display_name, 0, 0, 0, 0))
            time.sleep(REQUEST_DELAY)
            continue

        # ── Match ───────────────────────────────────────────────────────────
        team_roster = [p for p in players if str(p.get("team_id")) == team_id]
        matched, unmatched = match_team_depth_chart(scraped, team_roster)

        # Track which players on this team we've evaluated.
        for p in team_roster:
            all_team_player_ids.add(str(p["id"]))

        # Merge into global on-DC set.
        for pid, rank in matched.items():
            if pid not in all_on_dc or rank < all_on_dc[pid]:
                all_on_dc[pid] = rank

        # ── Per-team report ─────────────────────────────────────────────────
        # Count overrides in matched set.
        override_on_dc = sum(1 for pid in matched if pid in override_ids)
        active_on_team = [p for p in team_roster
                          if (p.get("roster_status") or "active") == "active"]

        print(f"    Matched: {len(matched)} players on depth chart")
        if override_on_dc:
            print(f"    Override players on DC (will NOT be touched): {override_on_dc}")
        if unmatched:
            print(f"    Unmatched Ourlads names ({len(unmatched)}):")
            for u in unmatched[:8]:
                print(f"      {u['position']:<8} rank {u['rank']}  {u['raw_name']}")
            if len(unmatched) > 8:
                print(f"      ... and {len(unmatched) - 8} more")

        summary_rows.append((
            display_name, positions_scraped, len(matched),
            len(unmatched), override_on_dc,
        ))

        if team_key != list(urls_to_run.keys())[-1]:
            time.sleep(REQUEST_DELAY)

    # ── Compute off-DC set ──────────────────────────────────────────────────
    # Players on processed teams who were NOT matched → is_on_depth_chart = False.
    off_dc_ids = all_team_player_ids - set(all_on_dc.keys())

    # ── Build update plan ───────────────────────────────────────────────────
    player_map = {str(p["id"]): p for p in players}
    updates_on: list[dict] = []   # players to mark ON depth chart
    updates_off: list[dict] = []  # players to mark OFF depth chart
    skipped_overrides = 0

    for pid, rank in all_on_dc.items():
        p = player_map.get(pid)
        if not p:
            continue
        if pid in override_ids:
            skipped_overrides += 1
            continue
        old_dc = p.get("is_on_depth_chart", False)
        old_rank = p.get("depth_chart_rank")
        if old_dc is True and old_rank == rank:
            continue  # no change needed
        updates_on.append({
            "id": pid,
            "name": p["name"],
            "team_id": p.get("team_id"),
            "old_dc": old_dc,
            "old_rank": old_rank,
            "new_rank": rank,
        })

    for pid in off_dc_ids:
        p = player_map.get(pid)
        if not p:
            continue
        if pid in override_ids:
            skipped_overrides += 1
            continue
        if p.get("is_on_depth_chart") is not True:
            continue  # already off — no change needed
        updates_off.append({
            "id": pid,
            "name": p["name"],
            "team_id": p.get("team_id"),
            "old_rank": p.get("depth_chart_rank"),
            "cfo_valuation": p.get("cfo_valuation"),
        })

    # ── Print update plan ───────────────────────────────────────────────────
    print(f"\n{'=' * 80}")
    print(f"  UPDATE PLAN ({mode})")
    print(f"{'=' * 80}")

    if updates_on:
        print(f"\n  SET ON DEPTH CHART ({len(updates_on)} players):")
        header = f"{'PLAYER':<28} {'TEAM':<18} {'OLD DC':>6} {'OLD RK':>6} {'NEW RK':>6}"
        print(f"    {header}")
        print(f"    {'─' * len(header)}")
        for u in sorted(updates_on, key=lambda x: (x["team_id"] or "", x["new_rank"])):
            tname = teams.get(u["team_id"] or "", "?")[:17]
            old_dc_s = "True" if u["old_dc"] else "False"
            old_rk_s = str(u["old_rank"]) if u["old_rank"] is not None else "—"
            print(f"    {u['name']:<28} {tname:<18} {old_dc_s:>6} {old_rk_s:>6} {u['new_rank']:>6}")

    if updates_off:
        print(f"\n  REMOVE FROM DEPTH CHART ({len(updates_off)} players):")
        header = f"{'PLAYER':<28} {'TEAM':<18} {'OLD RK':>6} {'CFO VAL':>12}"
        print(f"    {header}")
        print(f"    {'─' * len(header)}")
        for u in sorted(updates_off, key=lambda x: -(x.get("cfo_valuation") or 0)):
            tname = teams.get(u["team_id"] or "", "?")[:17]
            old_rk_s = str(u["old_rank"]) if u["old_rank"] is not None else "—"
            val = u.get("cfo_valuation")
            val_s = f"${val:>10,}" if val else f"{'—':>11}"
            print(f"    {u['name']:<28} {tname:<18} {old_rk_s:>6} {val_s}")

    if skipped_overrides:
        print(f"\n  Override players skipped: {skipped_overrides}")

    if not updates_on and not updates_off:
        print("\n  No changes needed — depth chart is up to date.")

    # ── Team summary table ──────────────────────────────────────────────────
    print(f"\n  {'TEAM':<22} {'POS':>5} {'MATCH':>6} {'UNMTCH':>7} {'OVRRD':>6}")
    print(f"  {'─' * 50}")
    for name, pos, match, unmatch, ovr in summary_rows:
        print(f"  {name:<22} {pos:>5} {match:>6} {unmatch:>7} {ovr:>6}")

    # ── Apply ───────────────────────────────────────────────────────────────
    if dry_run:
        total_changes = len(updates_on) + len(updates_off)
        print(f"\n  DRY RUN — {total_changes} changes NOT applied.")
        print(f"  To apply: python sync_ourlads_depth_charts.py --apply")
    else:
        now = datetime.datetime.utcnow().isoformat()
        applied = 0
        errors = 0

        for u in updates_on:
            try:
                supabase.table("players").update({
                    "is_on_depth_chart": True,
                    "depth_chart_rank": u["new_rank"],
                    "last_updated": now,
                }).eq("id", u["id"]).execute()
                applied += 1
            except Exception as exc:
                print(f"    [ERROR] {u['name']}: {exc}")
                errors += 1

        for u in updates_off:
            try:
                supabase.table("players").update({
                    "is_on_depth_chart": False,
                    "depth_chart_rank": None,
                    "last_updated": now,
                }).eq("id", u["id"]).execute()
                applied += 1
            except Exception as exc:
                print(f"    [ERROR] {u['name']}: {exc}")
                errors += 1

        print(f"\n  Applied: {applied}, Errors: {errors}")

    print(f"\n{'=' * 80}")


if __name__ == "__main__":
    main()
