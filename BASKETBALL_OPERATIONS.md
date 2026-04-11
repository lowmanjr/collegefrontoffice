# College Front Office — Basketball Operations Runbook

> **Last Updated:** April 10, 2026
> **Scope:** Men's college basketball NIL valuations
> **Current teams:** BYU, Kentucky (2 of 68 Power 4)
> **Companion docs:** `BASKETBALL_VALUATION_ENGINE.md` (formula detail), `OPERATIONS.md` (football pipeline reference)

---

## 1. Overview

The basketball product produces CFO Valuations for men's college basketball players across tracked Power 4 programs. Each player receives an integer dollar value representing their estimated annualized NIL market value, computed by a multiplicative formula with six components (position base, NBA draft premium, role tier, talent modifier, market multiplier, experience multiplier) plus an additive social premium.

The tech stack is identical to football: Next.js (App Router) on Vercel, Supabase (PostgreSQL), Python data pipeline. Basketball uses its own set of tables (`basketball_teams`, `basketball_players`, `basketball_nil_overrides`, `basketball_player_events`) and its own pipeline scripts (all prefixed `*_bball_*` or `*_basketball_*`).

The valuation engine is V1.1. See `BASKETBALL_VALUATION_ENGINE.md` for the full formula specification.

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

Expected output: BYU and Kentucky rows with their market multipliers (1.08 and 1.20 respectively).

---

## 3. Adding a New Team

Step-by-step for onboarding any new program. This is the most critical section — follow in exact order.

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

### 3.4 Run the Full Pipeline

Run in this exact order:

```bash
cd python_engine

# 1. Import roster from ESPN
python ingest_bball_espn_rosters.py --team SLUG

# 2. Enrich stats (MPG → role_tier, PER, ppg/rpg/apg)
python enrich_bball_usage_rates.py --team SLUG

# 3. Enrich class years from ESPN experience data (runs all teams)
python enrich_bball_class_years.py

# 4. Enrich star ratings from recruiting CSV (see §4)
#    Create data/{SLUG}_basketball_recruits_2025.csv FIRST
python enrich_bball_star_ratings.py --team SLUG

# 5. Compute valuations
python calculate_bball_valuations.py --team SLUG

# 6. Apply any known deals
python apply_bball_overrides.py

# 7. Generate URL slugs
python generate_bball_slugs.py
```

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

## 4. Recruiting CSV — Required for Incoming Players

Every new team needs a recruiting CSV for incoming players (freshmen and first-semester transfers with no ESPN stats).

### 4.1 File Location

```
python_engine/data/{team_slug}_basketball_recruits_2025.csv
```

### 4.2 Format

```csv
espn_athlete_id,player_name,star_rating,composite_score,position_247
5142718,AJ Dybantsa,5,0.9999,SF
5095153,Jasper Johnson,5,0.9958,SG
```

### 4.3 How to Identify Who Needs It

After running steps 1–2 of the pipeline (roster ingest + usage rate enrichment), query for players with no stats:

```bash
cd python_engine && python3 -c "
from supabase_client import supabase
team = supabase.table('basketball_teams') \
    .select('id').eq('slug', 'SLUG').single().execute()
players = supabase.table('basketball_players') \
    .select('name, position, espn_athlete_id, usage_rate, star_rating') \
    .eq('team_id', team.data['id']) \
    .eq('roster_status', 'active') \
    .execute()
incoming = [p for p in players.data if not p.get('usage_rate')]
print(f'{len(incoming)} players need recruiting CSV:')
for p in incoming:
    print(f'  {p[\"espn_athlete_id\"]} | {p[\"name\"]} | {p[\"position\"]} | stars: {p.get(\"star_rating\", \"?\")}')"
```

### 4.4 Data Source

247Sports basketball composite rankings (public). If scraping is unavailable, use manually verified public data. Mark composite scores as estimates with a `#` comment if unverified.

### 4.5 Existing CSVs

| File | Team |
|------|------|
| `byu_basketball_recruits_2025.csv` | BYU |
| `kentucky_basketball_recruits_2025.csv` | Kentucky |

---

## 5. Valuation Refresh (Existing Team)

Run when: stats update mid-season, class years change, new draft projections emerge, or social data needs refreshing.

