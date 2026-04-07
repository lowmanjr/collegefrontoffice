# DEPRECATED — See calculate_cfo_valuations.py and VALUATION_ENGINE.md
import os
import numpy as np
import pandas as pd
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

# --- Read sandbox Excel file ---
xlsx_path = os.path.join(os.path.dirname(__file__), "..", "cfo_sandbox.xlsx")
df = pd.read_excel(xlsx_path, sheet_name="Players")

# --- Clean: replace NaN with None so the payload is JSON-serializable ---
df = df.replace({np.nan: None})

# --- Convert to list of dicts ---
records = df.to_dict(orient="records")

# --- Insert into Supabase `players` table ---
response = supabase.table("players").insert(records).execute()

print(f"Success: {len(response.data)} records inserted into the 'players' table.")
