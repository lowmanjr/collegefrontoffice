# CFO Basketball Valuation Engine — Internal Technical Specification

> **Status:** Canonical (V1.4) | **Last Updated:** April 15, 2026
> **Audience:** Developers, Claude Code sessions, internal team only
> **⚠️ PROPRIETARY — Do not share externally or commit to a public repo.**

---

## 1. Overview

The CFO Basketball Valuation Engine produces a single integer dollar value (`cfo_valuation`) for every active college basketball player in the system. This value represents College Front Office's proprietary estimate of a player's annualized NIL market value.

It is a companion to the CFO Football Valuation Engine (V3.6b) and shares the same architectural philosophy: a multiplicative formula built from independently calibrated components.

Basketball valuations differ from football in three fundamental ways:

1. **Role economics replace depth chart economics.** With only 5 starters and 13 scholarship players, a player's minutes share drives more of the spread than their position. The role tier multiplier (0.30×–2.20×) produces the widest spread of any single component.

2. **NBA draft premium is steeper.** The gap between a lottery pick and an undrafted player is larger than the equivalent NFL gap, and the one-and-done dynamic concentrates extreme value at the top.

3. **Incoming players use a recruiting path.** Players with no college minutes are valued on composite score and draft projection rather than production, with a fixed 0.60× role multiplier that sits between rotation and bench.

The engine runs as a Python batch job (`calculate_bball_valuations.py`) that reads player data from Supabase, computes valuations, and writes results back. It uses the **service role key** and bypasses RLS.

---

## 2. Master Formula

### 2.1 Combined Premium (V1.3)

Draft premium and role tier both measure player importance — one from NBA scouts, one from minutes. When draft data exists, we use whichever signal is stronger. When no draft data exists, role tier applies alone. The neutral 1.00× draft baseline is the absence of data, not a signal.

```
For players WITH an NBA draft projection (draft_premium > 1.0):
    combined_premium = max(nba_draft_premium, role_tier_multiplier)

For players WITHOUT a draft projection:
    combined_premium = role_tier_multiplier

basketball_value = position_base(position)
                 × combined_premium
                 × talent_modifier(per or composite_score)
                 × market_multiplier(team.market_multiplier)
                 × experience_multiplier(class_year)

social_premium = tiered_social_bonus(ig, x, tiktok)

cfo_valuation = max(int(basketball_value + social_premium), 5_000)
```

A player is classified as "incoming" when `usage_rate` is NULL or 0. Incoming players without a draft projection use the fixed 0.60× role tier. Incoming players WITH a draft projection use the draft premium directly (it will always be higher than 0.60×).

### 2.3 Eligibility Gate

Not every rostered player participates in the NIL market. The formula only runs for players who clear at least one criterion:

**Players with college stats (usage_rate > 0):**
- Minutes per game ≥ 8.0

**Incoming players (no college minutes):**
- 247Sports star rating ≥ 4

Players below these thresholds appear on team roster pages without a dollar figure. Team totals reflect only valued players.

Current gate results (V1.4, 82 teams):
- 848 valued players across 82 teams
- Players below thresholds appear on roster pages without a dollar figure

---

## 3. Component Specifications

### 3.1 Position Base

Sets the economic floor by position. Basketball position bases are intentionally flatter than football — a center and a point guard are within 55% of each other, vs a QB and a kicker being 12× apart in football.

| Position | Base Value | Notes |
|----------|-----------|-------|
| PG | $700,000 | Calibrated to Power 4 floor |
| SG | $600,000 | |
| SF | $550,000 | |
| PF | $500,000 | |
| C  | $450,000 | |
| G (generic) | $600,000 | ESPN fallback |
| F (generic) | $550,000 | ESPN fallback |

Bases are calibrated to the Power 4 market floor. Mid-major and lower programs scale down via market_multiplier (0.30–0.75). The prior bases ($225K–$350K) were recalibrated in V1.1 after stress-testing against Opendorse market data and publicly reported deal anchors.

