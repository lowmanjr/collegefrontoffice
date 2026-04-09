# CollegeFrontOffice.com — Master Architecture Document

## 1. Project Overview
College Front Office is a data dashboard and valuation tool for the modern college sports economy. It aggregates player data across all 68 Power 4 programs (SEC, Big Ten, Big 12, ACC, and Notre Dame), calculates a proprietary "C.F.O. Valuation" for college athletes and elite HS recruits, and tracks team-level roster composition and estimated roster value.

## 2. Tech Stack
* **Frontend Framework:** Next.js (App Router)
* **Styling:** Tailwind CSS
* **UI Components:** shadcn/ui, recharts (for charts)
* **Database:** Supabase (PostgreSQL)
* **Hosting:** Vercel
* **Data Pipeline:** Python (pandas, requests, BeautifulSoup) → Supabase API (service role)
* **Testing:** Vitest (TypeScript, 134 tests), pytest (Python, 131 tests) — 265 total

## 3. Valuation Engine
**The canonical valuation engine specification lives in `VALUATION_ENGINE.md`. All valuation logic must conform to that document.**

The active engine is **V3.5** (`python_engine/calculate_cfo_valuations.py`). All prior versions (V1–V3.4) are superseded.

### V3.5 Changes (April 2026)
- **Position base value recalibration:** QB $850K→$1.2M, OT $550K→$800K, WR $400K→$550K, etc. All positions increased ~27% to match 2025-26 market data.
- **2028 HS experience fix:** Multiplier for 2028 juniors reduced from 0.70→0.35, 2029+ from 0.65→0.25. Fixes 4.6× On3 overvaluation for young QBs.
- **EA rating fallback in talent_modifier:** Priority chain: production_score → ea_rating → star_rating. EA OVR tiers: 90+→1.4, 82+→1.2, 75+→1.0, 68+→0.65, <68→0.4
- **Recruiting pedigree floor:** 5★ class ≤ 3 → depth chart multiplier floor of 1.0×. 4★ class ≤ 3 → floor of 0.45×.
- **TE is a 2-starter position** (changed from 1 in V3.4). TE2 gets 1.0× instead of 0.35×.
- **New column:** `players.ea_rating` (INTEGER) — EA Sports CFB 26 OVR rating

Two formula paths:
- **College Athlete Formula** — production/draft-based model with position-aware depth chart rank multiplier
- **High School Recruit Formula** — composite-score-based model for 4★ and 5★ HS recruits

Key algorithm files:
- `VALUATION_ENGINE.md` — canonical spec (internal, do not share publicly)
- `python_engine/calculate_cfo_valuations.py` — Python batch engine (both paths)
- `python_engine/supabase_client.py` — shared Supabase service-role client
- `lib/valuation.ts` — TypeScript mirror for server-side breakdown rendering