### 5.1 Single Team

```bash
cd python_engine
python enrich_bball_usage_rates.py --team SLUG    # if stats updated
python enrich_bball_class_years.py                # if new season (runs all teams)
python calculate_bball_valuations.py --team SLUG  # always
python apply_bball_overrides.py                   # always
```

### 5.2 Full Refresh (All Teams)

```bash
cd python_engine
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

## 6. Managing Known Deal Values

When a reported NIL figure becomes public for a basketball player.

### 6.1 Confirm ESPN Athlete ID

```bash
cd python_engine && python3 -c "
from supabase_client import supabase
p = supabase.table('basketball_players') \
    .select('name, espn_athlete_id') \
    .ilike('name', '%PLAYER_NAME%').execute()
print(p.data)
"
```

### 6.2 Add to Overrides CSV

File: `python_engine/data/basketball_approved_overrides.csv`

Format:

```csv
espn_athlete_id,player_name,total_value,years,source_name,source_url
```

Example:

```csv
5142718,AJ Dybantsa,4400000,1,Reported — On3/multiple sources,$4-7M range reported
```

For multi-year deals, set `years` accordingly — the `annualized_value` column in `basketball_nil_overrides` is a generated column (`total_value / years`).

### 6.3 Apply

```bash
cd python_engine && python apply_bball_overrides.py
```

### 6.4 Verify

```bash
cd python_engine && python3 -c "
from supabase_client import supabase
p = supabase.table('basketball_players') \
    .select('name, cfo_valuation, is_override') \
    .ilike('name', '%PLAYER_NAME%').single().execute()
print(p.data)
"
```

### 6.5 Current Known Values (V1.1)

| Player | Team | Value | Source |
|--------|------|-------|--------|
| AJ Dybantsa | BYU | $4,400,000 | Multiple reported sources |
| Jayden Quaintance | Kentucky | $2,000,000 | Multiple reported sources |

---

## 7. Social Data Enrichment

Scrapes On3 team NIL pages for per-player social follower counts (Instagram, Twitter/X, TikTok).

### 7.1 Run

```bash
cd python_engine && python enrich_bball_social_data.py --team SLUG
# Full refresh (all teams):
cd python_engine && python enrich_bball_social_data.py
```

### 7.2 Name Alias Handling

On3 player names sometimes differ from ESPN names in the database. When a player isn't matched during enrichment, add an alias to the `NAME_ALIASES` dict in `enrich_bball_social_data.py`:

```python
NAME_ALIASES: dict[str, str] = {
    "rob wright": "robert wright",
    # add others as discovered
}
```

Keys are the On3 normalized name (lowercase, no suffixes). Values are the DB normalized name.

---

## 8. NBA Draft Projections

### 8.1 File

```
python_engine/data/nba_draft_projections_2025.csv
```

Format: `espn_athlete_id, player_name, projected_pick`

### 8.2 Update Process

Update the CSV when mock draft consensus shifts, then recalculate:

```bash
cd python_engine
python calculate_bball_valuations.py
python apply_bball_overrides.py
```

### 8.3 Current Projections

| Player | Team | Projected Pick |
|--------|------|---------------|
| Richie Saunders | BYU | 58 |
| Jayden Quaintance | Kentucky | 35 |

Players not in the CSV receive a neutral 1.00× draft premium.

---

## 9. Transfer Portal Sync

Scrapes On3 committed transfer portal data and updates roster assignments for tracked teams.

### 9.1 Dry Run First

```bash
cd python_engine && python sync_basketball_transfer_portal.py --dry-run --max-pages 2
```

### 9.2 Full Sync

```bash
cd python_engine && python sync_basketball_transfer_portal.py
```

### 9.3 Post-Sync Pipeline

After portal sync, update stats and valuations for affected teams:

```bash
cd python_engine
python enrich_bball_usage_rates.py
python calculate_bball_valuations.py
python apply_bball_overrides.py
```

### 9.4 Matching Behavior

Only matches players whose destination school exists in `basketball_teams`. Unmatched transfers are skipped — this is correct behavior. They will match automatically when their school is added to the system.

---

## 10. Slug Generation

Generates URL-safe slugs for all basketball teams and players.

```bash
cd python_engine && python generate_bball_slugs.py
```

Run after adding new players or teams. Collision handling: duplicate names receive a `-{team_slug}` suffix automatically (e.g., `john-smith` → `john-smith-byu`).

---

## 11. Frontend Routes

All basketball pages live under `/basketball/`:

| Route | Page | Data Source |
|-------|------|-------------|
| `/basketball/players` | National leaderboard | `basketball_players` + `basketball_teams` join |
| `/basketball/players/[slug]` | Player profile | `basketball_players` + `basketball_teams` + `basketball_nil_overrides` |
| `/basketball/teams` | Team grid | `basketball_teams` |
| `/basketball/teams/[slug]` | Team roster | `basketball_players` + `basketball_teams` |
| `/basketball/methodology` | Formula explanation | Static JSX |

No frontend changes are needed when adding a new team — all pages query `basketball_teams` and `basketball_players` dynamically.

---

## 12. Database Tables

| Table | Purpose |
|-------|---------|
| `basketball_teams` | One row per program (market_multiplier, estimated_nil_pool, logo, slug) |
| `basketball_players` | All players across all teams (stats, valuations, roster status) |
| `basketball_nil_overrides` | Known deal values (annualized_value is a generated column) |
| `basketball_player_events` | Audit log for valuation and status changes |

### 12.1 Quick DB Health Check

```bash
cd python_engine && python3 -c "
from supabase_client import supabase
for table in ['basketball_teams', 'basketball_players',
              'basketball_nil_overrides', 'basketball_player_events']:
    r = supabase.table(table).select('*', count='exact').execute()
    print(f'{table}: {r.count} rows')
