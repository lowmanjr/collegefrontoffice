# CollegeFrontOffice.com — Master Architecture Document

## Current Status (April 2026)
- **68 Power 4 teams**, ~15,360 players, ~4,980 valued (includes 441 uncommitted HS recruits valued with 1.00x neutral market multiplier)
- **Valuation Engine V3.6b** — QB/DL base bumps, no-data talent penalty, star proxy widening, graduated starter multiplier, unattached-recruit pass (parity with basketball engine)
- **96 active overrides** across calibrated teams: Texas (9), Texas Tech (7), Georgia (49), Penn State (4), Kentucky (3), LSU (+Trey'Dez Green), Texas A&M (Mario Craver), plus original market-consensus + reported-deal overrides
- **EA Sports CFB 26 ratings** now cover all 68 Power 4 teams (expanded from 16). 4,674 ratings applied, 2,372 on-DC players with EA data (61.5% coverage)
- **Pipeline order**: ESPN rosters → On3 transfer portal → Ourlads depth charts → valuations
- ESPN sync runs first (base truth), On3 portal sync runs second (catches recent transfers ESPN missed)
- Transfer portal scraper: sync_transfer_portal.py (On3, paginated, 5,432 committed entries)
- **Transfer portal file (on3_portal_raw.txt) is the AUTHORITATIVE SOURCE for team assignments.** It overrides any ESPN or CFBD roster assignments. When a player appears in on3_portal_raw.txt with a destination school, that assignment wins — even if ESPN or CFBD still lists them at their origin school. Any audit, sync, or reassignment script must check on3_portal_raw.txt before moving a player.
- **Comparison CSV workflow**: paste On3 data → generate CSV → fill Override Value → ingest overrides. Active CSVs: texas_comparison.csv, texas_tech_comparison.csv, georgia_comparison.csv
- **OL→OT position mapping fix**: sync_ourlads_depth_charts.py now maps LT/RT → OT ($800K) instead of generic OL ($475K). 178 tackles corrected, $93.3M recovered.
- Methodology page cleaned (no EA Sports, no On3, no "verified" language)
- All UI pages use slug-based URLs, compact currency for team totals, full precision for player valuations

## 1. Project Overview
College Front Office is a data dashboard and valuation tool for the modern college sports economy. It aggregates player data across all 68 Power 4 programs (SEC, Big Ten, Big 12, ACC, and Notre Dame), calculates a proprietary "C.F.O. Valuation" for college athletes and elite HS recruits, and tracks team-level roster composition and estimated roster value.

## 2. Tech Stack
* **Frontend Framework:** Next.js (App Router)
* **Styling:** Tailwind CSS
* **UI Components:** shadcn/ui, recharts (for charts)
* **Database:** Supabase (PostgreSQL)
* **Hosting:** Vercel
* **Data Pipeline:** Python (pandas, requests, BeautifulSoup) → Supabase API (service role)
* **Testing:** Vitest (TypeScript, 586 tests), pytest (Python, 188 tests) — 774 total

## 3. Valuation Engine
**The canonical valuation engine specification lives in `VALUATION_ENGINE.md`. All valuation logic must conform to that document.**

The active engine is **V3.6b** (`python_engine/calculate_cfo_valuations.py`). All prior versions (V1–V3.4) are superseded.

### V3.6b Changes (April 2026)
- **Position base value recalibration:** QB $1.2M→$1.5M, DT/DL $500K→$600K. Other positions unchanged from V3.5.
- **Talent modifier no-data default:** 1.0x→0.70x when all three talent signals (production, EA, star) are missing.
- **Star proxy widened:** 5★ 1.15→1.30, 3★ 0.90→0.80, 1-2★ 0.80→0.65, no-data 1.0→0.70.
- **Graduated starter multiplier:** Non-#1 starters get graduated discount: rank 2=0.90x, rank 3=0.80x, rank 4=0.75x, rank 5=0.70x. Single-starter positions unchanged.
- **OL→OT position mapping fix:** sync_ourlads_depth_charts.py now maps LT/RT → OT ($800K base) instead of generic OL ($475K). 178 tackles corrected across 68 teams, $93.3M in recovered value.
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
| `name_utils.py` | Shared name normalization + 4-pass fuzzy matching (exact -> exact-stripped -> fuzzy -> fuzzy-stripped) |
| `enrich_star_ratings_247.py` | 247Sports fallback for star_rating/composite_score (classes 2022-2026, runs after enrich_star_ratings.py) |
| `generate_texas_comparison.py` | Generates CFO vs On3 comparison CSV for Texas with Override Value column |
| `diagnose_duplicates.py` | Comprehensive duplicate detection across all 68 teams with merge-before-delete logic |
| `fix_class_years.py` | Populates class_year NULLs via CFBD team+name matching (broader than update_class_years.py) |
| `backfill_acquisition_type.py` | Tags players as 'retained', 'portal', or 'recruit' using CFBD transfer portal data |
| `validate_valuations.py` | Post-valuation validation: 6 check categories (position config, sanity ceilings, rank inversions, data integrity incl. orphan check, distribution, override health). Run after every valuation recompute |
| `parse_on3_portal.py` | Parses On3 transfer portal raw text dump into structured CSV for portal comparison workflow |
| `audit_confusable_schools.py` | Audits 10 confusable school pairs (§5.18) for team misassignments. Cross-references CFBD + portal-verified exclusions via on3_portal_2026.csv. Fuzzy threshold 0.90 (raised from 0.80 after false-positive analysis). Read-only. |
| `audit_2026_recruits.py` | Cross-references python_engine/data/2026_recruits_raw.txt (247Sports composite feed) against DB. Flags misassignments, 4/5★ players missing from DB, stale DB entries, and name-variant pairs. Read-only. |

### Overrides
96 active overrides as of April 2026. Overrides bypass the algorithmic formula entirely (§2.0 of VALUATION_ENGINE.md). Managed via `python_engine/data/approved_overrides.csv` → `apply_overrides.py`, or directly via the comparison CSV workflow.

## 4. Tracked Teams (68 — All Power 4)
**SEC (16):** Alabama, Arkansas, Auburn, Florida, Georgia, Kentucky, LSU, Mississippi State, Missouri, Oklahoma, Ole Miss, South Carolina, Tennessee, Texas, Texas A&M, Vanderbilt
**Big Ten (18):** Illinois, Indiana, Iowa, Maryland, Michigan, Michigan State, Minnesota, Nebraska, Northwestern, Ohio State, Oregon, Penn State, Purdue, Rutgers, UCLA, USC, Washington, Wisconsin
**Big 12 (16):** Arizona, Arizona State, Baylor, BYU, Cincinnati, Colorado, Houston, Iowa State, Kansas, Kansas State, Oklahoma State, TCU, Texas Tech, UCF, Utah, West Virginia
**ACC (17):** Boston College, Cal, Clemson, Duke, Florida State, Georgia Tech, Louisville, Miami, NC State, North Carolina, Pittsburgh, SMU, Stanford, Syracuse, Virginia, Virginia Tech, Wake Forest
**Independent (1):** Notre Dame

### Market Multiplier Distribution (April 2026)

Source of truth is the `teams.market_multiplier` column. Query `supabase.table('teams').select('university_name, market_multiplier').order('market_multiplier', desc=True)` for a live view. Snapshot as of this doc:

| Multiplier | Count | Teams |
|-----------|-------|-------|
| **1.30** | 3 | Ohio State, Texas A&M, Texas Tech |
| **1.25** | 9 | Alabama, Georgia, Indiana, LSU, Miami, Michigan, Oregon, Texas, USC |
| **1.20** | 6 | Florida State, Houston, Notre Dame, Penn State, Tennessee, Vanderbilt |
| **1.15** | 5 | Arkansas, Clemson, Florida, Michigan State, Oklahoma |
| **1.10** | 7 | Auburn, Colorado, Iowa State, Kentucky, North Carolina, Ole Miss, South Carolina |
| **1.05** | 6 | Iowa, Missouri, Nebraska, UCLA, Washington, Wisconsin |
| **1.00** | 17 | Arizona State, BYU, Baylor, Georgia Tech, Illinois, Kansas State, Louisville, Maryland, Minnesota, Mississippi State, Oklahoma State, Pittsburgh, Stanford, TCU, Utah, Virginia Tech, West Virginia |
| **0.95** | 15 | Arizona, Boston College, Cal, Cincinnati, Duke, Kansas, NC State, Northwestern, Purdue, Rutgers, SMU, Syracuse, UCF, Virginia, Wake Forest |

Multipliers are clamped 0.80–1.30 in the engine (`market_multiplier()` in `calculate_cfo_valuations.py` §3.5). Recalibrated via multiple passes in April 2026 against external market data.

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
* `cfo_valuation` (INTEGER — computed by V3.6b engine; NULL for ineligible players)
* `is_override` (BOOLEAN — true if nil_overrides row replaces algorithm)
* `is_on_depth_chart` (BOOLEAN)
* `depth_chart_rank` (INTEGER — 1=starter, 2=backup, etc.)
* `roster_status` (TEXT — 'active', 'departed_draft', 'departed_transfer', 'departed_graduated', 'departed_other')
* `acquisition_type` (TEXT — 'retained', 'portal', 'recruit'; DEFAULT 'retained')
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
* Use `<RosterTabs>` from `components/RosterTabs.tsx` as the shared primitive for team page roster tabs (Full Roster / Portal / Recruits / Retained) with URL state via `?view=`; football composes it via `<TeamRoster>` (`components/TeamRoster.tsx`), basketball via `<BasketballTeamRoster>` (`components/BasketballTeamRoster.tsx`). Both sports ship the same 4 tabs in the same order.
* Use `<RosterDonut>` from `components/RosterDonut.tsx` for SVG donut chart showing roster value breakdown (dark/light variants).
* Use `<PortalBoard>` from `components/PortalBoard.tsx` for the /portal page player/team leaderboard with tabs, filters, search.
* Use `<ConferenceFilter>` from `components/ConferenceFilter.tsx` for conference pill buttons on both `/teams` and `/basketball/teams`; parameterized by a `conferences` prop (and optional `paramName`). Football passes `FOOTBALL_CONFERENCES` from `app/teams/page.tsx`; basketball passes `BASKETBALL_CONFERENCES` from `app/basketball/teams/page.tsx`.
* All valuation math must use `lib/valuation.ts` (TypeScript) or `calculate_cfo_valuations.py` (Python). Do not implement valuation logic inline.
* Routes use slugs, not UUIDs: `/players/[slug]` and `/teams/[slug]`.
* The `/futures` route has been renamed to `/recruits` with a permanent redirect.
* 2026 HS recruits are merged into team active rosters (post national signing day).
* 3-star 2026 recruits are tracked in the database (3,088 total recruits: 41 five-star, 437 four-star, 2,610 three-star) but only 4★/5★ receive valuations. 3-star recruits appear on team pages as incoming recruits with no dollar figure.
* Long snappers (LS) are excluded from algorithmic valuation — no meaningful NIL market exists. LS players with verified deals can still be valued via the override system.
* 2027/2028 commits do NOT appear on team pages.
* Team logos use ESPN CDN format: `https://a.espncdn.com/i/teamlogos/ncaa/500/{espn_id}.png`
* Player headshots use ESPN CDN: `https://a.espncdn.com/combiner/i?img=/i/headshots/college-football/players/full/{espn_id}.png&w=200&h=146`
* Recruit headshots come from 247Sports (scraped via `scrape_247_headshots.py`).
* All composite scores are on the 0-100 scale (not 0-1).
* **Never cite or reference On3 or 247Sports branding in any source fields, UI text, or user-facing content.** Internal scripts may reference these sources; end-user-visible text never does.
* Run `npm test` (Vitest) and `cd python_engine && python -m pytest tests/ -v` after valuation changes.

### UI Naming Conventions (enforce across all frontend changes)

Conventions apply to both football and basketball products unless explicitly flagged as sport-specific.

* **Player list pages** use column header **"Est. NIL Value"**. Never "CFO Valuation" in user-facing text.
* **Recruit list pages** use column header **"Proj. NIL Value"**.
* **Player profile hero** uses valuation heading **"Est. NIL Valuation"** for rostered players.
* **Recruit profile hero** uses valuation heading **"Projected NIL Valuation"**.
* **Portal team-view column** uses **"Acquired Value"**. Never "Est. Portal Value" or "Net Value".
* **Player profile `<title>` metadata** ends in **"| Projected NIL Valuation"** for High School Recruit tag, **"| Est. NIL Valuation"** otherwise. No "CFO" suffix in profile titles.
* **Page H1s** are sport-prefixed on sport-specific pages: "Top Football Player Valuations", "Basketball Team Valuations", "Football Transfer Portal Valuations", "Basketball Recruit Valuations", etc. Homepage and site-wide methodology-style pages are sport-agnostic.
* **Tab and filter buttons do NOT show counts in parentheses** — just the label. Applies to conference filters, roster tabs (Full Roster / Portal / Recruits / Retained), portal view toggles (By Player / By Team), and any filter pill row.
* **No rank "#" column** on portal player tables or portal team-view tables.
* **No table footers** with prospect counts or "X players" summaries.
* **Roster tabs** compose `<RosterTabs>` from `components/RosterTabs.tsx`. Football composes via `<TeamRoster>` (`components/TeamRoster.tsx`); basketball composes via `<BasketballTeamRoster>` (`components/BasketballTeamRoster.tsx`). Both ship the same 4 tabs in the same order: Full Roster / Portal / Recruits / Retained. Default tab (Full Roster) omits `?view=` from the URL; non-default tabs use `?view=portal`, `?view=recruits`, `?view=retained`. The `?view=` param name is load-bearing — bookmarked URLs depend on it.
* **Conference filter**: both sports use `<ConferenceFilter>` from `components/ConferenceFilter.tsx`, parameterized by a conferences list. The "All" pill is prepended internally; callers pass sport-specific entries only. Football passes `FOOTBALL_CONFERENCES` (SEC, Big Ten, Big 12, ACC, Independent) from `app/teams/page.tsx`; basketball passes `BASKETBALL_CONFERENCES` (SEC, Big Ten, Big 12, ACC, Big East, Other) from `app/basketball/teams/page.tsx`.
* **Search filters**: each sport has one reactive filter component serving both its `/players` and `/recruits` routes. Football uses `<SearchFilters>` from `components/SearchFilters.tsx`; basketball uses `<BasketballSearchFilters>` from `components/basketball/BasketballSearchFilters.tsx`. Mode detection via `usePathname()` (no mode prop). 350ms debounce on the search input. Query params `q` and `pos` are load-bearing — do not rename.
* **Override source attribution** renders via `<OverrideSourceLink>` from `components/OverrideSourceLink.tsx`. Football reads `nil_overrides.source_url` (via join); basketball reads `basketball_players.override_source_url`. Component renders "Source: hostname" with hostname parsed via `new URL(sourceUrl).hostname.replace(/^www\./, "")`. Raw `source_name` text is NOT rendered to users — the hostname link is the only user-facing attribution.
* **Dynamic OG images** ship for both sports' player profiles and team profiles (`app/players/[slug]/opengraph-image.tsx`, `app/teams/[slug]/opengraph-image.tsx`, `app/basketball/players/[slug]/opengraph-image.tsx`, `app/basketball/teams/[slug]/opengraph-image.tsx`). Homepage OG is shared and sport-agnostic (`app/opengraph-image.tsx`).
* **Sitemap** (`app/sitemap.ts`) includes both football and basketball static routes, team slugs, and public player slugs (paginated). Any new sport-specific route must be added here.
* **No external branding** in user-facing text: never mention On3, 247Sports, or EA Sports. Internal source fields may reference these; the UI only renders hostname via `<OverrideSourceLink>`.
* **No engine version numbers** (V3.x, V1.x) in user-facing strings. Internal docs and commit messages are fine.
* **No "verified" language** in user-facing copy. Use "reported" where the distinction matters in internal docs.
* **Currency formatting**: `formatCurrency` (full precision) for player-level values; `formatCompactCurrency` ($29.8M style) for team-level aggregates. Both from `lib/utils.ts`.

**Sport-specific differences (intentional):**

* **Position badge colors**: football uses `positionBadgeClass`; basketball uses `basketballPositionBadgeClass`. Both exported from `lib/ui-helpers.ts`.
* **Inline acquisition-type badges on team roster rows**: basketball's `<BasketballTeamRoster>` shows inline **Transfer** (blue), **In Portal** (amber), and **Recruit** (purple) badges on desktop rows in the Player column. Football's `<TeamRoster>` does NOT show these — acquisition context on football is conveyed by the active tab the user is on. Divergence is intentional.
* **`portal_evaluating` acquisition type**: basketball only. Players with this value appear on the Full Roster tab with the amber "In Portal" badge and are excluded from the Portal tab predicate, which matches `acquisition_type === "portal"` (incoming transfers) only.

**Known drift (flagged for future cleanup):**

* Football team OG image (`app/teams/[slug]/opengraph-image.tsx`) uses `formatCurrency` for the roster total. Basketball's equivalent uses `formatCompactCurrency` per the team-aggregate convention; football should be updated to match.

### Headshot Pipeline
* **`map_espn_athlete_ids.py` MUST run after any bulk portal sync or transfer window.** Portal transfer scripts write team_id but not `espn_athlete_id`; without backfill, headshot URLs are never generated.
* Pass 3 of `map_espn_athlete_ids.py` has **relaxed team verification for portal players**: accepts a name + position match from the ESPN search API regardless of the ESPN team nickname, because ESPN's roster API lags portal moves (a player's ESPN profile is still the correct person even if ESPN still shows the origin school). Safeguards: exact normalized name match, position match when ESPN provides one, skip ambiguous multi-result hits. Non-portal players retain strict team verification. See OPERATIONS.md §5.19.
* **Recruit headshots come from 247Sports** via `scrape_247_headshots.py --year {2026|2027|2028}`.
* **Broken ESPN URLs (HTTP 404) should be cleared before re-running the 247 scraper.** The scraper's "already has headshot" check treats non-NULL URLs as complete, so broken URLs block the fallback. Verify a suspicious URL with a quick HEAD/GET — body <6KB from the combiner endpoint is almost always the generic 404 page.