**Source:** ESPN provides G/F/C generics via their roster API. Granular positions (PG/SG/SF/PF/C) come from On3 recruiting data and are enriched via CSV for incoming players.

**Implementation:** `get_position_base()` in `calculate_bball_valuations.py`, mirrored in `getBasketballPositionBase()` in `lib/valuation.ts`.

---

### 3.2 NBA Draft Premium

Amplifies value for players with known NBA draft projections. The curve is steeper than the NFL equivalent because NBA lottery contracts are 4-year guaranteed deals worth $10M+/year for top picks, creating a much wider gap between lottery and second-round selections.

| Projected Pick | Premium | Tier Label |
|---------------|---------|------------|
| 1–5 | 3.50× | Consensus lottery |
| 6–14 | 2.60× | Lottery |
| 15–30 | 1.80× | Late first round |
| 31–60 | 1.25× | Second round |
| Undrafted / not projected | 1.00× | Baseline (neutral) |

Draft projections are maintained in `python_engine/data/nba_draft_projections_2025.csv` (columns: `espn_athlete_id, player_name, projected_pick`). Only players with known projections appear in the file — all others receive 1.00×. The file is updated manually as mock draft consensus shifts throughout the season.

**Implementation:** `get_nba_draft_premium()` in `calculate_bball_valuations.py`, mirrored in `getNbaDraftPremium()` in `lib/valuation.ts`.

---

### 3.3 Role Tier Multiplier

The largest spread driver for players without a draft projection. Role tier is derived from minutes per game (MPG), which is used as a transparent, auditable proxy for usage rate. MPG is stored as `usage_rate = MPG / 40.0` for formula compatibility.

#### MPG Thresholds → Role Tier

| MPG | Role Tier | Multiplier | Typical Player |
|-----|-----------|-----------|----------------|
| ≥ 30 | franchise | 2.20× | Primary scorer / floor general |
| 24–29 | star | 1.65× | Core starter, heavy minutes |
| 16–23 | starter | 1.20× | Full-time starter or high-usage sixth man |
| 8–15 | rotation | 0.75× | Regular rotation player |
| < 8 | bench | 0.30× | Spot minutes / walk-on |
| No stats | incoming | 0.60× | Freshmen and new transfers |

**Sixth man handling:** A player who comes off the bench but logs 20+ MPG correctly slots into "starter" tier (1.20×). The formula does not penalize rotation status — only minutes determine tier.

**Incoming multiplier rationale:** The fixed 0.60× sits between rotation (0.75×) and bench (0.30×). This is intentional: a high-ranked incoming player should be valued above a low-minutes veteran, with differentiation provided by draft premium and composite score. A 5-star lottery pick arriving on campus is not a bench player — the draft premium (3.50×) and talent modifier (1.30×) carry the signal.

**Source:** `enrich_bball_usage_rates.py` fetches season stats from ESPN Core Stats API, computes MPG, and assigns `role_tier`, `rotation_rank`, and `rotation_status`.

**Implementation:** `get_role_tier_multiplier()` in `calculate_bball_valuations.py`, mirrored in `getRoleTierMultiplier()` in `lib/valuation.ts`.

---

### 3.4 Talent Modifier

Measures individual talent above or below the average college player. The signal source depends on whether a player has college stats.

#### For players WITH stats: PER-based

NCAA average PER ≈ 15.0. Tiers are calibrated around this baseline.

| PER | Modifier | Label |
|-----|---------|-------|
| ≥ 25 | 1.30× | Elite |
| 20–24 | 1.20× | Strong |
| 15–19 | 1.10× | Above average |
| 10–14 | 1.00× | Average (neutral) |
| < 10 | 0.90× | Below average |

PER is fetched from ESPN Core Stats API: `sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball/seasons/{year}/types/2/athletes/{id}/statistics` → `splits.categories[general].stats[PER].value`.

#### For INCOMING players: composite score-based

