# College Front Office --- Operations Runbook

## 1. Team Onboarding Checklist

Step-by-step process for adding a new school to the College Front Office platform. Every step must be completed in order. Someone should be able to onboard a new school by following this document alone.

### 1.1 Create Team Record

Insert a new row into the Supabase `teams` table with the following fields:

| Field | Value | Notes |
|-------|-------|-------|
| `university_name` | e.g., "Penn State" | Must match canonical name used across all scripts |
| `conference` | e.g., "Big Ten" | One of: SEC, Big Ten, Big 12, ACC, Independent |
| `market_multiplier` | See tiers below | Numeric, 0.80 to 1.30 |
| `estimated_cap_space` | `20500000` | Default $20,500,000 for all new teams |
| `logo_url` | ESPN CDN URL | e.g., `https://a.espncdn.com/i/teamlogos/ncaa/500/{espn_id}.png` |
| `active_payroll` | `0` | Computed later by the valuation engine |

**Market multiplier tiers:**

- SEC / Big Ten: 1.20
- ACC / Independent: 1.00
- Adjust +/-0.05 to 0.10 based on program stature (Ohio State gets 1.30, Vanderbilt gets 0.95)

Example SQL:

```sql
INSERT INTO teams (university_name, conference, market_multiplier, estimated_cap_space, logo_url, active_payroll)
VALUES ('Penn State', 'Big Ten', 1.20, 20500000, 'https://a.espncdn.com/i/teamlogos/ncaa/500/213.png', 0);
```

### 1.2 Add Ourlads URL

Add the team's Ourlads depth chart URL to the `OURLADS_URLS` dict in `python_engine/sync_ourlads_depth_charts.py`:

- Format: `https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/{slug}/{id}`
- Find the URL by browsing ourlads.com, then NCAA Football, then Depth Charts, then select the team
- The dict key must be the normalized university_name (lowercase)

Example:

```python
"penn state": "https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/penn-state/81",
```

### 1.3 Add EA Sports Team ID

Add the team's EA CFB 26 ID to the `EA_TEAM_IDS` dict in `python_engine/scrape_ea_ratings.py`:

- To find the ID: check the EA ratings page with the `?team={id}` query parameter
- Current IDs for the 16 tracked teams:

| Team | EA ID |
|------|-------|
| Alabama | 3 |
| Clemson | 20 |
| Florida | 29 |
| Georgia | 32 |
| LSU | 48 |
| Miami | 52 |
| Michigan | 54 |
| Notre Dame | 70 |
| Ohio State | 72 |
| Oklahoma | 73 |
| Oregon | 77 |
| South Carolina | 88 |
| Tennessee | 94 |
| Texas | 96 |
| USC | 110 |
| Washington | 120 |

### 1.4 Add ESPN Team ID

Add the team to `ESPN_TEAM_MAP` in `python_engine/sync_ourlads_depth_charts.py` (used for the ESPN roster sync):

| Team | ESPN ID |
|------|---------|
| Ohio State | 194 |
| Georgia | 61 |
| Alabama | 333 |
| Texas | 251 |
| Oregon | 2483 |
| Michigan | 130 |
| USC | 30 |
| Washington | 264 |
| LSU | 99 |
| Tennessee | 2633 |
| Oklahoma | 201 |
| Florida | 57 |
| South Carolina | 2579 |
| Miami | 2390 |
| Clemson | 228 |
| Notre Dame | 87 |

### 1.5 Add School Aliases

Add the school's name variations to:

- `SCHOOL_ALIASES` in `python_engine/flag_draft_eligible.py` (for Drafttek matching)
- Any known abbreviations (e.g., "Ohio St.", "S. Carolina", "Southern Cal")

When adding aliases:

1. Browse each data source and note the exact team name used
2. Add to the appropriate alias map in the script
3. Test with `fuzzy(norm(alias), norm(canonical))` to ensure >= 0.90
4. Verify no collisions: `fuzzy(norm(new_alias), norm(other_school))` must be < 0.85 for all existing schools

### 1.6 Import Roster

Run in this exact order:

```bash
cd python_engine
python ingest_espn_rosters.py                    # imports ESPN roster
python map_cfbd_ids.py                           # maps CFBD player IDs
python enrich_star_ratings.py                    # adds historical star ratings
python enrich_class_years.py                     # adds class years from CFBD recruiting
python update_class_years.py                     # converts to human-readable labels
```

