"""
scout_proposals.py
──────────────────
Generates mock scouting proposals and inserts them into the proposed_events
staging table for review in the Admin Approval Feed.

Fetches 3 random players with cfo_valuation > 0, generates a realistic
'Summer Camp Bump' or 'Rivals Rankings Update' event for each, and
calculates a proposed valuation 10–20% above their current value.

Run:
    python python_engine/scout_proposals.py
"""

import os
import random
import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError("Missing Supabase credentials in .env.local")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------------------------------------------------
# Event templates
# ---------------------------------------------------------------------------

EVENT_TYPES = ["Summer Camp Bump", "Rivals Rankings Update"]

DESCRIPTIONS: dict[str, list[str]] = {
    "Summer Camp Bump": [
        "{name} dominated the Elite 11 regionals, drawing significant interest from Power 4 collectives and raising market demand.",
        "{name} impressed evaluators at the Nike Opening, posting elite measurables and earning a invite to the national finals.",
        "{name} stood out at the Under Armour All-America Camp, outperforming higher-ranked peers and forcing a re-evaluation.",
        "{name} turned heads at the Rivals Camp Series with a standout performance, prompting an upward adjustment in market value.",
        "{name} earned MVP honors at a regional showcase, putting multiple programs on high alert ahead of the signing period.",
    ],
    "Rivals Rankings Update": [
        "Rivals updated their board following spring evaluation, bumping {name} after film review of their most recent season.",
        "A consensus re-ranking among major services elevated {name} following a strong spring game performance.",
        "Updated algorithmic composite scores reflect new Rivals data, pushing {name}'s market value above prior estimates.",
        "Cross-platform grade reconciliation between 247Sports and Rivals resulted in an upward move for {name}.",
        "Post-spring rankings refresh: {name} gained ground after evaluators factored in position-group depth at target schools.",
    ],
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # ── Fetch candidate players ────────────────────────────────────────────
    print("Fetching players from Supabase ...")
    resp = (
        supabase.table("players")
        .select("id, name, cfo_valuation")
        .gt("cfo_valuation", 0)
        .execute()
    )

    players = resp.data or []
    if len(players) < 3:
        raise RuntimeError(
            f"Need at least 3 eligible players, found {len(players)}. "
            "Ensure players with cfo_valuation > 0 exist in the database."
        )

    selected = random.sample(players, 3)
    print(f"  Selected {len(selected)} players for scouting proposals.\n")

    # ── Build proposals ────────────────────────────────────────────────────
    today      = datetime.date.today().isoformat()
    proposals  = []

    for player in selected:
        event_type  = random.choice(EVENT_TYPES)
        bump_pct    = random.uniform(0.10, 0.20)
        current_val = player["cfo_valuation"]
        proposed_val = round(current_val * (1 + bump_pct) / 1000) * 1000  # round to nearest $1k

        template    = random.choice(DESCRIPTIONS[event_type])
        description = template.format(name=player["name"].split()[0])  # first name only

        proposals.append({
            "player_id":          player["id"],
            "event_type":         event_type,
            "event_date":         today,
            "current_valuation":  current_val,
            "proposed_valuation": proposed_val,
            "reported_deal":      None,
            "description":        description,
            "status":             "pending",
        })

        bump_display = f"+{(bump_pct * 100):.1f}%"
        print(
            f"  {player['name']:<30} "
            f"${current_val:>9,}  →  ${proposed_val:>9,}  ({bump_display})  [{event_type}]"
        )

    # ── Insert into proposed_events ────────────────────────────────────────
    print("\nInserting proposals into proposed_events ...")
    result = supabase.table("proposed_events").insert(proposals).execute()
    print(f"\nSuccess: {len(result.data)} proposals queued for review in the Admin Feed.")
    print("Visit /admin to approve or reject them.\n")


if __name__ == "__main__":
    main()