| 247Sports Composite | Stars | Modifier |
|--------------------|-------|---------|
| ≥ 0.9900 | 5★ | 1.30× |
| 0.8900–0.9899 | 4★ | 1.15× |
| ≤ 0.8899 (with 3★+ rating) | 3★ | 1.00× |
| < 0.7900 or unranked | ≤ 2★ | 0.85× |

Composite scores are maintained in `python_engine/data/{team}_basketball_recruits_{year}.csv` (columns: `espn_athlete_id, player_name, star_rating, composite_score, position_247`).

**Implementation:** `get_talent_modifier()` in `calculate_bball_valuations.py`, mirrored in `getBasketballTalentModifier()` in `lib/valuation.ts`.

---

### 3.5 Market Multiplier

School-level multiplier reflecting the NIL market power of a program's brand, fanbase size, media market, and conference visibility. Set per team in `basketball_teams.market_multiplier`. Clamped to **[0.80, 1.30]**.

Basketball market multipliers are calibrated **independently** from football. Duke basketball (1.30) ≠ Duke football (1.05). BYU basketball is currently set at 1.08 — Big 12 visibility with strong LDS fanbase reach.

#### Calibration Guide (for new teams)

| Program tier | Range | Examples |
|---|---|---|
| Blue blood | 1.25–1.35 | Duke, Kentucky, Kansas, UNC, UCLA |
| Elite Power 4 | 1.15–1.24 | Gonzaga, Houston, Villanova |
| Strong Power 4 | 1.05–1.14 | BYU (1.08), Iowa State, Arkansas |
| Mid-major (A-10, MWC, WCC) | 0.55–0.75 | — |
| Lower D1 | 0.30–0.50 | — |

**Implementation:** `get_market_multiplier()` in `calculate_bball_valuations.py`.

---

### 3.6 Experience Multiplier

Reflects increased NIL earning power as a player builds name recognition, marketing history, and on-court track record over their college career.

| Class Year | Multiplier |
|-----------|-----------|
| Freshman | 0.85× |
| Sophomore | 0.95× |
| Junior | 1.05× |
| Senior | 1.10× |
| Graduate | 1.15× |
| Unknown | 0.90× (conservative default) |

**Source:** ESPN roster API `experience.displayValue` field, captured during class year enrichment (`enrich_bball_class_years.py`).

**Implementation:** `get_experience_multiplier()` in `calculate_bball_valuations.py`, mirrored in `getBasketballExperienceMultiplier()` in `lib/valuation.ts`.

---

### 3.7 Social Premium

Flat dollar bonus added **after** the multiplicative formula. Applied to all players regardless of formula output. TikTok is weighted 1.2× vs Instagram's 1.0× and Twitter/X's 0.7× — basketball players skew younger and TikTok reach converts to NIL deals at a higher rate.

```
weighted_followers = ig + (x × 0.7) + (tiktok × 1.2)
```

| Weighted Followers | Social Premium |
|-------------------|---------------|
| ≥ 1,000,000 | $150,000 |
| ≥ 500,000 | $75,000 |
| ≥ 100,000 | $25,000 |
| ≥ 50,000 | $10,000 |
| ≥ 10,000 | $3,000 |
| < 10,000 | $0 |

**Current state:** Social data is enriched via `enrich_bball_social_data.py` (On3 scraping) and `apply_bball_social_manual.py` (manual CSV for players not covered by On3). As of the 82-team expansion, On3 org keys exist for 13 teams only — the remaining 69 teams have $0 social premium until their org keys are added. The social premium is additive and does not affect the base multiplicative formula.

**Implementation:** `calculate_social_premium()` in `calculate_bball_valuations.py`.

---

## 4. Valuation Floor

All valuations are subject to a **$5,000 minimum** regardless of formula output. Walk-ons and deep bench players with no recruiting profile receive this floor. The basketball floor ($5K) is lower than football ($10K) because basketball rosters are smaller and low-end values are naturally compressed.

---

## 5. Database Schema

### Tables