### 1.7 Import Recruits

```bash
python import_recruiting_class.py --year 2026 --min-stars 4
python import_recruiting_class.py --year 2027 --min-stars 4
python populate_hs_grad_year.py
```

### 1.8 Sync Depth Charts

```bash
python sync_ourlads_depth_charts.py --team {teamname} --apply
```

Replace `{teamname}` with the lowercase canonical name (e.g., `penn-state`).

### 1.9 Scrape EA Ratings

```bash
python scrape_ea_ratings.py --team {teamname}
python populate_ea_ratings.py --apply
```

### 1.10 Compute Production Scores

```bash
python calculate_production_scores.py
```

### 1.11 Run Valuations

```bash
python calculate_cfo_valuations.py
```

This must always be the final step. The valuation engine (V3.5) reads all upstream data and computes `cfo_valuation` for every player.

### 1.12 Verification

After onboarding, verify the following:

| Check | Expected |
|-------|----------|
| Player count | 70-120 college athletes per team |
| Depth chart coverage | 40-70 players on depth chart |
| Valuation coverage | All depth chart players should have valuations |
| Star player gaps | No 4/5-star active players with NULL valuations |
| Top QB valuation | $500K+ for Power 4 programs |
| OL starter valuations | $400K+ (confirms EA rating fallback is working) |

Useful verification queries:

```sql
-- Player count by team
SELECT t.university_name, COUNT(*)
FROM players p JOIN teams t ON p.team_id = t.id
WHERE p.roster_status = 'active' AND p.player_tag = 'College Athlete'
GROUP BY t.university_name ORDER BY COUNT(*) DESC;

-- Depth chart coverage
SELECT t.university_name, COUNT(*) FILTER (WHERE p.is_on_depth_chart) AS on_dc, COUNT(*) AS total
FROM players p JOIN teams t ON p.team_id = t.id
WHERE p.roster_status = 'active' AND p.player_tag = 'College Athlete'
GROUP BY t.university_name ORDER BY on_dc DESC;

-- Missing valuations for starred players
SELECT p.name, p.position, p.star_rating, t.university_name
FROM players p JOIN teams t ON p.team_id = t.id
WHERE p.star_rating >= 4 AND p.cfo_valuation IS NULL
  AND p.roster_status = 'active';
```

---

## 2. Data Pipeline Execution Order

### 2.1 Full Fresh Build (new database)

Run these steps in order. Each numbered group must complete before the next begins.

```bash
# 1. Team setup (manual -- insert team records in Supabase)
python update_team_markets.py                   # sets conference + market_multiplier
python ingest_eada_finances.py                  # imports financial data

# 2. Roster import
python ingest_espn_rosters.py                   # ESPN roster data
python map_cfbd_ids.py                          # CFBD player ID mapping
python enrich_star_ratings.py                   # historical star ratings
python enrich_class_years.py                    # recruiting class years
python update_class_years.py                    # human-readable labels

# 3. Recruiting
python import_recruiting_class.py --year 2026 --min-stars 4
python import_recruiting_class.py --year 2027 --min-stars 4
python import_recruiting_class.py --year 2028 --min-stars 4
python populate_hs_grad_year.py

# 4. Depth charts & external ratings
python sync_ourlads_depth_charts.py --apply     # Ourlads depth charts
python scrape_ea_ratings.py                     # EA CFB 26 ratings
python populate_ea_ratings.py --apply           # write EA ratings to DB

# 5. Production & draft data
python calculate_production_scores.py           # CFBD production scores
python populate_draft_projections.py            # draft projections from CSV

# 6. Roster status
python sync_roster_status.py --dry-run          # preview departures
python sync_roster_status.py                    # apply departures
python flag_draft_eligible.py --apply-status    # flag draft declarees

# 7. Overrides
python identify_override_candidates.py          # screen for overrides
# (manual review of candidates, add to approved_overrides.csv)
python apply_overrides.py                       # apply approved overrides
python verify_override_urls.py                  # validate source URLs

# 8. Social data
python scrape_on3_socials.py                    # social follower counts
python scrape_on3_valuations.py                 # On3 valuations (comparison only)

# 9. Cleanup
python clean_duplicates.py                      # remove duplicate records

# 10. Valuations (ALWAYS LAST)
python calculate_cfo_valuations.py              # compute all valuations
```

