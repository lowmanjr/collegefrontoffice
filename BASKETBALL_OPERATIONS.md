# College Front Office — Basketball Operations Runbook

> **Last Updated:** April 16, 2026
> **Scope:** Men's college basketball NIL valuations
> **Current teams:** 82 — All Power 4 (SEC, Big Ten, Big 12, ACC), Full Big East, Gonzaga (WCC), Memphis (AAC), San Diego State (MWC)
> **Current state:** V1.4 engine, ~848 valued players, 550 HS recruits (259/210/81 across 2026/2027/2028), 27 overrides (10 market-anchored + 17 editorial)
> **Companion docs:** `BASKETBALL_VALUATION_ENGINE.md` (formula detail), `BASKETBALL_CALIBRATION_V1.4.md` (CFO vs On3 reference), `OPERATIONS.md` (football pipeline reference)

---

## 1. Overview

The basketball product produces CFO Valuations for men's college basketball players across tracked Power 4 programs. Each player receives an integer dollar value representing their estimated annualized NIL market value, computed by a multiplicative formula with six components (position base, NBA draft premium, role tier, talent modifier, market multiplier, experience multiplier) plus an additive social premium.

The tech stack is identical to football: Next.js (App Router) on Vercel, Supabase (PostgreSQL), Python data pipeline. Basketball uses its own set of tables (`basketball_teams`, `basketball_players`, `basketball_nil_overrides`, `basketball_player_events`) and its own pipeline scripts (all prefixed `*_bball_*` or `*_basketball_*`).

The valuation engine is V1.4. See `BASKETBALL_VALUATION_ENGINE.md` for the full formula specification.

---

## 2. Environment Setup

### 2.1 Required Environment Variables

Same as football — set in `.env` or shell profile:

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (bypasses RLS) |

Both are read by `python_engine/supabase_client.py`, which is shared across football and basketball scripts.

### 2.2 Python Dependencies

All basketball scripts use the same `requirements.txt` as football:

```bash
cd python_engine && pip install -r requirements.txt
```

Key packages: `supabase`, `requests`, `beautifulsoup4`, `pandas`.

### 2.3 Verify Setup

```bash
cd python_engine && python3 -c "
from supabase_client import supabase
t = supabase.table('basketball_teams').select('university_name, slug, market_multiplier').execute()
for r in t.data:
    print(r)
"
```

Expected output: all 82 tracked teams with their market multipliers.

---

## 3. Adding a New Team

Step-by-step for onboarding any new program. This is the most critical section — follow in exact order.

**Bulk expansion (April 2026):** The initial 82-team universe was seeded via `expand_to_basketball_universe.py`, which reads `data/basketball_expansion_teams.csv` (82 rows with ESPN IDs, market multipliers, and conference assignments). That script is idempotent — it skips existing teams and only inserts new ones. The manual §3 process below is for individual team additions going forward (e.g., adding a mid-major not in the current universe).

**Automation note:** All pipeline scripts load teams dynamically from `basketball_teams`. The ESPN team ID is derived from `logo_url` automatically. The only script file that needs updating for a new team is adding their On3 org key to `ON3_ORG_KEYS` in `enrich_bball_social_data.py` (see §3.3a).

### 3.1 Find ESPN Team ID

```bash
curl -s "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams" | python3 -c "
import sys, json
data = json.load(sys.stdin)
teams = data.get('sports',[{}])[0].get('leagues',[{}])[0].get('teams',[])
for t in teams:
    team = t.get('team', {})
    name = team.get('displayName','')
    if 'SCHOOL_NAME' in name.lower():
        print(f'ID: {team[\"id\"]} | {name}')
"
```

Replace `SCHOOL_NAME` with the target school name (case-insensitive substring match).

### 3.2 Determine Market Multiplier

Reference table from `BASKETBALL_VALUATION_ENGINE.md` §3.5:

| Program Tier | Range | Examples |
|---|---|---|
| Blue blood | 1.25–1.35 | Duke, Kentucky, Kansas, UNC, UCLA |
| Elite Power 4 | 1.15–1.24 | Gonzaga, Houston, Villanova |
| Strong Power 4 | 1.05–1.14 | BYU (1.08), Iowa State, Arkansas |
| Mid-major (A-10, MWC, WCC) | 0.55–0.75 | — |
| Lower D1 | 0.30–0.50 | — |

