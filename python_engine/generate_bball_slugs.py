"""
Generate URL slugs for all basketball teams and players.
Handles duplicate names by appending team slug.
Mirrors generate_slugs.py (football).

Usage: python generate_bball_slugs.py [--dry-run]
"""

import logging
import sys
import re
import unicodedata
from supabase_client import supabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    text = text.strip("-")
    return text


def main():
    dry_run = "--dry-run" in sys.argv

    # ── Teams ────────────────────────────────────────────────────────────
    log.info("Generating basketball team slugs...")
    teams_resp = supabase.table("basketball_teams").select("id, university_name, slug").execute()
    teams = teams_resp.data or []

    team_id_to_slug = {}
    team_updates = 0
    for t in teams:
        slug = slugify(t["university_name"])
        team_id_to_slug[t["id"]] = slug

        if t.get("slug") == slug:
            continue

        if dry_run:
            log.info(f"  [DRY RUN] {t['university_name']} -> /basketball/teams/{slug}")
        else:
            supabase.table("basketball_teams").update({"slug": slug}).eq("id", t["id"]).execute()
        team_updates += 1

    log.info(f"Teams: {team_updates} slugs {'would be ' if dry_run else ''}updated")

    # ── Players ──────────────────────────────────────────────────────────
    log.info("Fetching all basketball players...")
    all_players = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            supabase.table("basketball_players")
            .select("id, name, team_id, slug")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        all_players.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    log.info(f"Found {len(all_players)} players")

    # First pass: generate base slugs and find duplicates
    base_slugs = {}
    for p in all_players:
        base = slugify(p["name"])
        base_slugs.setdefault(base, []).append(p)

    # Second pass: resolve duplicates by appending team slug
    final_slugs = {}  # player_id -> slug
    slug_set = set()  # track all assigned slugs for uniqueness

    for base, players in base_slugs.items():
        if len(players) == 1:
            slug = base
            if slug in slug_set:
                slug = f"{base}-{players[0]['id'][:8]}"
            slug_set.add(slug)
            final_slugs[players[0]["id"]] = slug
        else:
            for p in players:
                team_slug = team_id_to_slug.get(p.get("team_id"), "")
                if team_slug:
                    slug = f"{base}-{team_slug}"
                else:
                    slug = f"{base}-{p['id'][:8]}"

                if slug in slug_set:
                    slug = f"{slug}-{p['id'][:8]}"

                slug_set.add(slug)
                final_slugs[p["id"]] = slug

    dup_groups = len([k for k, v in base_slugs.items() if len(v) > 1])
    unique_names = len(base_slugs) - dup_groups
    log.info(f"Generated {len(final_slugs)} slugs ({unique_names} unique names, {dup_groups} duplicate groups)")

    # Write slugs
    player_updates = 0
    player_skipped = 0
    for p in all_players:
        new_slug = final_slugs.get(p["id"])
        if not new_slug:
            continue
        if p.get("slug") == new_slug:
            player_skipped += 1
            continue

        if dry_run:
            if player_updates < 20:
                log.info(f"  [DRY RUN] {p['name']} -> /basketball/players/{new_slug}")
        else:
            try:
                supabase.table("basketball_players").update({"slug": new_slug}).eq("id", p["id"]).execute()
            except Exception:
                fallback_slug = f"{new_slug}-{p['id'][:8]}"
                log.warning(f"  Slug collision for {p['name']}: {new_slug} -> {fallback_slug}")
                supabase.table("basketball_players").update({"slug": fallback_slug}).eq("id", p["id"]).execute()
        player_updates += 1

    log.info(f"Players: {player_updates} slugs {'would be ' if dry_run else ''}updated, {player_skipped} already correct")
    if dry_run:
        log.info("(Dry run -- no changes written)")


if __name__ == "__main__":
    main()