### 2.2 Recurring Update Pipeline

**Weekly (during season):**

```bash
python calculate_production_scores.py
python sync_ourlads_depth_charts.py --apply
python calculate_cfo_valuations.py
```

**Monthly:**

```bash
python scrape_on3_socials.py
python scrape_on3_valuations.py
python identify_override_candidates.py
python verify_override_urls.py
python calculate_cfo_valuations.py
```

**Post-Transfer Portal (January through April):**

```bash
python sync_roster_status.py --dry-run          # preview
python sync_roster_status.py                    # apply
# EA cross-reference to detect transfers missed by CFBD
python scrape_ea_ratings.py                     # scrape all 16 teams
# Compare EA team assignments vs DB — any mismatches are transfers
python sync_ourlads_depth_charts.py --apply     # updated depth charts
# For teams with poor Ourlads coverage (e.g., Tennessee):
python assign_default_depth_chart.py --apply    # default DC for unvalued 4/5-star
python scrape_ea_ratings.py                     # EA may update rosters
python populate_ea_ratings.py --apply
python calculate_cfo_valuations.py
```

**Post-Draft (April through May):**

```bash
python flag_draft_eligible.py --apply-status    # flag draft declarees
python sync_ourlads_depth_charts.py --apply     # departed players off DC
python calculate_cfo_valuations.py
```

**Preseason (July through August):**

```bash
# EA Sports releases new game -- ratings update
python scrape_ea_ratings.py
python populate_ea_ratings.py --apply
# Ourlads publishes preseason depth charts
python sync_ourlads_depth_charts.py --apply
# New recruits enroll
python import_recruiting_class.py --year 2027 --min-stars 4
python populate_hs_grad_year.py
# Full valuation refresh
python calculate_production_scores.py
python calculate_cfo_valuations.py
```

### 2.6 Headshot Pipeline

After roster data is populated, run headshot mapping:

```bash
cd python_engine
python map_espn_athlete_ids.py                         # College athletes — ESPN headshots
python scrape_247_headshots.py --year 2026             # HS recruits — 247 headshots
python scrape_247_headshots.py --year 2027
python scrape_247_headshots.py --year 2028
```

### 2.7 National Rank Backfill

```bash
cd python_engine
python scrape_247_ranks.py --year 2026
python scrape_247_ranks.py --year 2027
python scrape_247_ranks.py --year 2028
```

### 2.8 Slug Generation

After any new players are added:

```bash
cd python_engine
python generate_slugs.py
```

### 2.9 Roster Sync Pipeline (Transfer Season)

The roster sync pipeline runs three complementary sources to catch all transfers. Run in this order:

```bash
cd python_engine

# Step 1: ESPN roster sync (most reliable — uses ESPN athlete IDs)
python sync_espn_rosters_by_id.py

# Step 2: On3 team roster sync (catches transfers ESPN hasn't processed)
python sync_on3_rosters.py

# Step 3: On3 transfer portal sync (scrapes all 5,400+ committed transfers)
python sync_transfer_portal.py

# Step 4: Re-sync depth charts for transferred players
python sync_ourlads_depth_charts.py --apply

# Step 5: Re-run valuations
python calculate_cfo_valuations.py

# Step 6: Regenerate slugs for new players
python generate_slugs.py
```

**HS Recruit Commitments** (run separately):

```bash
python scrape_247_commitments.py --year 2026
python scrape_247_commitments.py --year 2027
python scrape_247_commitments.py --year 2028
python backfill_recruit_commitments.py --year 2026
python backfill_recruit_commitments.py --year 2027
python backfill_recruit_commitments.py --year 2028
```

**Social Data Refresh** (run after roster changes):

```bash
python scrape_on3_team_socials.py
```

### 2.10 ESPN Team ID Reference

All 68 Power 4 ESPN IDs are in `ESPN_IDS_BY_NAME` in `ingest_espn_rosters.py`. Key corrections (April 2026):

| Team | ESPN ID | Notes |
|------|---------|-------|
| Tennessee | 2633 | Corrected — was previously 245 (Texas A&M) |
| South Carolina | 2579 | Corrected — was previously 257 (Richmond) |