Basketball market multipliers are calibrated **independently** from football. Duke basketball (1.30) ≠ Duke football (1.05).

### 3.3 Seed the Team

```bash
cd python_engine && python3 -c "
from supabase_client import supabase
result = supabase.table('basketball_teams').insert({
    'university_name': 'SCHOOL_NAME',
    'conference': 'CONFERENCE',
    'logo_url': 'https://a.espncdn.com/i/teamlogos/ncaa/500/ESPN_ID.png',
    'market_multiplier': MULTIPLIER,
    'estimated_nil_pool': NIL_POOL,
    'slug': 'SLUG'
}).execute()
print('Inserted:', result.data)
"
```

Replace all UPPERCASE placeholders. `estimated_nil_pool` guidelines:

| Program Tier | Estimated NIL Pool |
|---|---|
| Blue blood | $3,000,000–$5,000,000 |
| Strong Power 4 | $800,000–$2,000,000 |
| Mid-major | $300,000–$800,000 |

### 3.3a Update On3 Org Key (for Social Enrichment)

Add the team's On3 organization key to `ON3_ORG_KEYS` in `enrich_bball_social_data.py`:

```python
ON3_ORG_KEYS: dict[str, int] = {
    "BYU": 21364,
    "Kentucky": 12013,
    "UConn": 24966,
    "SCHOOL_NAME": ON3_KEY,  # add new team here
}
```

This is the **only script file that needs updating** for a new team. To find the On3 org key: search for the team at `https://www.on3.com/nil/rankings/player/nil-100/?team-key=XXXXX` or inspect the URL on their On3 school page.

### 3.3b Portal Player Auto-Linking

When a new school is onboarded, portal players already in `basketball_players` with `team_id = NULL` and a matching `espn_athlete_id` are automatically linked to the new team during `ingest_bball_espn_rosters.py`. This happens because `enrich_bball_portal_players.py` creates records for incoming portal players from non-tracked schools with `team_id = NULL`. When that school is later added to `basketball_teams`, the ESPN roster ingest matches by `espn_athlete_id` and fills in `team_id`.

**ESPN ingest guard:** `ingest_bball_espn_rosters.py` protects portal-managed players via `PROTECTED_ACQUISITION` (`portal`, `portal_evaluating`) and `PROTECTED_ROSTER` (`departed_transfer`) sets. Players with a non-NULL `team_id` and a protected acquisition type or roster status are never overwritten by the ESPN roster ingest. Players with `team_id = NULL` are always eligible for linking regardless of acquisition type.

### 3.4 Run the Full Pipeline

Run in this exact order:

```bash
cd python_engine

# 1. Import roster from ESPN
python ingest_bball_espn_rosters.py --team SLUG

# 2. Verify headshots resolve (fixes broken URLs, NULLs missing ones)
python fix_bball_headshots.py --team SLUG

# 3. Enrich stats (MPG → role_tier, PER, ppg/rpg/apg)
python enrich_bball_usage_rates.py --team SLUG

# 4. Enrich class years from ESPN experience data (runs all teams)
python enrich_bball_class_years.py

# 5. Enrich star ratings from recruiting CSV (see §4)
#    Create data/{SLUG}_basketball_recruits_2025.csv FIRST
python enrich_bball_star_ratings.py --team SLUG

# 6. Scrape recruit headshots from 247Sports
python scrape_bball_247_headshots.py

# 7. Compute valuations
python calculate_bball_valuations.py --team SLUG

# 8. Apply any known deals
python apply_bball_overrides.py

# 9. Generate URL slugs
python generate_bball_slugs.py
```

**Note:** ESPN CDN headshots for incoming freshmen may return 404 early in the season. Re-run `fix_bball_headshots.py` in November once ESPN populates new player photos.

### 3.5 Verify

```bash
cd python_engine && python3 -c "
from supabase_client import supabase
team = supabase.table('basketball_teams') \
    .select('id, university_name') \
    .eq('slug', 'SLUG').single().execute()
players = supabase.table('basketball_players') \
    .select('name, position, role_tier, cfo_valuation, slug') \
    .eq('team_id', team.data['id']) \
    .order('cfo_valuation', desc=True).execute()
print(f'{team.data[\"university_name\"]} — {len(players.data)} players')
issues = [p['name'] for p in players.data \
    if not p['slug'] or not p['cfo_valuation']]
print(f'Issues: {issues if issues else \"None\"}')
total = sum(p['cfo_valuation'] or 0 for p in players.data)
print(f'Roster total: \${total:,}')
"
```

