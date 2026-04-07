"""
ingest_eada_finances.py
-----------------------
Reads verified federal EADA financial data from two Excel files and pushes
total athletics revenue, football revenue, and football expenses to the
Supabase `teams` table.

Sources:
  - instLevel.xlsx  : institution-level aggregates (macro)
  - EADA_2024.xlsx  : sport-level breakdowns (micro) — wide format, one row/school

Target columns (must exist on `teams` table):
  total_athletics_revenue  INTEGER
  total_football_revenue   INTEGER
  total_football_expenses  INTEGER
  reporting_year           TEXT
"""

import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# 1. SETUP & CREDENTIALS
# ---------------------------------------------------------------------------
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise EnvironmentError(
        "Missing Supabase credentials. "
        "Ensure NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY "
        "are set in .env.local"
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ---------------------------------------------------------------------------
# 2. ALIAS DICTIONARY
#    Key   : clean university_name stored in our `teams` table (lowercase)
#    Value : exact institution_name string in the EADA files
# ---------------------------------------------------------------------------
ALIAS_MAP: dict[str, str] = {
    # SEC
    "alabama":       "The University of Alabama",
    "georgia":       "University of Georgia",
    "texas":         "The University of Texas at Austin",
    "lsu":           "Louisiana State University and Agricultural & Mechanical College",
    "tennessee":     "The University of Tennessee-Knoxville",
    "auburn":        "Auburn University",
    "florida":       "University of Florida",
    "arkansas":      "University of Arkansas",
    "ole miss":      "University of Mississippi",
    "mississippi":   "University of Mississippi",
    "miss state":    "Mississippi State University",
    "south carolina":"University of South Carolina-Columbia",
    "missouri":      "University of Missouri-Columbia",
    "kentucky":      "University of Kentucky",
    "vanderbilt":    "Vanderbilt University",
    "texas a&m":     "Texas A & M University-College Station",
    "texas am":      "Texas A & M University-College Station",

    # Big Ten
    "ohio state":    "Ohio State University-Main Campus",
    "oregon":        "University of Oregon",
    "michigan":      "University of Michigan-Ann Arbor",
    "penn state":    "Pennsylvania State University-Main Campus",
    "iowa":          "University of Iowa",
    "wisconsin":     "University of Wisconsin-Madison",
    "michigan state":"Michigan State University",
    "minnesota":     "University of Minnesota-Twin Cities",
    "indiana":       "Indiana University-Bloomington",
    "illinois":      "University of Illinois Urbana-Champaign",
    "nebraska":      "University of Nebraska-Lincoln",
    "purdue":        "Purdue University-Main Campus",
    "rutgers":       "Rutgers University-New Brunswick",
    "maryland":      "University of Maryland-College Park",
    "northwestern":  "Northwestern University",
    "ucla":          "University of California-Los Angeles",
    "washington":    "University of Washington-Seattle Campus",
    "usc":           "University of Southern California",
    "usc trojans":   "University of Southern California",

    # Big 12
    "baylor":        "Baylor University",
    "tcu":           "Texas Christian University",
    "texas tech":    "Texas Tech University",
    "oklahoma":      "University of Oklahoma-Norman Campus",
    "oklahoma state":"Oklahoma State University-Main Campus",
    "kansas":        "University of Kansas",
    "kansas state":  "Kansas State University",
    "iowa state":    "Iowa State University",
    "west virginia": "West Virginia University",
    "cincinnati":    "University of Cincinnati-Main Campus",
    "houston":       "University of Houston",
    "ucf":           "University of Central Florida",
    "byu":           "Brigham Young University",
    "colorado":      "University of Colorado Boulder",
    "utah":          "University of Utah",
    "arizona":       "University of Arizona",

    # ACC
    "clemson":       "Clemson University",
    "notre dame":    "University of Notre Dame",
    "florida state": "Florida State University",
    "north carolina":"University of North Carolina at Chapel Hill",
    "unc":           "University of North Carolina at Chapel Hill",
    "nc state":      "North Carolina State University at Raleigh",
    "virginia":      "University of Virginia-Main Campus",
    "virginia tech": "Virginia Polytechnic Institute and State University",
    "georgia tech":  "Georgia Institute of Technology-Main Campus",
    "miami":         "University of Miami",
    "duke":          "Duke University",
    "wake forest":   "Wake Forest University",
    "pittsburgh":    "University of Pittsburgh-Pittsburgh Campus",
    "pitt":          "University of Pittsburgh-Pittsburgh Campus",
    "syracuse":      "Syracuse University",
    "boston college":"Boston College",
    "louisville":    "University of Louisville",
    "stanford":      "Stanford University",
    "cal":           "University of California-Berkeley",
    "oregon state":  "Oregon State University",
    "washington state":"Washington State University",

    # Group of 5 / notable independents
    "army":          "United States Military Academy",
    "navy":          "United States Naval Academy",
}

REPORTING_YEAR = "FY2023"
SCRIPT_DIR = os.path.dirname(__file__)

# ---------------------------------------------------------------------------
# 3. LOAD EXCEL FILES
# ---------------------------------------------------------------------------
print("Loading Excel files...")
inst_df = pd.read_excel(os.path.join(SCRIPT_DIR, "instLevel.xlsx"))
eada_df = pd.read_excel(os.path.join(SCRIPT_DIR, "EADA_2024.xlsx"))

# Normalise institution_name for reliable lookup
inst_df["_inst_key"] = inst_df["institution_name"].str.strip()
eada_df["_inst_key"] = eada_df["institution_name"].str.strip()

print(f"  instLevel.xlsx : {len(inst_df):,} rows")
print(f"  EADA_2024.xlsx : {len(eada_df):,} rows")

# ---------------------------------------------------------------------------
# 4. FETCH TEAMS FROM SUPABASE
# ---------------------------------------------------------------------------
print("\nFetching teams from Supabase...")
response = supabase.table("teams").select("id, university_name").execute()
teams = response.data
print(f"  Found {len(teams)} teams: {[t['university_name'] for t in teams]}")

# ---------------------------------------------------------------------------
# 5. MATCH & UPDATE
# ---------------------------------------------------------------------------
print("\nProcessing financial data...\n")
print(f"{'Team':<20} {'EADA Name':<55} {'Total Rev':>15} {'FB Rev':>14} {'FB Exp':>14}")
print("-" * 120)

matched = 0
skipped = 0

for team in teams:
    team_id   = team["id"]
    clean_name = team["university_name"]
    lookup_key = clean_name.strip().lower()

    # Resolve EADA institution name via alias map
    eada_name = ALIAS_MAP.get(lookup_key)
    if not eada_name:
        print(f"  [SKIP] '{clean_name}' — no alias mapping found")
        skipped += 1
        continue

    # --- Macro: total athletics revenue from instLevel.xlsx ---
    inst_row = inst_df[inst_df["_inst_key"] == eada_name]
    if inst_row.empty:
        print(f"  [SKIP] '{clean_name}' — '{eada_name}' not found in instLevel.xlsx")
        skipped += 1
        continue

    total_athletics_revenue = int(inst_row["GRND_TOTAL_REVENUE"].iloc[0] or 0)

    # --- Micro: football revenue & expenses from EADA_2024.xlsx ---
    eada_row = eada_df[eada_df["_inst_key"] == eada_name]
    if eada_row.empty:
        print(f"  [SKIP] '{clean_name}' — '{eada_name}' not found in EADA_2024.xlsx")
        skipped += 1
        continue

    total_football_revenue  = int(eada_row["TOTAL_REVENUE_ALL_Football"].iloc[0]  or 0)
    total_football_expenses = int(eada_row["TOTAL_EXPENSE_ALL_Football"].iloc[0]  or 0)

    # --- Push to Supabase ---
    supabase.table("teams").update({
        "total_athletics_revenue": total_athletics_revenue,
        "total_football_revenue":  total_football_revenue,
        "total_football_expenses": total_football_expenses,
        "reporting_year":          REPORTING_YEAR,
    }).eq("id", team_id).execute()

    print(
        f"  {clean_name:<18} {eada_name:<55} "
        f"${total_athletics_revenue:>14,} "
        f"${total_football_revenue:>13,} "
        f"${total_football_expenses:>13,}"
    )
    matched += 1

# ---------------------------------------------------------------------------
# 6. SUMMARY
# ---------------------------------------------------------------------------
print("\n" + "=" * 120)
print(f"Done.  Updated: {matched} team(s)   Skipped: {skipped} team(s)   Reporting year: {REPORTING_YEAR}")