### Pipeline Scripts (python_engine/)
| Script | Purpose |
|--------|---------|
| `calculate_cfo_valuations.py` | Master valuation engine — runs all formulas |
| `calculate_production_scores.py` | Fetches CFBD season stats, computes 0-100 production scores |
| `populate_draft_projections.py` | Imports draft projections from CSV |
| `populate_hs_grad_year.py` | Populates hs_grad_year for HS recruits |
| `sync_depth_charts.py` | Scrapes OurLads depth charts, sets is_on_depth_chart |
| `sync_roster_status.py` | Flags departed players via CFBD transfer portal/roster data |
| `sync_ourlads_depth_charts.py` | Scrapes Ourlads depth charts, sets is_on_depth_chart + depth_chart_rank |
| `import_recruiting_class.py` | Imports HS recruiting classes from CFBD API or CSV |
| `identify_override_candidates.py` | Screens players for potential NIL override candidates |
| `apply_overrides.py` | Reads approved_overrides.csv, applies to nil_overrides table |
| `verify_override_urls.py` | HTTP-checks source URLs for nil_overrides |
| `ingest_espn_rosters.py` | Bulk imports ESPN roster data |
| `ingest_eada_finances.py` | Imports EADA financial data for teams |
| `flag_draft_eligible.py` | Scrapes Drafttek Big Board, flags draft-eligible players |
| `scrape_ea_ratings.py` | Scrapes EA Sports CFB 26 OVR ratings via Next.js API |
| `populate_ea_ratings.py` | Writes EA OVR ratings from CSV to players.ea_rating |
| `assign_default_depth_chart.py` | Assigns conservative DC rank to unvalued 4/5★ active players |
| `validate_ea_vs_production.py` | Comparison report: EA ratings vs CFBD production scores |
| `ingest_tennessee_transfers.py` | Imports missing transfer-in players from Ourlads (Tennessee-specific pattern) |
| `clean_duplicates.py` | Identifies and removes duplicate College Athlete records |
| `map_cfbd_ids.py` | Maps CFBD integer IDs to players via team-scoped fuzzy name matching |
| `enrich_star_ratings.py` | Enriches College Athletes with historical 247Sports star ratings |
| `enrich_class_years.py` | Enriches players with recruiting class_year from CFBD |
| `update_class_years.py` | Converts class_year to human-readable labels from CFBD roster data |
| `update_team_markets.py` | Sets conference and market_multiplier on teams table |
| `scrape_on3_valuations.py` | Pulls On3 NIL valuations for comparison/calibration |
| `scrape_on3_socials.py` | Pulls social follower counts from On3 rankings |
| `map_espn_athlete_ids.py` | Maps ESPN athlete IDs to players, generates headshot URLs from ESPN CDN |
| `scrape_247_headshots.py` | Scrapes 247Sports composite rankings for recruit headshot URLs |
| `scrape_247_ranks.py` | Scrapes 247Sports composite rankings to backfill national_rank |
| `generate_slugs.py` | Generates URL-safe slugs for all teams and players, handles duplicates |
| `snapshot_valuations.py` | Snapshots current valuations into valuation_history for sparkline data |
| `expand_to_power4.py` | Creates/updates all 68 Power 4 team records with conference, multiplier, logo, slug |
| `onboard_new_teams.py` | Master pipeline script — runs full onboarding sequence for new teams |
| `sync_espn_rosters_by_id.py` | Syncs rosters via ESPN athlete IDs — moves transfers, creates new players |
| `sync_on3_rosters.py` | Syncs rosters via On3 team NIL pages — catches transfers ESPN hasn't processed |
| `sync_transfer_portal.py` | Scrapes On3 committed transfer portal (5,400+ entries) for roster moves |
| `scrape_on3_team_socials.py` | Scrapes On3 team NIL pages for per-player social follower counts |
| `scrape_247_commitments.py` | Scrapes 247Sports for current HS recruit commitment data |
| `backfill_recruit_commitments.py` | Backfills team_id for HS recruits using CFBD committedTo field |

### Overrides
21 active overrides as of April 2026. Overrides bypass the algorithmic formula entirely. Managed via `python_engine/data/approved_overrides.csv` → `apply_overrides.py`.

## 4. Tracked Teams (68 — All Power 4)
**SEC (16):** Alabama, Arkansas, Auburn, Florida, Georgia, Kentucky, LSU, Mississippi State, Missouri, Oklahoma, Ole Miss, South Carolina, Tennessee, Texas, Texas A&M, Vanderbilt
**Big Ten (18):** Illinois, Indiana, Iowa, Maryland, Michigan, Michigan State, Minnesota, Nebraska, Northwestern, Ohio State, Oregon, Penn State, Purdue, Rutgers, UCLA, USC, Washington, Wisconsin
**Big 12 (16):** Arizona, Arizona State, Baylor, BYU, Cincinnati, Colorado, Houston, Iowa State, Kansas, Kansas State, Oklahoma State, TCU, Texas Tech, UCF, Utah, West Virginia
**ACC (17):** Boston College, Cal, Clemson, Duke, Florida State, Georgia Tech, Louisville, Miami, NC State, North Carolina, Pittsburgh, SMU, Stanford, Syracuse, Virginia, Virginia Tech, Wake Forest
**Independent (1):** Notre Dame

## 5. Data Architecture

### Table: `players`
* `id` (UUID, PK)
* `name` (TEXT, NOT NULL)
* `position` (TEXT)
* `star_rating` (INTEGER: 1–5)
* `class_year` (TEXT: 1=FR…5=5Y for college; stored as integer)
* `experience_level` (TEXT: "High School", "Active Roster", "Portal")
* `player_tag` (TEXT: "College Athlete" | "High School Recruit")
* `composite_score` (NUMERIC — 247Sports composite, 0–100 scale)
* `cfo_valuation` (INTEGER — computed by V3.5 engine)
* `is_override` (BOOLEAN — true if nil_overrides row replaces algorithm)
* `is_on_depth_chart` (BOOLEAN)
* `depth_chart_rank` (INTEGER — 1=starter, 2=backup, etc.)
* `roster_status` (TEXT — 'active', 'departed_draft', 'departed_transfer', 'departed_graduated', 'departed_other')
* `is_public` (BOOLEAN)
* `nfl_draft_projection` (INTEGER — pick 1–260, sentinel ≥500 or 0 = no data)
* `production_score` (NUMERIC — 0–100 from CFBD stats)
* `hs_grad_year` (INTEGER — 2026, 2027, 2028 for HS recruits)
* `total_followers`, `ig_followers`, `x_followers`, `tiktok_followers` (INTEGER)
* `ea_rating` (INTEGER — EA Sports CFB 26 OVR rating, 0–99)
* `cfbd_id` (INTEGER — CollegeFootballData player ID)
* `espn_athlete_id` (INTEGER — ESPN athlete ID for headshot CDN)
* `headshot_url` (TEXT — ESPN CDN or 247Sports headshot URL)
* `slug` (TEXT, UNIQUE — URL-safe slug, e.g. "gunner-stockton")
* `team_id` (UUID, FK → teams)
* `last_updated`, `created_at` (TIMESTAMPTZ)