Replace `SLUG` with the team slug. Expected: 13–17 players, zero issues, total within conference band.

---

## 4. National Recruit Pipeline

High school recruits are managed via national CSV files organized by class year, not per-team CSVs. The CSVs are generated from live 247Sports data via `parse_raw_247_recruits.py`. The `build_bball_recruit_csvs.py` script is the source of truth for the hardcoded Python lists and regenerates CSVs without re-scraping.

**Current scale:** 550 recruits — 2026 (259), 2027 (210), 2028 (81). All 4★+ receive valuations and 247 headshots.

### 4.1 Pipeline Steps (Run During Signing Periods)

```bash
cd python_engine

# 1. Scrape fresh data from 247Sports (writes CSV + prints Python list)
python parse_raw_247_recruits.py --year 2026
python parse_raw_247_recruits.py --year 2027
python parse_raw_247_recruits.py --year 2028

# 2. (Optional) Paste the printed RECRUITS_{year} list into
#    build_bball_recruit_csvs.py to keep hardcoded source in sync

# 3. Regenerate CSVs from build script (idempotent)
python build_bball_recruit_csvs.py

# 4. Ingest recruits into basketball_players
python ingest_bball_recruits.py

# 5. Calculate valuations
python calculate_bball_valuations.py

# 6. Apply known deal values
python apply_bball_overrides.py

# 7. Generate URL slugs for new players
python generate_bball_slugs.py

# 8. Scrape 247Sports headshots for new recruits
python scrape_bball_247_headshots.py
```

**Dedup note:** When the same recruit is ingested via both the older hardcoded list and newer scraped data, duplicates can appear with identical `espn_athlete_id` values. Run a dedup pass by grouping on `espn_athlete_id` within `hs_grad_year` and deleting all but the newest record (by `created_at`).

### 4.2 CSV Files

| File | Contents |
|------|----------|
| `data/basketball_recruits_2026.csv` | Committed 2026 class (national) |
| `data/basketball_recruits_2027.csv` | National 4-star+ big board |
| `data/basketball_recruits_2028.csv` | National 4-star+ big board |

Format:

```csv
espn_athlete_id,player_name,star_rating,composite_score,position_247,committed_school_slug,hs_grad_year
hs2026_aj-dybantsa,AJ Dybantsa,5,0.9999,SF,byu,2026
```

The `espn_athlete_id` uses a deterministic placeholder format `hs{year}_{slug}` for recruits who don't yet have an ESPN athlete ID. When a recruit enrolls and receives an ESPN ID, the placeholder is updated during `ingest_bball_espn_rosters.py`.

### 4.3 Data Source

247Sports basketball composite rankings (public). Recruit lists in `build_bball_recruit_csvs.py` are updated manually as commits are announced or rankings shift.

### 4.4 Legacy Per-Team CSVs

The original per-team CSV approach (`data/{slug}_basketball_recruits_2025.csv` + `enrich_bball_star_ratings.py`) is still supported for star rating enrichment but is superseded by the national pipeline for new recruit ingestion.

---

## 5. Valuation Refresh (Existing Team)

Run when: stats update mid-season, class years change, new draft projections emerge, or social data needs refreshing.

### 5.1 Single Team

```bash
cd python_engine
python enrich_bball_usage_rates.py --team SLUG    # if stats updated
python enrich_bball_class_years.py                # if new season (runs all teams)
python sync_nba_draft_projections.py              # if mock drafts shifted
python calculate_bball_valuations.py --team SLUG  # always
python apply_bball_overrides.py                   # always
```

### 5.2 Full Refresh (All Teams)

```bash
cd python_engine
python sync_nba_draft_projections.py              # ESPN draft API → DB
python enrich_bball_usage_rates.py
python calculate_bball_valuations.py
python apply_bball_overrides.py
```

### 5.3 Dry Run

Always available for previewing changes without writing to the database:

```bash
cd python_engine && python calculate_bball_valuations.py --dry-run
cd python_engine && python calculate_bball_valuations.py --dry-run --team SLUG
```

---

## 6. Seasonal Maintenance (Run Every April After Tournament)

After the NCAA Tournament concludes each April, run the full refresh sequence to update all teams to current season data:

```bash
cd python_engine

# 1. Update CURRENT_SEASON in enrich_bball_usage_rates.py to the new year

# 2. Re-ingest rosters (picks up new players, updates headshots)
python ingest_bball_espn_rosters.py
python fix_bball_headshots.py

# 3. Detect departed players (graduated, transferred, went pro)
python -c "
from supabase_client import supabase
import requests, time
teams = supabase.table('basketball_teams').select('id, university_name, logo_url').execute()
for team in teams.data:
    espn_id = team['logo_url'].split('/')[-1].replace('.png', '')
    resp = requests.get(f'https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams/{espn_id}/roster', timeout=10)
    current_ids = {str(a['id']) for a in resp.json().get('athletes', [])}
    db = supabase.table('basketball_players').select('id, name, espn_athlete_id').eq('team_id', team['id']).eq('roster_status', 'active').execute()
    departed = [p for p in db.data if p['espn_athlete_id'] not in current_ids]
    for p in departed:
        supabase.table('basketball_players').update({'roster_status': 'departed_other'}).eq('id', p['id']).execute()
        print(f'  {team[\"university_name\"]}: {p[\"name\"]} -> departed')
    time.sleep(1.0)
"

# 4. Enrich with new season stats
python enrich_bball_usage_rates.py

# 5. Update class years (freshmen -> sophomores, etc.)
python enrich_bball_class_years.py

# 6. Sync draft boards (ESPN updates after tournament)
python sync_nba_draft_projections.py

# 7. Recalculate all valuations
python calculate_bball_valuations.py
python apply_bball_overrides.py

# 8. Generate slugs for any new players
python generate_bball_slugs.py
```

**Key things to check after refresh:**
- Players who lost significant minutes (role tier drops → valuation drops)
- New draft prospects discovered by `sync_nba_draft_projections.py`
- Known deal values that may need updating for returning stars
- Override players who graduated or went pro (remove from `basketball_approved_overrides.csv`)

---

## 7. Managing Known Deal Values

When a reported NIL figure becomes public for a basketball player, or when an editorial valuation is applied to a recruit/player to align closer to market consensus.

**Two override types (V1.4):**
- **Market-anchored (sourced):** Overrides with a reputable non-On3 source URL. Currently 10 roster players (e.g., AJ Dybantsa $7M via Yahoo Sports). The source URL renders as a "Source: hostname" link under the valuation on the player profile page.
- **Editorial (unsourced):** Overrides without a source URL. Currently 17 recruits (e.g., Tyran Stokes $6M). Applied to align CFO valuations with On3's recruit market consensus where no reputable dollar reporting exists.

Total overrides: 27 (10 sourced + 17 editorial).

### 7.1 Confirm ESPN Athlete ID

```bash
cd python_engine && python3 -c "
from supabase_client import supabase
p = supabase.table('basketball_players') \
    .select('name, espn_athlete_id') \
    .ilike('name', '%PLAYER_NAME%').execute()
print(p.data)
"
```

### 7.2 Add to Overrides CSV

File: `python_engine/data/basketball_approved_overrides.csv`

Format:

```csv
espn_athlete_id,player_name,total_value,years,source_name,source_url
```

**Sourced override example:**

```csv
5142718,AJ Dybantsa,7000000,1,Yahoo Sports — reported $7M deal,https://sports.yahoo.com/articles/aj-dybantsa-nil-deals-explained-081002827.html
```

**Editorial override example (recruit, no source):**

```csv
hs2026_tyran_stokes,Tyran Stokes,6000000,1,,
```

`source_name` and `source_url` are optional. When `source_url` is present, `apply_bball_overrides.py` writes it to `basketball_players.override_source_url` and the player profile page renders a "Source: hostname" link under the valuation.

For multi-year deals, set `years` accordingly — the `annualized_value` column in `basketball_nil_overrides` is a generated column (`total_value / years`).

### 7.3 Apply

```bash
cd python_engine && python apply_bball_overrides.py
```

### 7.4 Verify

```bash
cd python_engine && python3 -c "
from supabase_client import supabase
p = supabase.table('basketball_players') \
    .select('name, cfo_valuation, is_override') \
    .ilike('name', '%PLAYER_NAME%').single().execute()
print(p.data)
"
```

### 7.5 Current Overrides (V1.4 — 27 total)

**Market-anchored roster players (10, sourced):**