| Table | Purpose |
|-------|---------|
| `basketball_teams` | Team metadata, market_multiplier, estimated_nil_pool |
| `basketball_players` | Player data, valuations, stats, roster status |
| `basketball_nil_overrides` | Reported NIL deal data (annualized_value is generated column) |
| `basketball_player_events` | Audit log for valuation and status changes |

### Key Columns (basketball_players)

| Column | Type | Source |
|--------|------|--------|
| `cfo_valuation` | INTEGER | Computed by engine or market data |
| `is_override` | BOOLEAN | TRUE if reported deal replaces formula |
| `role_tier` | TEXT | franchise/star/starter/rotation/bench |
| `rotation_rank` | INTEGER | 1 = most minutes, descending |
| `rotation_status` | TEXT | starter/rotation/bench |
| `usage_rate` | NUMERIC | MPG / 40.0 (0.0–1.0) |
| `ppg, rpg, apg, per` | NUMERIC | ESPN Core Stats API |
| `nba_draft_projection` | INTEGER | Pick 1–60, NULL if not projected |
| `star_rating` | INTEGER | 247Sports composite (1–5) |
| `composite_score` | NUMERIC | 247Sports composite (0.0–1.0) |
| `class_year` | TEXT | Freshman/Sophomore/Junior/Senior/Graduate |
| `experience_level` | TEXT | Same as class_year (ESPN source) |

Schema migration: `supabase/migrations/00013_basketball_schema.sql`

---

## 6. Pipeline Execution Order

### New Team Onboarding

```
1. ingest_bball_espn_rosters.py --team {slug}      # ESPN roster → basketball_players
2. enrich_bball_usage_rates.py --team {slug}        # ESPN stats → usage_rate, role_tier, ppg/rpg/apg/per
3. enrich_bball_class_years.py                      # ESPN experience → class_year, experience_level
4. enrich_bball_star_ratings.py                     # CSV → star_rating, composite_score, position
5. calculate_bball_valuations.py --team {slug}      # Formula → cfo_valuation
6. generate_bball_slugs.py                          # Name → URL slug
```

### Valuation Refresh (existing team)

```
1. enrich_bball_usage_rates.py --team {slug}        # Updated stats
2. calculate_bball_valuations.py --team {slug}      # Recalculate
```

### Transfer Portal Sync

```
1. sync_basketball_transfer_portal.py               # On3 committed transfers → roster moves
2. enrich_bball_usage_rates.py                      # Stats for new players
3. calculate_bball_valuations.py                    # Recalculate affected teams
```

---

## 7. Known Limitations (V1.4)

1. **ESPN position granularity.** ESPN provides G/F/C only. Granular positions (PG/SG/SF/PF/C) are corrected for incoming players via recruiting CSV but not yet for all returning players.

2. **Usage rate is MPG-based, not true usage%.** True usage rate (`(FGA + 0.44×FTA + TOV) / team_possessions × minutes_share`) requires possession-level data. MPG/40 is used as a transparent, auditable proxy. The column is named `usage_rate` for formula compatibility if upgraded later.

3. **Blue-chip recruits projected as top-3 NBA picks represent anomalies the formula is not designed to capture.** These players are valued using market information rather than the standard formula.

4. **No team_roster_summary view.** Basketball team aggregates are computed inline on the frontend. A materialized view will be created when team count grows further.

5. **Social data coverage is partial.** On3 org keys are configured for 13 of 82 teams (BYU, Duke, Florida, Georgia, Kansas, Kentucky, Louisville, Miami, Michigan, Oregon, Providence, San Diego State, Tennessee). The remaining 69 teams receive $0 social premium. This is non-blocking — social premium is additive and valuations are valid without it. On3 org keys for additional teams should be added to `ON3_ORG_KEYS` in `enrich_bball_social_data.py` as they are discovered.

---

## 8. Calibration Reference

### Team Totals (V1.4, April 2026 — 82 teams)