### 2.11 Power 4 Expansion (April 2026)

Expanded from 16 to 68 teams using `expand_to_power4.py`. See `onboard_new_teams.py` for the full pipeline.

### 2.12 Script Dependencies & Safety

**Safe to run independently (no side effects if run alone):**

- `identify_override_candidates.py` (read-only)
- `validate_ea_vs_production.py` (read-only)
- `scrape_ea_ratings.py` (writes CSV only, not DB)
- `flag_draft_eligible.py` without flags (dry-run only)

**MUST run in order:**

- `ingest_espn_rosters.py` then `map_cfbd_ids.py` (cfbd_id depends on roster existing)
- `map_cfbd_ids.py` then `calculate_production_scores.py` (needs cfbd_id)
- `scrape_ea_ratings.py` then `populate_ea_ratings.py` (reads CSV from scraper)
- ANY depth chart/roster/status change then `calculate_cfo_valuations.py` (must recompute)

**Scripts with --dry-run flag:**

| Script | Default Behavior | Flag to Apply |
|--------|-----------------|---------------|
| `sync_ourlads_depth_charts.py` | Dry-run | `--apply` |
| `sync_roster_status.py` | Applies changes | `--dry-run` to preview |
| `flag_draft_eligible.py` | Dry-run | `--apply` or `--apply-status` |
| `populate_ea_ratings.py` | Dry-run | `--apply` |
| `assign_default_depth_chart.py` | Dry-run | `--apply` |
| `ingest_tennessee_transfers.py` | Dry-run | `--apply` |

---

## 3. School Name Alias Map

### 3.1 Canonical Names (in our `teams` table)

Alabama, Clemson, Florida, Georgia, LSU, Miami, Michigan, Notre Dame, Ohio State, Oklahoma, Oregon, South Carolina, Tennessee, Texas, USC, Washington

### 3.2 Known Aliases by Source

| Canonical | CFBD | Ourlads | Drafttek | EA CFB 26 | ESPN | 247Sports |
|-----------|------|---------|----------|-----------|------|-----------|
| Alabama | Alabama | alabama | Alabama | Alabama | Alabama | Alabama |
| Clemson | Clemson | clemson | Clemson | Clemson | Clemson | Clemson |
| Florida | Florida | florida | Florida | Florida | Florida | Florida |
| Georgia | Georgia | georgia | Georgia | Georgia | Georgia | Georgia |
| LSU | LSU | lsu | LSU | LSU | LSU | LSU |
| Miami | Miami | miami | Miami (FL) | Miami | Miami | Miami |
| Michigan | Michigan | michigan | Michigan | Michigan | Michigan | Michigan |
| Notre Dame | Notre Dame | notre-dame | Notre Dame | Notre Dame | Notre Dame | Notre Dame |
| Ohio State | Ohio State | ohio-state | Ohio State, Ohio St. | Ohio State | Ohio State | Ohio State |
| Oklahoma | Oklahoma | oklahoma | Oklahoma | Oklahoma | Oklahoma | Oklahoma |
| Oregon | Oregon | oregon | Oregon | Oregon | Oregon | Oregon |
| South Carolina | South Carolina | south-carolina | South Carolina, S. Carolina | South Carolina | South Carolina | South Carolina |
| Tennessee | Tennessee | tennessee | Tennessee | Tennessee | Tennessee | Tennessee |
| Texas | Texas | texas | Texas | Texas | Texas | Texas |
| USC | USC | usc | USC, Southern California, Southern Cal | USC | USC | USC |
| Washington | Washington | washington | Washington | Washington | Washington | Washington |

### 3.3 Known Collision Risks

**"South Carolina" vs "East Carolina" vs "North Carolina":**

- Fuzzy matching `fuzzy("east carolina", "s carolina") = 0.870` -- exceeds the 0.85 threshold
- FIX: Removed "S. Carolina" alias, raised school matching threshold to 0.90 in `flag_draft_eligible.py`
- RULE: Never use abbreviated aliases like "S. Carolina" in fuzzy matching -- use full names only

**"Miami (FL)" vs "Miami (OH)":**

- Drafttek uses "Miami (FL)", our DB uses "Miami"
- EA uses "Miami" for both -- our EA team ID (52) is specifically Miami FL
- Include "Miami (FL)" and "Miami (Fla.)" as aliases

