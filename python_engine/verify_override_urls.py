"""
verify_override_urls.py
------------------------
Checks all nil_overrides source URLs for validity (HTTP 200).
Broken links are set to NULL with a note in source_name.

Usage:
    python verify_override_urls.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import requests
from supabase_client import supabase

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}


def check_url(url: str) -> tuple[str, int | None, str | None]:
    """Returns (status: 'ok'|'redirect'|'broken', code, final_url)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if resp.status_code == 200:
            if resp.url != url:
                return "redirect", resp.status_code, resp.url
            return "ok", resp.status_code, resp.url
        return "broken", resp.status_code, None
    except requests.exceptions.RequestException as exc:
        return "broken", None, str(exc)[:80]


def main():
    print("=" * 100)
    print("  VERIFY OVERRIDE SOURCE URLs")
    print("=" * 100)

    resp = supabase.table("nil_overrides").select(
        "player_id, name, annualized_value, source_name, source_url"
    ).not_.is_("source_url", "null").execute()

    rows = resp.data or []
    print(f"  Rows with non-NULL source_url: {len(rows)}\n")

    ok = 0
    redirected = 0
    broken = 0

    for r in rows:
        name = r.get("name") or "(legacy)"
        url = r["source_url"]
        source = r.get("source_name") or "?"

        status, code, final = check_url(url)

        if status == "ok":
            print(f"  OK  {name:<28} {url[:70]}")
            ok += 1
        elif status == "redirect":
            print(f"  ~>  {name:<28} {url[:70]}")
            print(f"      Redirected to: {final[:70]}")
            redirected += 1
        else:
            code_str = str(code) if code else "ERR"
            print(f"  XX  {name:<28} {url[:70]}")
            print(f"      Status: {code_str}  {final or ''}")

            # Fix: null out the URL and flag source_name
            new_source = source
            if "(link removed" not in new_source:
                new_source = f"{source} (link removed - unverified)"
            supabase.table("nil_overrides").update({
                "source_url": None,
                "source_name": new_source,
            }).eq("player_id", r["player_id"]).execute()
            print(f"      -> Set source_url=NULL, flagged source_name")
            broken += 1

    print(f"\n{'=' * 60}")
    print(f"  SUMMARY")
    print(f"{'=' * 60}")
    print(f"  OK (200):         {ok}")
    print(f"  Redirected:       {redirected}")
    print(f"  Broken (removed): {broken}")
    print(f"  Total checked:    {len(rows)}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