| Player | Team | Value | Source |
|--------|------|-------|--------|
| AJ Dybantsa | BYU | $7,000,000 | Yahoo Sports |
| Yaxel Lendeborg | Michigan | $5,000,000 | CBS Sports |
| JT Toppin | Texas Tech | $4,000,000 | CBS Sports |
| P.J. Haggerty | Kansas State | $2,500,000 | Athlon Sports |
| Cameron Boozer | Duke | $2,200,000 | SI |
| Morez Johnson Jr. | Michigan | $2,000,000 | Yahoo Sports |
| Jayden Quaintance | Kentucky | $2,000,000 | Front Office Sports |
| Denzel Aberdeen | Florida | $2,000,000 | The Alligator |
| Boogie Fland | Florida | $2,000,000 | CBS Sports |
| Darryn Peterson | Kansas | $1,500,000 | Pro Football Network |

**Editorial recruit overrides (17, unsourced):** Tyran Stokes ($6M, Kentucky), Jordan Smith Jr. ($1.6M, Arkansas), Cam Williams ($1.5M, Duke), Caleb Holt ($1.4M, Arizona), plus 13 others in the $662K–$1.3M range. See `python_engine/data/basketball_approved_overrides.csv` for full list.

**Held (commented out):** Milan Momcilovic ($4.4M, UNC commit April 13 2026) — pending 2026 portal ingest to move player from Iowa State to UNC.

---

## 8. Social Data Enrichment

Scrapes On3 team NIL pages for per-player social follower counts (Instagram, Twitter/X, TikTok).

### 8.1 Run

```bash
cd python_engine && python enrich_bball_social_data.py --team SLUG
# Full refresh (all teams):
cd python_engine && python enrich_bball_social_data.py
```

### 8.2 Name Alias Handling

On3 player names sometimes differ from ESPN names in the database. When a player isn't matched during enrichment, add an alias to the `NAME_ALIASES` dict in `enrich_bball_social_data.py`:

```python
NAME_ALIASES: dict[str, str] = {
    "rob wright": "robert wright",
    # add others as discovered
}
```

Keys are the On3 normalized name (lowercase, no suffixes). Values are the DB normalized name.

---

## 9. NBA Draft Projections

### 9.1 Automated Sync (ESPN API)

```bash
cd python_engine && python sync_nba_draft_projections.py --dry-run    # preview
cd python_engine && python sync_nba_draft_projections.py              # sync + recalculate
cd python_engine && python sync_nba_draft_projections.py --season 2027  # next year's draft
```

The script fetches ESPN's draft prospects API, matches prospects to our DB by ESPN athlete ID, updates `basketball_players.nba_draft_projection`, writes a reference CSV to `data/nba_draft_projections_2025.csv`, and re-runs valuations automatically.

Run before `calculate_bball_valuations.py` when mock draft consensus shifts. The valuation engine reads draft projections directly from the DB column, not the CSV — the CSV is a reference file only.

### 9.2 Current Projections (ESPN API, April 2026)

| Player | Team | ESPN Rank |
|--------|------|-----------|
| AJ Dybantsa | BYU | 1 |
| Braylon Mullins | UConn | 17 |
| Jayden Quaintance | Kentucky | 20 |
| Alex Karaban | UConn | 36 |
| Tarris Reed Jr. | UConn | 42 |
| Richie Saunders | BYU | 56 |
| Malachi Moreno | Kentucky | 60 |
| Solo Ball | UConn | 68 |
| Otega Oweh | Kentucky | 93 |

Players not in ESPN's prospects list receive a neutral 1.00× draft premium.

---

## 10. Transfer Portal Sync

Scrapes On3 committed transfer portal data and updates roster assignments for tracked teams.

### 10.1 Dry Run First

```bash
cd python_engine && python sync_basketball_transfer_portal.py --dry-run --max-pages 2
```

### 10.2 Full Sync

```bash
cd python_engine && python sync_basketball_transfer_portal.py
```

### 10.3 Post-Sync Pipeline

After portal sync, update stats and valuations for affected teams:

```bash
cd python_engine
python enrich_bball_usage_rates.py
python calculate_bball_valuations.py
python apply_bball_overrides.py
```

### 10.4 Matching Behavior

Only matches players whose destination school exists in `basketball_teams`. Unmatched transfers are skipped — this is correct behavior. They will match automatically when their school is added to the system.

---

## 10.5 Transfer Portal Display

Run during active portal windows to refresh `basketball_portal_entries`:

```bash
cd python_engine && python sync_bball_portal_display.py --dry-run    # preview
cd python_engine && python sync_bball_portal_display.py              # sync
```

Clears and rebuilds the table on each run.

**Portal windows:**
- Spring: ~April 7–21 (post-tournament)
- Fall: ~November 8–18 (pre-season)

### Roster Changes (During Portal Windows)

Update `data/on3_basketballportal_raw.txt` by copy-pasting the full On3 portal page, then:

```bash
cd python_engine
python parse_bball_portal_txt.py --parse-only   # 1. verify parsing + school resolution
python parse_bball_portal_txt.py --dry-run       # 2. preview DB changes (A/B/C ops)
python parse_bball_portal_txt.py                 # 3. apply roster moves + departures + flags
python enrich_bball_portal_players.py            # 4. create records for new portal players
python calculate_bball_valuations.py             # 5. reprice all teams
python apply_bball_overrides.py                  # 6. reapply known deal values
python generate_bball_slugs.py                   # 7. slugs for new players
python scrape_bball_247_headshots.py             # 8. headshots for new recruits
```

Name mismatches between On3 and our DB are handled by `NAME_ALIASES` in `parse_bball_portal_txt.py`. School name variants are resolved via `SCHOOL_ALIASES` in the same file.

**Note:** `sync_bball_portal_display.py` still runs separately to keep the `/basketball/portal` display page current. `parse_bball_portal_txt.py` handles roster changes only.

**Frontend:** `/basketball/portal` — displays portal entries with status badges, team links, and CFO valuations.

**Migration:** `supabase/migrations/00015_basketball_portal_entries.sql` — must be run via Supabase dashboard before the sync script will work.

---

## 11. Slug Generation

Generates URL-safe slugs for all basketball teams and players.

```bash
cd python_engine && python generate_bball_slugs.py
```

Run after adding new players or teams. Collision handling: duplicate names receive a `-{team_slug}` suffix automatically (e.g., `john-smith` → `john-smith-byu`).

---

## 12. Frontend Routes

All basketball pages live under `/basketball/`:

| Route | Page | Data Source | Revalidate |
|-------|------|-------------|------------|
| `/basketball/players` | National leaderboard | `basketball_players` + `basketball_teams` join | 3600s |
| `/basketball/players/[slug]` | Player profile | `basketball_players` + `basketball_teams` + `basketball_nil_overrides` | 3600s |
| `/basketball/teams` | Team grid | `basketball_teams` | 3600s |
| `/basketball/teams/[slug]` | Team roster | `basketball_players` + `basketball_teams` | 3600s |
| `/basketball/portal` | Transfer portal tracker | `basketball_portal_entries` + `basketball_teams` | 300s |
| `/basketball/recruits` | HS recruit big board | `basketball_players` (player_tag='High School Recruit') + `basketball_teams` | 3600s |
| `/basketball/methodology` | Formula explanation | Static JSX | — |

No frontend changes are needed when adding a new team — all pages query `basketball_teams` and `basketball_players` dynamically.

---

## 13. Database Tables

| Table | Purpose |
|-------|---------|
| `basketball_teams` | One row per program (market_multiplier, estimated_nil_pool, logo, slug) |
| `basketball_players` | All players across all teams (stats, valuations, roster status) |
| `basketball_nil_overrides` | Known deal values (annualized_value is a generated column) |
| `basketball_player_events` | Audit log for valuation and status changes |
| `basketball_portal_entries` | Display-only portal tracker (rebuilt on each sync run) |

### 13.1 Quick DB Health Check

```bash
cd python_engine && python3 -c "
from supabase_client import supabase
for table in ['basketball_teams', 'basketball_players',
              'basketball_nil_overrides', 'basketball_player_events',
              'basketball_portal_entries']:
    r = supabase.table(table).select('*', count='exact').execute()
    print(f'{table}: {r.count} rows')
"
```

### 13.2 basketball_portal_entries Schema

Display-only table rebuilt on each `sync_bball_portal_display.py` run. Not permanent storage.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID, PK | Auto-generated |
| `player_name` | TEXT | |
| `position` | TEXT | |
| `origin_school` | TEXT | School transferring from |
| `destination_school` | TEXT | Committed destination (if any) |
| `origin_team_id` | UUID, FK | NULL if origin school not tracked |
| `destination_team_id` | UUID, FK | NULL if destination school not tracked |
| `status` | TEXT | committed, entered, withdrawn |
| `star_rating` | INTEGER | |
| `cfo_valuation` | INTEGER | CFO valuation if player exists in system |
| `on3_nil_value` | INTEGER | On3's NIL valuation |
| `headshot_url` | TEXT | |
| `entry_date` | DATE | When player entered portal |
| `commitment_date` | DATE | When player committed (if committed) |
| `on3_player_slug` | TEXT | For linking to On3 profiles |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