**"USC" vs "South Carolina":**

- Some sources abbreviate South Carolina as "USC" or "SC"
- Our DB uses "USC" exclusively for Southern California
- Never add "USC" as an alias for South Carolina

### 3.4 Adding New Aliases

When adding a new school, check each data source for name variations:

1. Browse the source website and note the exact team name used
2. Add to the appropriate alias map in the script
3. Test with `fuzzy(norm(alias), norm(canonical))` to ensure >= 0.90
4. Verify no collisions: `fuzzy(norm(new_alias), norm(other_school))` must be < 0.85 for all existing schools

---

## 4. Position Mapping Reference

### 4.1 Canonical CFO Positions

QB, RB, WR, TE, OL, OT, OG, C, IOL, DE, DT, DL, EDGE, LB, CB, S, DB, K, P, LS, ATH, PK

### 4.2 Position Starter Counts (VALUATION_ENGINE.md section 3.8)

```
QB: 1      RB: 1      WR: 3      TE: 2
OL: 5      OT: 5      OG: 5      C: 5      IOL: 5
EDGE: 2    DE: 2      DT: 2      DL: 2
LB: 3      DB: 3
CB: 2      S: 2
K: 1       P: 1       LS: 1      PK: 1
ATH: 1
```

**Single-starter positions** (steeper backup penalty): QB, RB, K, P, LS, PK, ATH

**Multi-starter positions** (softer backup penalty): Everything else

### 4.3 Ourlads to CFO Position Map

```
WR-X   -> WR       WR-Z   -> WR       WR-SL  -> WR       WR-H   -> WR
LT     -> OL       LG     -> OL       C      -> OL       RG     -> OL       RT     -> OL
TE     -> TE       QB     -> QB       RB     -> RB       HB     -> RB       FB     -> RB
DE     -> DE       NT     -> DL       DT     -> DL
JACK   -> DE       LEO    -> DE       SAM    -> LB
MAC    -> LB       MIKE   -> LB       MLB    -> LB       WLB    -> LB       WILL   -> LB       MONEY  -> LB
LCB    -> CB       RCB    -> CB       NB     -> DB
SS     -> S        FS     -> S
PT     -> P        PK     -> PK       KO     -> PK       LS     -> LS       H      -> QB
PR     -> WR       KR     -> RB
LDE    -> DE       RDE    -> DE       LDT    -> DL       RDT    -> DL
```

Note: FB is mapped to RB, not TE.

### 4.4 EA CFB 26 to CFO Position Map

EA uses granular NFL-style positions:

```
LEDG   -> DE       REDG   -> DE       (Left/Right Edge)
MIKE   -> LB       WILL   -> LB       SAM    -> LB
FS     -> S        SS     -> S
HB     -> RB
LT     -> OL       LG     -> OL       C      -> OL       RG     -> OL       RT     -> OL
CB     -> CB       WR     -> WR       TE     -> TE       QB     -> QB
DT     -> DL       RE     -> DE       LE     -> DE
K      -> PK       P      -> P        LS     -> LS
FB     -> TE       (Fullbacks mapped to TE for base value purposes)
```

### 4.5 Drafttek to CFO Position Map

Drafttek uses NFL scouting positions:

```
DL1T   -> DL       (1-technique DT)
DL3T   -> DL       (3-technique DT)
DL5T   -> DL       (5-technique DE)
OLB    -> LB
ILB    -> LB
CBN    -> CB       (Nickel corner)
WRS    -> WR       (Slot receiver)
OC     -> OL       (Center)
OG     -> OL
OT     -> OL
EDGE   -> DE
```

### 4.6 Position Classification Notes

- **EDGE vs DE vs DL:** Ourlads uses JACK/LEO (team-specific DE names). Drafttek uses EDGE. EA uses LEDG/REDG. Our DB stores most as either DE or DL. When a player is listed as "EDGE" on Drafttek but "LB" in our DB, it is a known mismatch -- defensive ends who rush from a linebacker alignment.
- **FB to RB or TE:** We map Ourlads FB to RB. EA maps FB differently. Max Bredeson (Michigan) is listed as FB on EA but TE in our DB -- a real mismatch.
- **TE starter count = 2:** Changed from 1 to 2 in V3.4. Most modern offenses use 2 tight ends (base personnel 12 package). TE2 is now valued as a starter (1.0x) rather than backup (0.35x).

