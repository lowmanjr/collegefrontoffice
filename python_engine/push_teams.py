import os
from dotenv import load_dotenv
from supabase import create_client, Client

# --- Load credentials from .env.local ---
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise EnvironmentError(
        "Missing Supabase credentials. "
        "Ensure NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY "
        "are set in .env.local"
    )

# --- Initialize Supabase client ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --- Team data (schema: university_name, conference, estimated_cap_space, active_payroll) ---
teams = [
    {
        "university_name": "Ohio State",
        "conference": "Big Ten",
        "estimated_cap_space": 20_500_000,
        "active_payroll": 19_500_000,
    },
    {
        "university_name": "Georgia",
        "conference": "SEC",
        "estimated_cap_space": 20_500_000,
        "active_payroll": 18_200_000,
    },
    {
        "university_name": "Texas",
        "conference": "SEC",
        "estimated_cap_space": 20_500_000,
        "active_payroll": 16_750_000,
    },
    {
        "university_name": "Oregon",
        "conference": "Big Ten",
        "estimated_cap_space": 20_500_000,
        "active_payroll": 14_000_000,
    },
    {
        "university_name": "Alabama",
        "conference": "SEC",
        "estimated_cap_space": 20_500_000,
        "active_payroll": 17_400_000,
    },
]

# --- Insert into Supabase `teams` table ---
response = supabase.table("teams").insert(teams).execute()

print(f"Success: {len(response.data)} teams inserted into the 'teams' table.")
for team in response.data:
    cap_remaining = team["estimated_cap_space"] - team["active_payroll"]
    print(
        f"  {team['university_name']} ({team['conference']}) — "
        f"Payroll: ${team['active_payroll']:,} | "
        f"Remaining: ${cap_remaining:,}"
    )
