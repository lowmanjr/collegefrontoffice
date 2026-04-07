# DEPRECATED — See calculate_cfo_valuations.py and VALUATION_ENGINE.md
import pandas as pd
import uuid
from datetime import datetime

# --- Raw player data matching the `players` table schema (Section 3) ---
# id and cfo_valuation are generated programmatically below.
# experience_level values: "High School" | "Active Roster" | "Portal"

players_raw = [
    # name,                   high_school,                   position, star_rating, experience_level, composite_score
    ("Marcus Williams",       "IMG Academy (FL)",            "QB",      5,           "Active Roster",  0.9998),
    ("Deion Carter",          "St. Thomas Aquinas (FL)",     "QB",      4,           "Portal",         0.9412),
    ("Jaylen Brooks",         "Mater Dei (CA)",              "WR",      5,           "Active Roster",  0.9876),
    ("Tre'von Mitchell",      "North Shore (TX)",            "WR",      4,           "Portal",         0.9204),
    ("Calvin Osei",           "Buford (GA)",                 "WR",      3,           "High School",    0.8751),
    ("Darius Hunt",           "Trinity (KY)",                "LT",      5,           "Portal",         0.9945),
    ("Quentin Moss",          "Duncanville (TX)",            "LT",      4,           "Active Roster",  0.9317),
    ("Elijah Ford",           "Chandler (AZ)",               "EDGE",    5,           "Active Roster",  0.9889),
    ("Malik Reeves",          "Cedar Hill (TX)",             "EDGE",    4,           "Portal",         0.9101),
    ("Chris Lampley",         "Centennial (NV)",             "EDGE",    3,           "Active Roster",  0.8602),
    ("Javonte Harris",        "Grayson (GA)",                "CB",      5,           "Portal",         0.9923),
    ("Terrell Simmons",       "Edna Karr (LA)",              "CB",      4,           "Active Roster",  0.9255),
    ("Devon King",            "St. John Bosco (CA)",         "CB",      3,           "High School",    0.8490),
    ("Amon Blackwell",        "Allen (TX)",                  "DT",      5,           "Active Roster",  0.9867),
    ("Rasheed Owens",         "Warren Easton (LA)",          "DT",      4,           "Portal",         0.9078),
    ("Bryce Coleman",         "Katy (TX)",                   "RB",      4,           "Active Roster",  0.9186),
    ("Isaiah Grant",          "Venice (FL)",                 "RB",      3,           "Portal",         0.8344),
    ("Tanner Walsh",          "Bishop Gorman (NV)",          "TE",      4,           "High School",    0.8933),
    ("Kendall Price",         "Booker T. Washington (OK)",   "OLB",     3,           "Active Roster",  0.8215),
    ("Freddie Langston",      "Southwest DeKalb (GA)",       "S",       4,           "Portal",         0.9022),
]

# --- C.F.O. Valuation Algorithm V1.0 (Section 4) ---

BASE_RATES = {5: 100_000, 4: 50_000, 3: 25_000}

POSITIONAL_MULTIPLIERS = {
    "QB":   2.5,
    "LT":   1.5,
    "EDGE": 1.5,
    "WR":   1.2,
    "CB":   1.2,
    "DT":   1.2,
}

EXPERIENCE_MULTIPLIERS = {
    "Portal":        3.0,
    "Active Roster": 2.0,
    "High School":   1.0,
}


def calculate_cfo_valuation(star_rating: int, position: str, experience_level: str) -> int:
    """
    Total Value = Base Rate * Positional Multiplier * Experience Multiplier
    Returns an integer dollar value.
    """
    base_rate = BASE_RATES[star_rating]
    pos_multiplier = POSITIONAL_MULTIPLIERS.get(position, 1.0)  # default 1.0 for all others
    exp_multiplier = EXPERIENCE_MULTIPLIERS[experience_level]
    return int(base_rate * pos_multiplier * exp_multiplier)


# --- Build the DataFrame ---

records = []
for (name, high_school, position, star_rating, experience_level, composite_score) in players_raw:
    records.append({
        "id":               str(uuid.uuid4()),
        "name":             name,
        "high_school":      high_school,
        "position":         position,
        "star_rating":      star_rating,
        "experience_level": experience_level,
        "composite_score":  composite_score,
        "cfo_valuation":    calculate_cfo_valuation(star_rating, position, experience_level),
        "last_updated":     datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    })

df = pd.DataFrame(records, columns=[
    "id", "name", "high_school", "position",
    "star_rating", "experience_level", "composite_score",
    "cfo_valuation", "last_updated",
])

# --- Export to Excel ---

output_path = "../cfo_sandbox.xlsx"
df.to_excel(output_path, index=False, sheet_name="Players")

print(f"Done. {len(df)} players written to {output_path}")
print(df[["name", "position", "star_rating", "experience_level", "cfo_valuation"]].to_string(index=False))