"
```

### 12.2 Schema Reference

Full column listing: `BASKETBALL_VALUATION_ENGINE.md` §5.

Migration: `supabase/migrations/00013_basketball_schema.sql`.

---

## 13. Common Issues

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

## 14. Script Reference

All basketball pipeline scripts in `python_engine/`:

| Script | Purpose | Flags |
|--------|---------|-------|
| `ingest_bball_espn_rosters.py` | ESPN roster → `basketball_players` | `--team SLUG` |
| `enrich_bball_usage_rates.py` | ESPN stats → usage_rate, role_tier, per | `--team SLUG` |
| `enrich_bball_class_years.py` | ESPN experience → class_year | (runs all teams) |
| `enrich_bball_star_ratings.py` | Recruiting CSV → star_rating, composite | `--team SLUG` |
| `enrich_bball_social_data.py` | On3 social → follower counts | `--team SLUG`, `--dry-run` |
| `calculate_bball_valuations.py` | Formula → cfo_valuation | `--team SLUG`, `--dry-run` |
| `apply_bball_overrides.py` | CSV → override valuations | — |
| `generate_bball_slugs.py` | Name → URL slug | — |
| `sync_basketball_transfer_portal.py` | On3 portal → roster moves | `--dry-run`, `--max-pages N` |

### Data Files

| File | Purpose |
|------|---------|
| `data/basketball_approved_overrides.csv` | Known deal values |
| `data/nba_draft_projections_2025.csv` | NBA mock draft projections |
| `data/{slug}_basketball_recruits_2025.csv` | Incoming player recruiting data (per team) |

---

## 15. Rollback Procedures

### 15.1 Safe Fields to Recompute

These can be recovered from source data at any time:

| Field | Recovery |
|-------|----------|
| `cfo_valuation` | `calculate_bball_valuations.py` |
| `role_tier`, `usage_rate`, `ppg`, `rpg`, `apg`, `per` | `enrich_bball_usage_rates.py` |
| `class_year`, `experience_level` | `enrich_bball_class_years.py` |
| `star_rating`, `composite_score` | `enrich_bball_star_ratings.py` (requires CSV) |
| `slug` | `generate_bball_slugs.py` |

### 15.2 Dangerous Fields (Cannot Auto-Recover)

- `is_override` — must be manually verified against `basketball_approved_overrides.csv`
- `roster_status` — requires manual review or portal re-sync to reconstruct
- `team_id` — requires ESPN roster data to re-associate
- Deleted records — cannot be recovered (use soft delete via `roster_status` instead)

### 15.3 Nuclear Reset (Last Resort)

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
