"""
supabase_client.py
------------------
Shared Supabase client for all python_engine scripts.
Uses the SERVICE ROLE KEY — bypasses Row Level Security.

Import with:
    from supabase_client import supabase
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))

_url      = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
_svc_key  = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not _url:
    raise EnvironmentError("Missing NEXT_PUBLIC_SUPABASE_URL in .env.local")
if not _svc_key:
    raise EnvironmentError(
        "Missing SUPABASE_SERVICE_ROLE_KEY in .env.local\n"
        "Never use the anon key for backend write operations."
    )

supabase: Client = create_client(_url, _svc_key)