## 7. Page Structure

| Route | What It Shows | Data Source |
|-------|---------------|-------------|
| `/` (Homepage) | Hero search + route cards (Teams, Players, Recruits) | Static |
| `/players` (Big Board) | Top 100 college athletes by valuation | players + teams join |
| `/players/[slug]` (Player Profile) | Name, avatar, team, valuation; override contract details; recruit profile card | players + teams + nil_overrides |
| `/recruits` | 4/5★ HS recruits by star rating, filtered by class year | players + teams join |
| `/teams` (Team Index) | Programs ranked by Est. Roster Value, conference filter buttons (SEC, Big Ten, Big 12, ACC) | team_roster_summary view |
| `/teams/[slug]` (Team Detail) | Active roster + 2026 recruits merged, roster breakdown tabs (Full Roster, Portal, Recruits, Retained) with donut chart visualization | players + teams |
| `/portal` (Transfer Portal) | Portal acquisitions ranked by valuation with player and team leaderboard views, filterable by position and conference | players + teams join |
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

---

## 9. Basketball Product (Men's College Basketball NIL)

The basketball product is a parallel vertical to football with its own tables, pipeline scripts, and valuation engine. See `BASKETBALL_OPERATIONS.md` for the full runbook and `BASKETBALL_VALUATION_ENGINE.md` for formula details.