---

## 5. Known Issues & Lessons Learned

### 5.1 Tennessee Ourlads Coverage Gap

**Issue:** Ourlads only lists 69 of Tennessee's approximately 230 active players. Many starters (including starting QB Marcel Reed) were missing.

**Cause:** Ourlads depth chart was stale/incomplete for Tennessee.

**Solution:** Ingested 24 transfer-in players from Ourlads manually via `ingest_tennessee_transfers.py`. Used `assign_default_depth_chart.py` for remaining 4/5-star players. Later detected 12 Tennessee to Texas A&M transfers via EA cross-reference.

**Prevention:** For teams with poor Ourlads coverage, supplement with EA roster data. Cross-reference EA team assignments to detect transfers.

### 5.2 OL Production Score Gap

**Issue:** CFBD has no meaningful OL statistics. All OL players got production_score = 0/NULL, falling to star_rating proxy in talent_modifier.

**Solution:** Added EA CFB 26 OVR as a fallback in the talent_modifier priority chain: production then EA then star. EA rates OL players based on gameplay attributes, providing a useful talent signal.

**Impact:** Drew Bobo (Georgia C): $495K to $657K with EA fallback. Gap to On3 closed from 42% to 7%.

### 5.3 Ourlads Depth Chart Rank Parsing Bug

**Issue:** The old `sync_depth_charts.py` used column index as rank. OL starters were getting rank 6-16 instead of 1-5, causing 0.55x to 0.25x multipliers instead of 1.0x.

**Solution:** Rewrote `sync_ourlads_depth_charts.py` to parse cell indices 2, 4, 6, 8 as ranks 1-4. Cell 10 (the departed column) is always skipped.

**Impact:** 76 OL players corrected. Drew Bobo went from $131K to $495K.

### 5.4 Ourlads Departed Column

**Issue:** Ourlads depth chart rows have 11 cells. Cell 10 contains departed players (transfers, draft declarees). The old script included these, incorrectly marking departed players as "on depth chart."

**Solution:** Skip cell index 10 entirely. Only parse cells 2, 4, 6, 8 (ranks 1-4).

### 5.5 East Carolina / North Carolina Fuzzy Collision

**Issue:** `fuzzy("east carolina", "s carolina") = 0.870`, exceeding the 0.85 school matching threshold. Caused Anthony Smith (East Carolina WR) to falsely match against South Carolina players.

**Solution:** Removed "S. Carolina" alias. Raised school matching threshold to 0.90 with exact-match-first strategy.

### 5.6 Transfer Detection via EA Cross-Reference

**Process:** Search EA CFB 26 ratings across ALL 11,062 players (134 teams) for names matching our players. If a player appears on a different EA team than our DB, they have transferred.

**Example:** Found 12 Tennessee players on Texas A&M's EA roster (Marcel Reed, Dezz Ricks, DJ Hicks, etc.). Flagged as departed_transfer.

### 5.7 Orphaned Records (No team_id)

**Issue:** 14 players with star_rating >= 4 had no team_id. They were HS recruit imports incorrectly tagged as College Athlete.

**Solution:** Cross-referenced against EA ratings (no matches) and DB duplicates (none). Deleted all 14 as stale records.

### 5.8 Name Normalization Issues

- **"Jr." / "III" suffixes:** "C.J. Allen" in our DB, "CJ Allen" on Ourlads, "C.J. Allen" on Drafttek. Normalize: strip periods, apostrophes, hyphens, convert to lowercase.
- **"Damon Payne Jr." vs "Damon Payne":** Fuzzy score 0.88 -- below 0.90 but above 0.80 threshold. Works with standard 0.80 cutoff.
- **"George Gumbs" vs "George Gumbs Jr.":** Fuzzy score 0.94. Works fine.

### 5.9 Sentinel Values

| Field | Sentinel Values | Meaning |
|-------|----------------|---------|
| `nfl_draft_projection` | NULL, 0, >= 500 (including 999) | "no data" -- applies 1.0x neutral multiplier |
| `production_score` | NULL, 0, 0.00 | "no data" -- falls to EA/star fallback |
| `ea_rating` | NULL, 0 | "no data" -- falls to star fallback |

Always check for sentinels BEFORE using values in calculations.

