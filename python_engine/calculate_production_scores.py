"""
calculate_production_scores.py
-------------------------------
Fetches season stats from the CollegeFootballData (CFBD) API and computes a
position-specific production_score (0–100) for each player with a cfbd_id.

Scores are percentile-ranked against ALL FBS players at the same position,
not just our players — ensuring scores reflect the full national distribution.

Usage:
    python calculate_production_scores.py

Requirements:
    pip install -r requirements.txt   # pandas, requests, supabase
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import datetime
import time
import requests
import pandas as pd
from collections import Counter, defaultdict
from supabase_client import supabase

# ─── Config ───────────────────────────────────────────────────────────────────

CFBD_API_KEY = os.getenv("CFBD_API_KEY")
if not CFBD_API_KEY:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))
    CFBD_API_KEY = os.getenv("CFBD_API_KEY")
    if not CFBD_API_KEY:
        raise EnvironmentError("CFBD_API_KEY environment variable is not set.")

BASE_URL = "https://api.collegefootballdata.com"
HEADERS  = {"Authorization": f"Bearer {CFBD_API_KEY}"}

SEASON_YEARS = [2025, 2024]
REQUEST_DELAY = 0.1

# ─── Position groups ─────────────────────────────────────────────────────────

QB_POSITIONS   = {"QB"}
RB_POSITIONS   = {"RB", "FB"}
WR_POSITIONS   = {"WR"}
TE_POSITIONS   = {"TE"}
DEF_POSITIONS  = {"DE", "DL", "EDGE", "DT", "LB", "CB", "S", "DB", "OLB", "ILB", "MLB", "NT"}
OL_POSITIONS   = {"OL", "OT", "OG", "C", "IOL"}
SKIP_POSITIONS = {"K", "P", "PK", "LS", "ATH"}


def position_group(position: str) -> str:
    pos = (position or "").upper().strip()
    if pos in QB_POSITIONS:   return "QB"
    if pos in RB_POSITIONS:   return "RB"
    if pos in WR_POSITIONS:   return "WR"
    if pos in TE_POSITIONS:   return "TE"
    if pos in DEF_POSITIONS:  return "DEF"
    if pos in OL_POSITIONS:   return "OL"
    if pos in SKIP_POSITIONS: return "SKIP"
    return "OTHER"


# ─── CFBD API: Bulk fetch ────────────────────────────────────────────────────

def fetch_all_season_stats(year: int) -> list[dict]:
    """
    GET /stats/player/season?year={year}
    Returns ALL player stat records for the season (100K+ rows).
    The playerId filter is NOT supported — bulk fetch only.
    """
    url = f"{BASE_URL}/stats/player/season"
    print(f"  Fetching bulk stats for year {year}...")
    try:
        resp = requests.get(url, headers=HEADERS, params={"year": year}, timeout=120)
        resp.raise_for_status()
        data = resp.json() or []
        print(f"  Got {len(data):,} stat records for {year}.")
        return data
    except requests.exceptions.RequestException as exc:
        print(f"  [API ERROR] bulk stats year {year}: {exc}")
        return []


def build_player_stats_map(raw_stats: list[dict]) -> dict[str, dict[str, float]]:
    """
    Group raw CFBD stat records by playerId → {category_STATTYPE: value}.
    Also stores player name, position, and team for percentile calculation.
    Returns: {cfbd_player_id_str: {"_name": ..., "_position": ..., "_team": ..., stat_key: value}}
    """
    player_map: dict[str, dict] = {}
    for item in raw_stats:
        pid = str(item.get("playerId", ""))
        if not pid:
            continue
        if pid not in player_map:
            player_map[pid] = {
                "_name":     item.get("player", ""),
                "_position": (item.get("position") or "").upper().strip(),
                "_team":     item.get("team", ""),
            }
        category  = (item.get("category") or "").lower()
        stat_type = (item.get("statType") or "").upper()
        key = f"{category}_{stat_type}"
        try:
            player_map[pid][key] = float(item.get("stat", 0) or 0)
        except (TypeError, ValueError):
            player_map[pid][key] = 0.0
    return player_map


# ─── Raw stat extractors ─────────────────────────────────────────────────────

def extract_qb_stats(s: dict) -> dict:
    att = s.get("passing_ATT", 0)
    comp = s.get("passing_COMPLETIONS", 0)
    return {
        "passing_yds":   s.get("passing_YDS", 0),
        "passing_tds":   s.get("passing_TD", 0),
        "passing_ints":  s.get("passing_INT", 0),
        "comp_pct":      (comp / att * 100) if att > 0 else 0,
        "ypa":           s.get("passing_YPA", 0),
        "rushing_yds":   s.get("rushing_YDS", 0),
    }

def extract_rb_stats(s: dict) -> dict:
    car = max(s.get("rushing_CAR", 0), 1)
    return {
        "rushing_yds":  s.get("rushing_YDS", 0),
        "ypc":          s.get("rushing_YDS", 0) / car,
        "rushing_tds":  s.get("rushing_TD", 0),
        "recv_yds":     s.get("receiving_YDS", 0),
        "fumbles_lost": s.get("fumbles_LOST", 0),
    }

def extract_wr_stats(s: dict) -> dict:
    return {
        "recv_yds":  s.get("receiving_YDS", 0),
        "recv_rec":  s.get("receiving_REC", 0),
        "recv_tds":  s.get("receiving_TD", 0),
        "ypr":       s.get("receiving_YPR", 0),
    }

def extract_te_stats(s: dict) -> dict:
    return {
        "recv_yds":  s.get("receiving_YDS", 0),
        "recv_rec":  s.get("receiving_REC", 0),
        "recv_tds":  s.get("receiving_TD", 0),
    }

def extract_def_stats(s: dict) -> dict:
    return {
        "tackles":   s.get("defensive_TOT", 0),
        "tfl":       s.get("defensive_TFL", 0),
        "sacks":     s.get("defensive_SACKS", 0),
        "ints":      s.get("interceptions_INT", 0),
        "pds":       s.get("defensive_PD", 0),
    }


EXTRACTORS = {
    "QB":  extract_qb_stats,
    "RB":  extract_rb_stats,
    "WR":  extract_wr_stats,
    "TE":  extract_te_stats,
    "DEF": extract_def_stats,
}


# ─── Percentile scoring functions ────────────────────────────────────────────

def percentile_rank(series: pd.Series) -> pd.Series:
    """Convert values to 0–100 percentile ranks within the group."""
    if series.nunique() <= 1:
        return pd.Series([50.0] * len(series), index=series.index)
    return series.rank(pct=True, method="average") * 100


def score_qb_group(df: pd.DataFrame) -> pd.Series:
    """QB: passing yards 25%, passing TDs 20%, TD:INT ratio 20%, comp% 15%, YPA 10%, rushing yds 10%"""
    td_int = df["passing_tds"] / df["passing_ints"].clip(lower=1)
    return (
        percentile_rank(df["passing_yds"]) * 0.25
        + percentile_rank(df["passing_tds"]) * 0.20
        + percentile_rank(td_int) * 0.20
        + percentile_rank(df["comp_pct"]) * 0.15
        + percentile_rank(df["ypa"]) * 0.10
        + percentile_rank(df["rushing_yds"]) * 0.10
    ).clip(0, 100)


def score_rb_group(df: pd.DataFrame) -> pd.Series:
    """RB: rushing yards 35%, YPC 20%, rushing TDs 20%, receiving yards 15%, fumbles -10%"""
    fumble_penalty = percentile_rank(-df["fumbles_lost"])  # fewer fumbles = higher percentile
    return (
        percentile_rank(df["rushing_yds"]) * 0.35
        + percentile_rank(df["ypc"]) * 0.20
        + percentile_rank(df["rushing_tds"]) * 0.20
        + percentile_rank(df["recv_yds"]) * 0.15
        + fumble_penalty * 0.10
    ).clip(0, 100)


def score_wr_group(df: pd.DataFrame) -> pd.Series:
    """WR: receiving yards 35%, receptions 25%, TDs 20%, YPR 20%"""
    return (
        percentile_rank(df["recv_yds"]) * 0.35
        + percentile_rank(df["recv_rec"]) * 0.25
        + percentile_rank(df["recv_tds"]) * 0.20
        + percentile_rank(df["ypr"]) * 0.20
    ).clip(0, 100)


def score_te_group(df: pd.DataFrame) -> pd.Series:
    """TE: receiving yards 40%, receptions 30%, TDs 30%"""
    return (
        percentile_rank(df["recv_yds"]) * 0.40
        + percentile_rank(df["recv_rec"]) * 0.30
        + percentile_rank(df["recv_tds"]) * 0.30
    ).clip(0, 100)


def score_def_group(df: pd.DataFrame) -> pd.Series:
    """DEF: tackles 30%, TFL 25%, sacks 25%, INTs+PD 20%"""
    coverage = df["ints"] + df["pds"]
    return (
        percentile_rank(df["tackles"]) * 0.30
        + percentile_rank(df["tfl"]) * 0.25
        + percentile_rank(df["sacks"]) * 0.25
        + percentile_rank(coverage) * 0.20
    ).clip(0, 100)


SCORERS = {
    "QB":  score_qb_group,
    "RB":  score_rb_group,
    "WR":  score_wr_group,
    "TE":  score_te_group,
    "DEF": score_def_group,
}


# ─── Main pipeline ────────────────────────────────────────────────────────────

def fetch_our_players() -> list[dict]:
    """Fetch all our players who have a cfbd_id and are on the depth chart."""
    print("Fetching our players with cfbd_id...")
    all_players = []
    offset = 0
    PAGE = 1000
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, position, cfbd_id, is_on_depth_chart, player_tag")
            .not_.is_("cfbd_id", "null")
            .range(offset, offset + PAGE - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE

    print(f"  {len(all_players)} player(s) with cfbd_id found.")
    dc_count = sum(1 for p in all_players if p.get("is_on_depth_chart") is True)
    print(f"  {dc_count} of those are on the depth chart.\n")
    return all_players


def main() -> None:
    print("=" * 70)
    print("PRODUCTION SCORE PIPELINE")
    print("=" * 70)

    # 1. Fetch our players
    our_players = fetch_our_players()
    if not our_players:
        print("No players with cfbd_id found. Exiting.")
        return

    # Build cfbd_id → our player mapping
    cfbd_to_player: dict[str, dict] = {}
    for p in our_players:
        cfbd_to_player[str(p["cfbd_id"])] = p

    # 2. Fetch bulk stats from CFBD
    all_cfbd_stats = []
    active_year = None
    for year in SEASON_YEARS:
        all_cfbd_stats = fetch_all_season_stats(year)
        if all_cfbd_stats:
            active_year = year
            break

    if not all_cfbd_stats:
        print("No stats available from CFBD. Exiting.")
        return

    print(f"\nUsing season: {active_year}")

    # 3. Build stats map for ALL CFBD players (for percentile base)
    all_player_stats = build_player_stats_map(all_cfbd_stats)
    print(f"Unique CFBD players with stats: {len(all_player_stats):,}")

    # 4. Group ALL players by position group and extract raw stats
    groups: dict[str, list[dict]] = defaultdict(list)
    cfbd_id_to_group_idx: dict[str, tuple[str, int]] = {}

    for cfbd_id, stats in all_player_stats.items():
        cfbd_pos = stats.get("_position", "")
        grp = position_group(cfbd_pos)
        if grp in ("OL", "SKIP", "OTHER"):
            continue
        extractor = EXTRACTORS.get(grp)
        if not extractor:
            continue
        row = extractor(stats)
        row["_cfbd_id"] = cfbd_id
        row["_name"] = stats.get("_name", "")
        row["_is_ours"] = cfbd_id in cfbd_to_player
        idx = len(groups[grp])
        groups[grp].append(row)
        cfbd_id_to_group_idx[cfbd_id] = (grp, idx)

    print(f"\nFBS players by position group (for percentile base):")
    for grp in ["QB", "RB", "WR", "TE", "DEF"]:
        ours = sum(1 for r in groups[grp] if r["_is_ours"])
        print(f"  {grp:<5}: {len(groups[grp]):>5} total FBS,  {ours:>4} ours")

    # 5. Score each group
    scores: dict[str, float] = {}  # our player UUID → score
    score_details: list[dict] = []

    for grp, rows in groups.items():
        if not rows:
            continue
        scorer = SCORERS.get(grp)
        if not scorer:
            continue

        # Build DataFrame, excluding metadata columns
        meta_cols = {"_cfbd_id", "_name", "_is_ours"}
        stat_cols = [c for c in rows[0] if c not in meta_cols]
        df = pd.DataFrame([{c: r[c] for c in stat_cols} for r in rows])

        grp_scores = scorer(df)

        # Extract scores for OUR players
        our_count = 0
        grp_our_scores = []
        for i, row in enumerate(rows):
            if row["_is_ours"]:
                cfbd_id = row["_cfbd_id"]
                player = cfbd_to_player[cfbd_id]
                score = round(float(grp_scores.iloc[i]), 1)
                scores[str(player["id"])] = score
                grp_our_scores.append(score)
                score_details.append({
                    "name": player.get("name", ""),
                    "position": (player.get("position") or "").upper().strip(),
                    "group": grp,
                    "score": score,
                    "is_on_dc": player.get("is_on_depth_chart", False),
                })
                our_count += 1

        avg = sum(grp_our_scores) / len(grp_our_scores) if grp_our_scores else 0
        print(f"  Scored {our_count} of our {grp} players. Avg: {avg:.1f}")

    # 6. Handle OL players — no meaningful stats available
    ol_count = sum(1 for p in our_players if position_group(p.get("position", "")) == "OL")
    print(f"\n  OL players: {ol_count} — production_score set to NULL (no CFBD stats available)")

    # 7. Write scores to database
    # Only write for players whose UUIDs are confirmed in our DB
    valid_ids = {str(p["id"]) for p in our_players}
    valid_scores = {pid: score for pid, score in scores.items() if pid in valid_ids}
    invalid = len(scores) - len(valid_scores)
    if invalid:
        print(f"  Filtered out {invalid} score(s) with unrecognized player IDs.")

    print(f"\nWriting {len(valid_scores)} production scores to database...")
    now = datetime.datetime.utcnow().isoformat()
    BATCH = 200  # smaller batches to limit blast radius of failures
    rows_to_write = [
        {"id": pid, "production_score": score, "last_updated": now}
        for pid, score in valid_scores.items()
    ]
    written = 0
    for i in range(0, len(rows_to_write), BATCH):
        chunk = rows_to_write[i:i + BATCH]
        try:
            supabase.table("players").upsert(chunk, on_conflict="id").execute()
            written += len(chunk)
        except Exception as exc:
            print(f"  [BATCH ERROR] Batch {i//BATCH + 1} failed: {exc}")
            print(f"  Retrying {len(chunk)} rows individually...")
            for row in chunk:
                try:
                    supabase.table("players").update(
                        {"production_score": row["production_score"], "last_updated": row["last_updated"]}
                    ).eq("id", row["id"]).execute()
                    written += 1
                except Exception as row_exc:
                    print(f"    [ROW ERROR] {row['id']}: {row_exc}")

    print(f"  Wrote production_score for {written} of {len(valid_scores)} player(s).")

    # 8. Summary report
    print("\n" + "=" * 70)
    print("PRODUCTION SCORE SUMMARY")
    print("=" * 70)

    # By position
    pos_counter: dict[str, list[float]] = defaultdict(list)
    for d in score_details:
        pos_counter[d["position"]].append(d["score"])

    print(f"\n{'POSITION':<8} {'COUNT':>6} {'AVG':>7} {'MIN':>7} {'MAX':>7}")
    print("-" * 40)
    for pos in sorted(pos_counter.keys()):
        vals = pos_counter[pos]
        print(f"{pos:<8} {len(vals):>6} {sum(vals)/len(vals):>7.1f} {min(vals):>7.1f} {max(vals):>7.1f}")

    # Top 10 overall
    top10 = sorted(score_details, key=lambda x: x["score"], reverse=True)[:10]
    print(f"\n{'RK':<4} {'NAME':<30} {'POS':<6} {'SCORE':>7} {'ON DC':>6}")
    print("-" * 58)
    for i, d in enumerate(top10, 1):
        dc = "Yes" if d["is_on_dc"] else "No"
        print(f"{i:<4} {d['name']:<30} {d['position']:<6} {d['score']:>7.1f} {dc:>6}")

    # Skipped summary
    no_stats_players = [
        p for p in our_players
        if str(p["id"]) not in scores
        and position_group(p.get("position", "")) not in ("OL", "SKIP")
    ]
    if no_stats_players:
        skip_pos = Counter((p.get("position") or "?").upper().strip() for p in no_stats_players)
        print(f"\nPlayers skipped (no CFBD stats found): {len(no_stats_players)}")
        for pos, cnt in sorted(skip_pos.items(), key=lambda x: -x[1]):
            print(f"  {pos:<8} {cnt:>5}")

    # OL and specialist summary
    skip_positions_count = sum(
        1 for p in our_players
        if position_group(p.get("position", "")) in ("OL", "SKIP", "OTHER")
    )
    print(f"\nOL/Specialist/Other (no stats, score=NULL): {skip_positions_count}")

    total_with_score = len(scores)
    total_without = len(our_players) - total_with_score
    print(f"\nFinal: {total_with_score} scored, {total_without} unscored (NULL)")
    print("=" * 70)


if __name__ == "__main__":
    main()