### 9.1 Current Status (April 2026)
- **82 teams** — All Power 4 conferences (SEC 16, Big Ten 18, Big 12 16, ACC 18), full Big East (11), plus Gonzaga (WCC), Memphis (AAC), San Diego State (MWC)
- **Valuation Engine V1.4** — multiplicative formula with position base, NBA draft premium, role tier, talent modifier, market multiplier, experience multiplier, plus additive social premium
- **~848 valued players** across the 82 teams
- **550 HS recruits** — 2026 (259), 2027 (210), 2028 (81); all 4★+ receive valuations and 247 headshots
- **27 overrides** — 10 market-anchored (sourced) + 17 editorial (unsourced recruits)
- **On3 org keys configured for 13 teams** — remaining 69 teams receive $0 social premium until keys added

### 9.2 Database Tables
- `basketball_teams` — 82 rows
- `basketball_players` — ~2,000 rows (varsity + recruits + portal players)
- `basketball_nil_overrides` — 27 rows (with `total_value`, `years`, `source_name`, `source_url`)
- `basketball_player_events` — audit log
- `basketball_portal_entries` — display-only portal tracker, rebuilt per sync

Key basketball-only player columns: `role_tier`, `rotation_rank`, `usage_rate`, `ppg`, `rpg`, `apg`, `per`, `nba_draft_projection`, `override_source_url` (NEW in migration 00017).