| Team | Conference | Market Mult. | Valued Players | Est. Roster Value |
|------|-----------|-------------|----------------|-------------------|
| BYU | Big 12 | 1.08 | 14 | $14,713,451 |
| Michigan | Big Ten | 1.18 | 14 | $14,321,456 |
| Louisville | ACC | 1.10 | 14 | $14,242,974 |
| Florida | SEC | 1.20 | 9 | $12,317,115 |
| Kansas | Big 12 | 1.28 | 14 | $12,059,222 |
| North Carolina | ACC | 1.28 | 9 | $11,938,576 |
| Oregon | Big Ten | 1.22 | 13 | $11,490,171 |
| UConn | Big East | 1.28 | 11 | $11,366,455 |
| Miami | ACC | 1.12 | 12 | $10,928,990 |
| Duke | ACC | 1.30 | 11 | $10,846,923 |
| Providence | Big East | 0.95 | 13 | $10,629,181 |
| Auburn | SEC | 1.16 | 10 | $10,574,586 |
| Alabama | SEC | 1.14 | 12 | $10,403,463 |
| Tennessee | SEC | 1.24 | 10 | $10,392,517 |
| Kentucky | SEC | 1.20 | 12 | $10,382,848 |
| Gonzaga | WCC | 1.14 | 10 | $10,207,600 |
| Ohio State | Big Ten | 1.10 | 11 | $10,030,513 |
| UCLA | Big Ten | 1.24 | 10 | $9,915,102 |
| Maryland | Big Ten | 1.04 | 12 | $9,861,761 |
| LSU | SEC | 1.04 | 10 | $9,759,698 |
| USC | Big Ten | 1.08 | 12 | $9,720,243 |
| Houston | Big 12 | 1.20 | 10 | $9,702,585 |
| Arizona | Big 12 | 1.18 | 8 | $9,621,409 |
| Arkansas | SEC | 1.10 | 8 | $9,564,885 |
| Iowa State | Big 12 | 1.08 | 9 | $9,527,584 |
| Illinois | Big Ten | 1.08 | 8 | $9,436,216 |
| Baylor | Big 12 | 1.12 | 8 | $9,260,076 |
| Indiana | Big Ten | 1.16 | 9 | $9,234,902 |
| Creighton | Big East | 1.02 | 12 | $9,033,692 |
| Missouri | SEC | 0.92 | 12 | $8,954,268 |
| Cincinnati | Big 12 | 1.00 | 12 | $8,773,200 |
| Michigan State | Big Ten | 1.20 | 9 | $8,732,340 |
| Villanova | Big East | 1.10 | 9 | $8,549,145 |
| Memphis | AAC | 0.96 | 13 | $8,523,612 |
| Texas Tech | Big 12 | 1.02 | 9 | $8,488,057 |
| Oklahoma | SEC | 1.00 | 10 | $8,403,937 |
| Iowa | Big Ten | 1.04 | 10 | $8,380,710 |
| Butler | Big East | 0.88 | 12 | $8,249,109 |
| Oklahoma State | Big 12 | 0.88 | 13 | $8,242,938 |
| Washington | Big Ten | 0.88 | 13 | $8,196,210 |
| Texas | SEC | 1.18 | 9 | $8,188,020 |
| Minnesota | Big Ten | 0.88 | 9 | $8,104,536 |
| Syracuse | ACC | 1.04 | 9 | $7,963,488 |
| Georgetown | Big East | 0.90 | 11 | $7,883,167 |
| Kansas State | Big 12 | 0.90 | 11 | $7,864,559 |
| Texas A&M | SEC | 1.06 | 11 | $7,798,234 |
| Purdue | Big Ten | 1.14 | 9 | $7,712,694 |
| Wisconsin | Big Ten | 1.00 | 8 | $7,711,200 |
| Cal | ACC | 0.84 | 10 | $7,694,715 |
| Georgia | SEC | 1.06 | 10 | $7,690,864 |
| Marquette | Big East | 1.06 | 9 | $7,668,608 |
| Virginia Tech | ACC | 0.88 | 10 | $7,625,178 |
| Colorado | Big 12 | 0.94 | 10 | $7,544,663 |
| St. John's | Big East | 1.08 | 10 | $7,516,719 |
| NC State | ACC | 0.96 | 10 | $7,512,732 |
| Clemson | ACC | 0.92 | 10 | $7,509,891 |
| Ole Miss | SEC | 0.94 | 11 | $7,419,807 |
| Georgia Tech | ACC | 0.88 | 12 | $7,353,423 |
| Arizona State | Big 12 | 0.96 | 9 | $7,328,304 |
| Nebraska | Big Ten | 0.84 | 10 | $7,324,222 |
| Notre Dame | ACC | 0.96 | 9 | $7,251,408 |
| Xavier | Big East | 0.92 | 9 | $7,240,032 |
| Mississippi State | SEC | 0.90 | 10 | $7,229,992 |
| Pittsburgh | ACC | 0.92 | 8 | $7,206,394 |
| Virginia | ACC | 1.00 | 9 | $7,155,000 |
| Florida State | ACC | 0.96 | 9 | $7,088,112 |
| Vanderbilt | SEC | 0.86 | 10 | $6,960,581 |
| Utah | Big 12 | 0.86 | 10 | $6,701,292 |
| South Carolina | SEC | 0.88 | 11 | $6,691,410 |
| Penn State | Big Ten | 0.90 | 10 | $6,684,354 |
| Northwestern | Big Ten | 0.82 | 11 | $6,472,423 |
| Seton Hall | Big East | 0.86 | 11 | $6,463,287 |
| West Virginia | Big 12 | 0.92 | 10 | $6,447,222 |
| DePaul | Big East | 0.82 | 10 | $6,351,073 |
| SMU | ACC | 0.90 | 8 | $6,328,326 |
| Boston College | ACC | 0.82 | 9 | $6,304,457 |
| Stanford | ACC | 0.84 | 11 | $6,173,496 |
| Wake Forest | ACC | 0.84 | 10 | $6,099,219 |
| UCF | Big 12 | 0.88 | 10 | $6,030,882 |
| TCU | Big 12 | 0.88 | 8 | $5,920,398 |
| Rutgers | Big Ten | 0.86 | 11 | $5,565,833 |
| San Diego State | Mountain West | 0.72 | 9 | $5,097,870 |