### Table: `teams`
* `id` (UUID, PK)
* `university_name`, `conference`, `logo_url`
* `slug` (TEXT, UNIQUE — URL-safe slug, e.g. "georgia")
* `estimated_cap_space` (INTEGER — defaults to $20,500,000)
* `active_payroll` (INTEGER)
* `market_multiplier` (NUMERIC — 0.8 to 1.3)

### Table: `nil_overrides`
* `player_id` (UUID, FK → players)
* `name` (TEXT)
* `total_value` (INTEGER)
* `years` (NUMERIC)
* `annualized_value` (INTEGER — generated column: total_value / years)
* `source_name` (TEXT)
* `source_url` (TEXT — verified URL or NULL)

### Table: `valuation_history`
* `id` (UUID, PK)
* `player_id` (UUID, FK → players)
* `valuation` (INTEGER)
* `snapshot_date` (DATE)
* UNIQUE(player_id, snapshot_date)

### View: `team_roster_summary`
Aggregates active college athletes + 2026 incoming recruits per team. Excludes departed players and future (2027/2028) recruits.

## 6. Coding Guidelines for Claude
* Always use TypeScript for Next.js components.
* Default to server components unless interactivity (useState, onClick) is required.
* Do not invent data; rely on the schema provided.
* Keep components modular (e.g., separate the `PlayerTable` from the `CapSpaceBar`).
* Import `formatCurrency` from `lib/utils.ts` for player-level values (full precision).
* Import `formatCompactCurrency` from `lib/utils.ts` for team-level aggregates (e.g. "$29.8M").
* Import `positionBadgeClass` from `lib/ui-helpers.ts` for position badge color coding.
* Import `BASE_URL` from `lib/constants.ts` for canonical URLs and structured data.
* Use `<PlayerAvatar>` from `components/PlayerAvatar.tsx` for player headshots with initials fallback.
* All valuation math must use `lib/valuation.ts` (TypeScript) or `calculate_cfo_valuations.py` (Python). Do not implement valuation logic inline.
* Routes use slugs, not UUIDs: `/players/[slug]` and `/teams/[slug]`.
* The `/futures` route has been renamed to `/recruits` with a permanent redirect.
* 2026 HS recruits are merged into team active rosters (post national signing day).
* 2027/2028 commits do NOT appear on team pages.
* Team logos use ESPN CDN format: `https://a.espncdn.com/i/teamlogos/ncaa/500/{espn_id}.png`
* Player headshots use ESPN CDN: `https://a.espncdn.com/combiner/i?img=/i/headshots/college-football/players/full/{espn_id}.png&w=200&h=146`
* Recruit headshots come from 247Sports (scraped via `scrape_247_headshots.py`).
* All composite scores are on the 0-100 scale (not 0-1).
* Do not display "247Sports" branding on player-facing pages.
* Run `npm test` (Vitest) and `cd python_engine && python -m pytest tests/ -v` after valuation changes.

## 7. Page Structure

| Route | What It Shows | Data Source |
|-------|---------------|-------------|
| `/` (Homepage) | Hero search + route cards (Teams, Players, Recruits) | Static |
| `/players` (Big Board) | Top 100 college athletes by valuation | players + teams join |
| `/players/[slug]` (Player Profile) | Name, avatar, team, valuation; override contract details; recruit profile card | players + teams + nil_overrides |
| `/recruits` | 4/5★ HS recruits by composite score, filtered by class year | players + teams join |
| `/teams` (Team Index) | Programs ranked by Est. Roster Value | team_roster_summary view |
| `/teams/[slug]` (Team Detail) | Active roster + 2026 recruits merged, sorted by valuation | players + teams |
| `/methodology` | Static content explaining valuation approach | Static JSX |

## 8. SEO

* All pages have canonical URLs via `alternates.canonical` (using `BASE_URL` from `lib/constants.ts`).
* Dynamic sitemap at `/sitemap.xml` includes all teams and all public players (paginated).
* JSON-LD structured data: Person (player profiles), SportsTeam (team profiles), ItemList (index pages).
* Dynamic OG images for player profiles and team profiles.
* Static OG image for homepage.
* Apple touch icon and web manifest at `/apple-icon` and `/manifest.webmanifest`.
* `robots.txt` blocks `/admin`, `/login`, `/auth`.
* Permanent redirect: `/futures` → `/recruits`.