### 9.3 Key Basketball Scripts
- `calculate_bball_valuations.py` — V1.4 engine (paginated over `basketball_players` to handle 1,500+ row table)
- `apply_bball_overrides.py` — reads CSV, writes overrides + `override_source_url`
- `expand_to_basketball_universe.py` — bulk team seeding from `basketball_expansion_teams.csv`
- `parse_raw_247_recruits.py` — scrapes 247Sports composite rankings with `--year` flag
- `build_bball_recruit_csvs.py` — regenerates recruit CSVs from hardcoded Python lists
- `ingest_bball_espn_rosters.py` — ESPN roster → `basketball_players` (guards portal-managed players)
- `scrape_bball_247_headshots.py` — recruit headshot URLs from 247Sports
- `sync_nba_draft_projections.py` — ESPN draft API → `nba_draft_projection`

### 9.4 Frontend Routes
All basketball pages under `/basketball/`: `/players`, `/players/[slug]`, `/teams`, `/teams/[slug]`, `/portal`, `/recruits`, `/methodology`. Player profile pages render a "Source: hostname" link under the valuation when `override_source_url` is populated.

### 9.5 Migrations
- `00013_basketball_schema.sql` — initial schema
- `00014_basketball_teams_espn_id.sql` — ESPN ID column
- `00015_basketball_portal_entries.sql` — portal display table
- `00016_basketball_acquisition_type.sql` — acquisition type tracking
- `00017_basketball_override_source_url.sql` — source URL attribution

### 9.6 Pagination Warning
Supabase's PostgREST default row limit is 1,000. Basketball queries that fetch all players must paginate via `.range(offset, offset + PAGE_SIZE - 1)`. This bug was silently dropping ~500 players until caught during the 14→82 team expansion; the fix is applied in `calculate_bball_valuations.py`, `app/basketball/teams/page.tsx`, and `app/basketball/portal/page.tsx`.

### 9.7 Related Docs
- `BASKETBALL_OPERATIONS.md` — pipeline runbook
- `BASKETBALL_VALUATION_ENGINE.md` — V1.4 formula spec
- `BASKETBALL_CALIBRATION_V1.4.md` — CFO vs On3 calibration snapshot (roster players + recruits)