**Total valued players:** 848 across 82 teams. Team totals include reported override values for known deals.

---

## 9. Changelog

| Version | Date | Notes |
|---------|------|-------|
| 1.0 | April 2026 | BYU launch. Formula established. 17 players valued. Class year enrichment from ESPN. |
| 1.1 | April 2026 | Position bases doubled (Power 4 recalibration). Market multiplier bands updated for mid-major and lower tiers. Kentucky market_multiplier adjusted from 1.25 to 1.20. Dybantsa updated to $4,400,000 (reported). Quaintance added at $2,000,000 (reported). Basis: Opendorse 2025-26 market data + publicly reported deal anchors. |
| 1.2 | April 2026 | Eligibility gate added. Players below MPG ≥ 8 (with stats) or star_rating ≥ 4 (incoming) receive NULL valuation. Team totals now reflect NIL market participants only. 15 of 63 players gated across 4 teams. |
| 1.3 | April 2026 | Formula fix: combined_premium = max(draft, role) when draft data exists, role_tier alone otherwise. Prevents multiplicative double-counting for franchise-tier lottery picks. Discovered via Lendeborg (Michigan) producing $5.31M. Option B (conditional max) preserves incoming/rotation discounts for non-drafted players. |
| 1.4 | April 2026 | Universe expansion: 14 → 82 teams. All Power 4 conferences (SEC 16, Big Ten 18, Big 12 16, ACC 18), full Big East (11), plus Gonzaga, Memphis, San Diego State. 1,278 players ingested, 848 valued, 66 draft prospects across 27 teams. Pagination bug fixed in valuation engine (Supabase 1,000-row default limit silently dropped players beyond first page). Social data coverage remains at 13 teams pending On3 org key expansion. |
