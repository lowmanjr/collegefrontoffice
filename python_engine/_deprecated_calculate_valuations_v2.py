# DEPRECATED — See calculate_cfo_valuations.py and VALUATION_ENGINE.md
"""
calculate_valuations.py
-----------------------
Calculates and writes a deterministic cfo_valuation for every player in
two passes:

  Pass 1 — College Athletes (player_tag = 'College Athlete')
    Uses positional multipliers and a depth-chart starter/bench penalty model.

  Pass 2 — High School Recruits (player_tag = 'High School Recruit')
    Uses a composite-score curve anchored to class year (2026 / 2027).
    Players with no composite_score receive a $10,000 baseline.

Usage:
    python calculate_valuations.py

Requirements:
    pip install supabase python-dotenv
"""

import os
import time
import random
from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# 1. SETUP
# ---------------------------------------------------------------------------

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))

SUPABASE_URL      = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise EnvironmentError(
        "Missing Supabase credentials. "
        "Ensure NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY are set in .env.local"
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ---------------------------------------------------------------------------
# 2. FETCH ALL COLLEGE ATHLETES (paginated)
# ---------------------------------------------------------------------------

def fetch_all_college_athletes() -> list[dict]:
    """Fetches every player with player_tag = 'College Athlete' via pagination."""
    PAGE_SIZE = 1000
    all_players: list[dict] = []
    offset = 0

    print("Fetching College Athletes from Supabase...")
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, star_rating, position, is_on_depth_chart")
            .eq("player_tag", "College Athlete")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        print(f"  Fetched {len(all_players)} players so far...")

        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    print(f"  Done. {len(all_players)} total College Athletes fetched.\n")
    return all_players

# ---------------------------------------------------------------------------
# 3. VALUATION ENGINE
# ---------------------------------------------------------------------------

POSITIONAL_MULTIPLIERS: dict[str, float] = {
    "QB":   1.8,
    "WR":   1.3,
    "EDGE": 1.3,
    "DE":   1.3,
    "OT":   1.3,
    "RB":   1.1,
    "CB":   1.1,
    "DT":   1.1,
}

KICKER_POSITIONS = {"K", "P", "LS"}


def calculate_valuation(player: dict) -> int:
    """
    Returns a deterministic cfo_valuation (int, rounded to nearest $1,000)
    for a single player dict.
    """
    # Seed random with the player's name so results are deterministic
    random.seed(player["name"])

    stars      = player.get("star_rating") or 0
    on_chart   = player.get("is_on_depth_chart") or False
    position   = (player.get("position") or "ATH").strip().upper()

    # ── Base Value ───────────────────────────────────────────────────────────
    if on_chart:
        if stars >= 5:
            base = random.randint(400_000, 1_200_000)
        elif stars == 4:
            base = random.randint(100_000, 350_000)
        else:  # 3-star or below
            base = random.randint(30_000, 80_000)
    else:
        # Bench penalty
        if stars >= 5:
            base = random.randint(80_000, 150_000)
        elif stars == 4:
            base = random.randint(15_000, 40_000)
        else:
            base = 0

    # ── Positional Multiplier ────────────────────────────────────────────────
    if position in KICKER_POSITIONS:
        multiplier = 0.2
    else:
        multiplier = POSITIONAL_MULTIPLIERS.get(position, 1.0)

    raw_value = base * multiplier

    # ── Final Polish: round to nearest $1,000 ────────────────────────────────
    return round(raw_value / 1000) * 1000


# ---------------------------------------------------------------------------
# 4. FETCH HIGH SCHOOL RECRUITS (paginated)
# ---------------------------------------------------------------------------

def fetch_all_hs_recruits() -> list[dict]:
    """Fetches every player with player_tag = 'High School Recruit' via pagination."""
    PAGE_SIZE = 1000
    all_recruits: list[dict] = []
    offset = 0

    print("Fetching High School Recruits from Supabase...")
    while True:
        resp = (
            supabase.table("players")
            .select("id, name, class_year, national_rank, composite_score")
            .eq("player_tag", "High School Recruit")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = resp.data or []
        all_recruits.extend(batch)
        print(f"  Fetched {len(all_recruits)} recruits so far...")

        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    print(f"  Done. {len(all_recruits)} total High School Recruits fetched.\n")
    return all_recruits

# ---------------------------------------------------------------------------
# 5. FUTURES VALUATION ENGINE
# ---------------------------------------------------------------------------

# Anchor definitions keyed by class_year string
FUTURES_ANCHORS: dict[str, dict] = {
    "2026": {"max": 1_000_000, "min": 50_000},
    "2027": {"max":   500_000, "min": 25_000},
}

COMPOSITE_FLOOR   = 0.8900  # lowest score that enters the curve (4-star floor)
COMPOSITE_CEILING = 1.0000
UNRANKED_BASELINE = 10_000  # assigned when composite_score is null


def calculate_futures_valuation(recruit: dict) -> int:
    """
    Returns a cfo_valuation (int, rounded to nearest $1,000) for a single
    High School Recruit using the composite-score curve.

    Logic:
      - No composite_score → $10,000 baseline.
      - class_year determines the Max/Min anchors (defaults to 2027 anchors
        if the year is unrecognised).
      - percentage = (score - 0.8900) / (1.0000 - 0.8900)
      - raw_value  = Min + percentage * (Max - Min)
      - Clamped to [Min, Max] and rounded to the nearest $1,000.
    """
    score      = recruit.get("composite_score")
    class_year = str(recruit.get("class_year") or "").strip()

    if score is None:
        return UNRANKED_BASELINE

    anchors = FUTURES_ANCHORS.get(class_year, FUTURES_ANCHORS["2027"])
    val_min = anchors["min"]
    val_max = anchors["max"]

    score = float(score)

    # Scores below the floor still receive the minimum guaranteed value
    if score <= COMPOSITE_FLOOR:
        return val_min

    percentage = (score - COMPOSITE_FLOOR) / (COMPOSITE_CEILING - COMPOSITE_FLOOR)
    raw_value  = val_min + percentage * (val_max - val_min)

    # Clamp and round
    clamped = max(val_min, min(val_max, raw_value))
    return round(clamped / 1000) * 1000


# ---------------------------------------------------------------------------
# 6. MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    # ── Pass 1: College Athletes ─────────────────────────────────────────────
    players = fetch_all_college_athletes()

    if not players:
        print("No College Athletes found. Skipping pass 1.")
    else:
        print(f"Calculating and writing valuations for {len(players)} College Athletes...\n")

        for i, player in enumerate(players, start=1):
            valuation = calculate_valuation(player)

            supabase.table("players").update(
                {"cfo_valuation": valuation}
            ).eq("id", player["id"]).execute()

            time.sleep(0.05)

            if i % 500 == 0:
                print(f"  Valued {i} players...")

        print(f"Pass 1 complete. {len(players)} College Athletes valued.\n")

    # ── Pass 2: High School Recruits ─────────────────────────────────────────
    recruits = fetch_all_hs_recruits()

    if not recruits:
        print("No High School Recruits found. Skipping pass 2.")
    else:
        print(f"Calculating and writing futures valuations for {len(recruits)} recruits...\n")

        baseline_count = 0
        curved_count   = 0

        for i, recruit in enumerate(recruits, start=1):
            valuation = calculate_futures_valuation(recruit)

            supabase.table("players").update(
                {"cfo_valuation": valuation}
            ).eq("id", recruit["id"]).execute()

            if recruit.get("composite_score") is None:
                baseline_count += 1
            else:
                curved_count += 1

            time.sleep(0.05)

            if i % 500 == 0:
                print(f"  Valued {i} recruits...")

        print(f"Pass 2 complete. {len(recruits)} High School Recruits valued.")
        print(f"  Curve-based (had composite_score) : {curved_count}")
        print(f"  Baseline $10k (no composite_score) : {baseline_count}")

    print(f"\nAll done.")


if __name__ == "__main__":
    main()
