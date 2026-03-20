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

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

logos = [
    {"university_name": "Ohio State", "logo_url": "https://a.espncdn.com/i/teamlogos/ncaa/500/194.png"},
    {"university_name": "Georgia",    "logo_url": "https://a.espncdn.com/i/teamlogos/ncaa/500/61.png"},
    {"university_name": "Alabama",    "logo_url": "https://a.espncdn.com/i/teamlogos/ncaa/500/333.png"},
    {"university_name": "Texas",      "logo_url": "https://a.espncdn.com/i/teamlogos/ncaa/500/251.png"},
    {"university_name": "Oregon",     "logo_url": "https://a.espncdn.com/i/teamlogos/ncaa/500/248.png"},
]

for entry in logos:
    response = (
        supabase.table("teams")
        .update({"logo_url": entry["logo_url"]})
        .eq("university_name", entry["university_name"])
        .execute()
    )
    if response.data:
        print(f"  Updated {entry['university_name']} -> {entry['logo_url']}")
    else:
        print(f"  WARNING: No row found for '{entry['university_name']}'")

print("Done.")