Migration: `supabase/migrations/00015_basketball_portal_entries.sql`

### 13.3 Schema Reference

Full column listing for core tables: `BASKETBALL_VALUATION_ENGINE.md` §5.

**Key migrations:**
- `supabase/migrations/00013_basketball_schema.sql` — initial schema
- `supabase/migrations/00014_basketball_teams_espn_id.sql` — ESPN ID column
- `supabase/migrations/00015_basketball_portal_entries.sql` — portal display table
- `supabase/migrations/00016_basketball_acquisition_type.sql` — acquisition type tracking
- `supabase/migrations/00017_basketball_override_source_url.sql` — `override_source_url TEXT` on `basketball_players` for source attribution

After applying a migration that adds a column, reload the PostgREST schema cache via **Supabase dashboard → Settings → API → Reload schema cache** (or run `NOTIFY pgrst, 'reload schema';` in the SQL editor) before pipeline scripts can use the new column.

---

## 14. Common Issues

### Player not found during social enrichment

Add name alias to `NAME_ALIASES` in `enrich_bball_social_data.py`. See §7.2.

### Slug collision on new player

Handled automatically by `generate_bball_slugs.py` with `-{team_slug}` suffix. No manual intervention needed.

### ESPN stats returning 404 for a player

Player has no college minutes yet (incoming freshman or redshirt). Expected behavior. They receive `usage_rate=0` and `role_tier` is not set — the formula applies the fixed incoming multiplier (0.60×). The recruiting CSV (§4) provides their talent modifier via star rating and composite score.

### Transfer portal sync matches 0 players

Check if destination school exists in `basketball_teams`. If not, seed the school first (§3), then re-run the portal sync.

### Valuation looks wrong after formula change

Check `is_override` flag first. Reported values bypass the formula entirely and must be updated manually in `basketball_approved_overrides.csv` (§6).

If it's a formula player, run with `--dry-run` and check each component:

```bash
cd python_engine && python calculate_bball_valuations.py --dry-run --team SLUG
```

The output shows position base, role tier, draft premium, talent modifier, and final valuation for each player.

### market_multiplier needs adjustment after reviewing outputs

Update directly in the `basketball_teams` table, then re-run valuations:

```bash
cd python_engine && python3 -c "
from supabase_client import supabase
supabase.table('basketball_teams') \
    .update({'market_multiplier': NEW_VALUE}) \
    .eq('slug', 'SLUG').execute()
print('Updated')
"
```

Then:

```bash
cd python_engine && python calculate_bball_valuations.py --team SLUG
cd python_engine && python apply_bball_overrides.py
```

### Override player accidentally recalculated by formula

The valuation engine skips `is_override=True` players. If a player's override was cleared incorrectly, re-run `apply_bball_overrides.py` to restore it from the CSV.

---

## 15. Script Reference

All basketball pipeline scripts in `python_engine/`:

| Script | Purpose | Flags |
|--------|---------|-------|
| `ingest_bball_espn_rosters.py` | ESPN roster → `basketball_players` (guards portal-managed players) | `--team SLUG` |
| `enrich_bball_usage_rates.py` | ESPN stats → usage_rate, role_tier, per | `--team SLUG` |
| `enrich_bball_class_years.py` | ESPN experience → class_year | (runs all teams) |
| `enrich_bball_star_ratings.py` | Per-team recruiting CSV → star_rating, composite | `--team SLUG` |
| `enrich_bball_social_data.py` | On3 social → follower counts | `--team SLUG`, `--dry-run` |
| `apply_bball_social_manual.py` | Manual CSV → social follower counts (players not on On3) | `--dry-run` |
| `calculate_bball_valuations.py` | Formula → cfo_valuation (paginated over basketball_players) | `--team SLUG`, `--dry-run` |
| `apply_bball_overrides.py` | CSV → override valuations + writes `override_source_url` when present | — |
| `generate_bball_slugs.py` | Name → URL slug | — |
| `fix_bball_headshots.py` | Validates ESPN CDN headshot URLs, NULLs broken ones | `--team SLUG` |
| `scrape_bball_247_headshots.py` | 247Sports → recruit headshot URLs | `--dry-run`, `--year YYYY` |
| `parse_raw_247_recruits.py` | Scrapes 247Sports composite rankings → recruit CSV + prints Python list | `--year 2026|2027|2028`, `--dry-run` |
| `build_bball_recruit_csvs.py` | Source of truth for HS recruits → national CSV files | `--year YYYY`, `--dry-run` |
| `ingest_bball_recruits.py` | National recruit CSVs → `basketball_players` | `--year YYYY`, `--dry-run` |
| `classify_bball_acquisition_types.py` | Tags players as retained/portal/recruit | `--dry-run` |
| `sync_nba_draft_projections.py` | ESPN draft API → nba_draft_projection + recalculate | `--dry-run`, `--season YYYY` |
| `enrich_bball_portal_players.py` | Creates DB records for portal players from untracked schools | `--dry-run` |
| `parse_bball_portal_txt.py` | Raw On3 txt → roster moves/departures/flags | `--parse-only`, `--dry-run` |
| `sync_bball_portal_display.py` | On3 portal → `basketball_portal_entries` (display) | `--dry-run` |
| `sync_bball_roster_from_portal.py` | Portal entries → roster moves/departures/flags | `--dry-run` |
| `sync_basketball_transfer_portal.py` | On3 portal → roster moves (legacy) | `--dry-run`, `--max-pages N` |
| `expand_to_basketball_universe.py` | Bulk team seeding from CSV (82-team expansion) | `--dry-run` |

### Data Files

| File | Purpose |
|------|---------|
| `data/basketball_approved_overrides.csv` | Known deal values |
| `data/nba_draft_projections_2025.csv` | NBA mock draft projections |
| `data/basketball_recruits_2026.csv` | National recruit CSV — committed 2026 class (259 recruits) |
| `data/basketball_recruits_2027.csv` | National recruit CSV — 4-star+ big board (210 recruits) |
| `data/basketball_recruits_2028.csv` | National recruit CSV — 4-star+ big board (81 recruits) |
| `data/raw_247_basketball_recruits_2026.txt` | Raw 247Sports paste (optional — parser scrapes live) |
| `data/raw_247_basketball_recruits_2027.txt` | Raw 247Sports paste (optional — parser scrapes live) |
| `data/raw_247_basketball_recruits_2028.txt` | Raw 247Sports paste (optional — parser scrapes live) |
| `data/{slug}_basketball_recruits_2025.csv` | Legacy per-team recruiting data (BYU, Kentucky) |
| `data/basketball_expansion_teams.csv` | Master CSV for 82-team universe (ESPN IDs, multipliers, conferences) |
| `data/on3_basketballportal_raw.txt` | Raw On3 portal copy-paste for `parse_bball_portal_txt.py` |
| `data/basketball_social_manual.csv` | Manual social follower counts for `apply_bball_social_manual.py` |

---

## 16. Rollback Procedures

### 16.1 Safe Fields to Recompute

These can be recovered from source data at any time:

| Field | Recovery |
|-------|----------|
| `cfo_valuation` | `calculate_bball_valuations.py` |
| `role_tier`, `usage_rate`, `ppg`, `rpg`, `apg`, `per` | `enrich_bball_usage_rates.py` |
| `class_year`, `experience_level` | `enrich_bball_class_years.py` |
| `star_rating`, `composite_score` | `enrich_bball_star_ratings.py` (requires CSV) |
| `slug` | `generate_bball_slugs.py` |

### 16.2 Dangerous Fields (Cannot Auto-Recover)

- `is_override` — must be manually verified against `basketball_approved_overrides.csv`
- `roster_status` — requires manual review or portal re-sync to reconstruct
- `team_id` — requires ESPN roster data to re-associate
- Deleted records — cannot be recovered (use soft delete via `roster_status` instead)

### 16.3 Nuclear Reset (Last Resort)

To wipe all valuations and recompute from scratch:

```bash
cd python_engine && python3 -c "
from supabase_client import supabase
supabase.table('basketball_players') \
    .update({'cfo_valuation': None}) \
    .eq('is_override', False) \
    .execute()
print('All formula valuations cleared')
"
```

Then rerun:

```bash
cd python_engine
python calculate_bball_valuations.py
python apply_bball_overrides.py
```