### 5.10 Override Protection Rules

Override players (`is_override=true`) must NEVER be auto-modified by any pipeline script:

- `sync_roster_status.py` skips overrides (logs for manual review)
- `sync_ourlads_depth_charts.py` skips overrides
- `flag_draft_eligible.py` skips overrides
- `assign_default_depth_chart.py` skips overrides

### 5.11 Batch Upsert Constraint Error

**Issue:** Supabase's upsert tries INSERT on conflict. If the row has only partial columns (e.g., id + roster_status), the INSERT fails on NOT NULL constraints (like `name`).

**Solution:** Use `.update().eq("id", pid)` instead of `.upsert()` when updating existing rows. Or include the full row in upsert batches. The valuation engine's `_flush_batch` has a row-by-row fallback for this.

---

### 5.12 Tennessee-to-Texas A&M Transfer Detection
**Issue:** 12 Tennessee players were still marked active in our DB but had transferred to Texas A&M. CFBD portal data didn't catch them.
**Solution:** Scraped all 11,062 EA CFB 26 players across 134 teams. Any player in our DB whose EA team differs from their DB team is a confirmed transfer. Found and flagged all 12.
**Prevention:** Run EA cross-reference after every transfer portal window.

### 5.13 2028 HS QB Overvaluation
**Issue:** 2028 HS QBs (Jayden Wade, Christopher Vargas) were valued at 4.6× On3. The 0.70× experience multiplier combined with QB $1.2M base × 2.0 HS position premium produced $1.3M+ valuations.
**Solution:** Lowered 2028 experience multiplier from 0.70 to 0.35, and 2029+ from 0.65 to 0.25.
**Impact:** Jayden Wade: $1,344,000 → $672,000 (2.32× On3 vs 4.63× before).

### 5.14 Position Mapping During Recruit Import
**Issue:** Immanuel Iheanacho (Oregon OT) was stored as IOL, giving him $475K base instead of $800K OT base.
**Solution:** Manual position correction. OT and IOL have different base values.
**Prevention:** Cross-validate position assignments during recruit import. Tackles should always be OT, not IOL.

### 5.15 Star Rating vs Composite Score Inconsistency
**Issue:** Jett Washington (Oregon S) had 97.28 composite but star_rating=4. A 97+ composite should always be 5-star.
**Solution:** Manual star_rating correction to 5.
**Prevention:** Run validation query: `WHERE composite_score >= 97 AND star_rating < 5`.

## 6. Rollback Procedures

### 6.1 Safe Fields to Bulk Reset

These can be recomputed from source data at any time:

| Field | Recovery Script |
|-------|----------------|
| `cfo_valuation` | `calculate_cfo_valuations.py` |
| `production_score` | `calculate_production_scores.py` |
| `ea_rating` | `scrape_ea_ratings.py` then `populate_ea_ratings.py` |
| `depth_chart_rank` / `is_on_depth_chart` | `sync_ourlads_depth_charts.py` |
| `nfl_draft_projection` | `populate_draft_projections.py` (reimport from CSV) |

### 6.2 Dangerous Fields (cannot auto-recover)

- `is_override` -- must be manually verified against `approved_overrides.csv`
- `roster_status` -- requires CFBD API + manual review to reconstruct
- `team_id` -- requires ESPN/CFBD roster data to re-associate
- Deleted records -- cannot be recovered (use soft delete via roster_status instead)

### 6.3 Identifying Bad Batch Updates

After a bad script run:

1. Check `last_updated` timestamps -- all rows modified in the batch will have the same timestamp
2. Query:
   ```sql
   SELECT COUNT(*), last_updated
   FROM players
   GROUP BY last_updated
   ORDER BY last_updated DESC
   LIMIT 5;
   ```
3. If the count matches the expected batch size, those are the affected rows
4. For depth chart issues: check players where `is_on_depth_chart = true` but `cfo_valuation IS NULL` -- these should not exist

### 6.4 Nuclear Reset (last resort)

To reset all depth charts and recompute from scratch:

```sql
UPDATE players
SET is_on_depth_chart = false, depth_chart_rank = NULL
WHERE player_tag = 'College Athlete';
```

Then rerun:

```bash
python sync_ourlads_depth_charts.py --apply
python calculate_cfo_valuations.py
```
