# College Front Office — Data Sources Reference

## 1. CollegeFootballData (CFBD)

**What it provides:** Rosters, season stats (passing, rushing, receiving, defense), transfer portal entries, recruiting data (247Sports composite), draft history
**API endpoint:** `https://api.collegefootballdata.com`
**Access:** Free API key required (`CFBD_API_KEY` in .env.local). Register at collegefootballdata.com
**Rate limits:** No formal limit, but use 0.1–1.0s delay between requests
**How accessed:** REST API with JSON responses via `requests` library

**Endpoints used:**
| Endpoint | Script | Purpose |
|----------|--------|---------|
| `/stats/player/season?year={year}` | `calculate_production_scores.py` | Season-level player stats |
| `/roster?year={year}&team={name}` | `map_cfbd_ids.py`, `update_class_years.py`, `sync_roster_status.py` | Team rosters with CFBD player IDs |
| `/recruiting/players?year={year}` | `import_recruiting_class.py`, `enrich_star_ratings.py`, `enrich_class_years.py` | Recruiting data with 247 composite |
| `/player/portal?year={year}` | `sync_roster_status.py` | Transfer portal entries |
| `/draft/picks?year={year}` | `populate_draft_projections.py` | NFL draft results |

**Fields extracted:**
- From roster: id (cfbd_id), firstName, lastName, position, year (class year)
- From stats: passing yards/TDs/INTs, rushing yards/TDs, receiving yards/receptions/TDs, tackles/TFL/sacks/INTs/PDs
- From recruiting: name, stars, rating (composite), committedTo, position
- From portal: firstName, lastName, origin, destination

**Gotchas:**
- **OL stats are nonexistent.** CFBD has no meaningful offensive line statistics. production_score will ALWAYS be 0/NULL for OL players. This is the primary reason we added the EA rating fallback.
- **CFBD roster year lag:** 2026 rosters may not appear until the season starts. Fall back to 2025 if 2026 returns empty.
- **Player ID instability:** CFBD player IDs occasionally change between seasons. The `map_cfbd_ids.py` script should be rerun annually.
- **Recruiting data covers 4 years back.** Stars from 2018+ are available; older players may have no star data.
- **Tennessee/South Carolina name matching:** These teams have historically poor CFBD name matching. Known issue documented in `sync_roster_status.py`.
- **Stats are cumulative per season.** No per-game breakdown — you get total season stats only.
- **Stat categories vary by source.** Some categories use different names (e.g., "PASS" vs "passing" depending on endpoint version).

**Data freshness:** Rosters update within 24 hours of official school announcements. Stats update within 48 hours of games. Portal data is real-time.

**Coverage gaps:** No OL stats, no snap counts, no PFF-style grades, limited special teams data.

---

## 2. Ourlads (ourlads.com)

**What it provides:** NCAA football depth charts with player names, jersey numbers, position groups, and depth ordering (1st string through 4th string)
**URL pattern:** `https://www.ourlads.com/ncaa-football-depth-charts/depth-chart/{team-slug}/{team-id}`
**Access:** Free, no API key. Scrape via HTTP GET with User-Agent header.
**Rate limits:** Use 1.5s delay between page fetches. Will return 403 if too fast.
**How accessed:** HTML scraping with BeautifulSoup

**Team URL map (from `sync_ourlads_depth_charts.py`):**
```
alabama: /depth-chart/alabama/89923
clemson: /depth-chart/clemson/90314
florida: /depth-chart/florida/90498
georgia: /depth-chart/georgia/90590
lsu: /depth-chart/lsu/90981
miami: /depth-chart/miami/91073
michigan: /depth-chart/michigan/91119
notre dame: /depth-chart/notre-dame/91487
ohio state: /depth-chart/ohio-state/91533
oklahoma: /depth-chart/oklahoma/91556
oregon: /depth-chart/oregon/91625
south carolina: /depth-chart/south-carolina/91832
tennessee: /depth-chart/tennessee/91993
texas: /depth-chart/texas/92016
usc: /depth-chart/usc/92269
washington: /depth-chart/washington/92453
```

**HTML structure:**
- Three `<tbody>` sections: `dcTBody` (offense), `dcTBody2` (defense), `dcTBody3` (special teams)
- Each `<tr>` = one position group (WR-X, LT, QB, etc.)
- 11 cells per row: `[position] [jersey#] [rank1_player] [jersey#] [rank2_player] [jersey#] [rank3_player] [jersey#] [rank4_player] [jersey#] [departed_player]`
- Active player cells: indices 2, 4, 6, 8 → ranks 1, 2, 3, 4
- **Cell 10 is the DEPARTED column — MUST be skipped**
- Player names in `<a>` tags: format "Lastname, Firstname RS SR/TR"
- Empty slots: `<a href="/player//0">` (href ends with /0)

**Name parsing:**
- Format: "Lastname, Firstname RS SR" or "Lastname, Firstname JR/TR"
- Suffix tokens to strip: RS, SR, JR, FR, SO, TR, GR
- First non-suffix token after comma = first name

**Class year parsing from suffixes:**
- FR = 1, SO = 2, JR = 3, SR = 4, GR/RS SR = 5
- RS prefix adds 1 (RS FR = 2, RS SO = 3, RS JR = 4, RS SR = 5)
- /TR suffix indicates transfer

**Gotchas:**
- **Tennessee is severely incomplete.** Only 69 of ~230 players listed. Their starting QB (Marcel Reed) was missing entirely. Supplemented with ESPN data.
- **The departed column (cell 10) must be skipped.** It contains players who transferred out, declared for draft, or graduated. Including it will mark departed players as "on depth chart."
- **Position names are team-specific.** Georgia uses "JACK" and "MONEY" for defensive positions. Other teams use "LEO", "SAM", "WILL". All must be mapped to canonical CFO positions.
- **Depth charts may be stale.** Some teams don't update until preseason. Check the page header for "last updated" date.
- **Duplicate appearances.** Players may appear at multiple positions (e.g., QB at QB and H for holder). Use best (lowest) rank across all appearances.
- **New transfer-in players may not be in our DB.** Run `ingest_tennessee_transfers.py`-style script to add them before syncing depth charts.

**Data freshness:** Updated during season (roughly weekly). Preseason updates start in July/August. Offseason may be stale.

---

## 3. Drafttek (drafttek.com)

**What it provides:** 2026 NFL Draft Big Board — ranked list of top 600 draft prospects with rank, name, school, position
**URL pattern:** `https://www.drafttek.com/2026-NFL-Draft-Big-Board/Top-NFL-Draft-Prospects-2026-Page-{1-6}.asp`
**Access:** Free, no API key. Scrape via HTTP GET.
**Rate limits:** Use 1.5s delay between page fetches.
**How accessed:** HTML scraping with BeautifulSoup

**HTML structure:**
- `<table class="player-info">` contains all prospect rows
- Each `<tr>` has 9 `<td>` cells: Rank, CNG (change), Prospect Name, College, POS, Ht, Wt, CLS, BIO
- Header row has non-numeric rank text ("Rank") — skip via `int(rank_text)` try/except
- 100 prospects per page, 6 pages total

**Fields extracted:** rank (int), name (text), school (text), position (text, uppercase)

**Gotchas:**
- **School names use abbreviations.** "Ohio St.", "Southern Cal", "S. Carolina", "Miami (FL)". Must be handled by alias map.
- **East Carolina fuzzy-matches South Carolina** at 0.87 via the "S. Carolina" alias. Fixed by removing that alias and raising threshold to 0.90.
- **Prospects include non-declarees.** Players ranked on the big board may NOT have declared for the draft. Don't auto-flag as departed_draft without verification.
- **Positions use NFL scouting terminology.** DL1T, DL3T, DL5T, OLB, ILB, CBN, WRS, OC — all need mapping to CFO positions.
- **Name format varies.** Some have "Jr.", "III", "II" — fuzzy matching handles this.

**Data freshness:** Updated weekly during draft season. Board expands to 600 as draft approaches.

---

## 4. EA Sports College Football 26 (ea.com)

**What it provides:** Player OVR (overall) ratings (0-99 scale), per-attribute ratings, position, school year, jersey number
**API endpoint:** Next.js data route: `https://www.ea.com/_next/data/{buildId}/en/games/ea-sports-college-football/ratings.json?team={teamId}`
**Main page:** `https://www.ea.com/games/ea-sports-college-football/ratings`
**Access:** Free, no API key. The buildId must be extracted from the main page's `__NEXT_DATA__` JSON blob.
**Rate limits:** 1.0s delay between requests.
**How accessed:** JSON API via Next.js data route

**Build ID discovery:**
1. Fetch the main ratings page
2. Search for `"buildId":"([^"]+)"` in the HTML
3. Use the extracted buildId in data route URLs
4. BuildId changes when EA deploys a new version — must be re-discovered each run

**EA Team IDs (from `scrape_ea_ratings.py`):**
```
Alabama=3, Clemson=20, Florida=29, Georgia=32, LSU=48, Miami=52,
Michigan=54, Notre Dame=70, Ohio State=72, Oklahoma=73, Oregon=77,
South Carolina=88, Tennessee=94, Texas=96, USC=110, Washington=120
```

**JSON response structure:**
```json
{
  "pageProps": {
    "ratingDetails": {
      "items": [
        {
          "firstName": "Fernando",
          "lastName": "Mendoza",
          "overallRating": 99,
          "position": { "id": "QB", "shortLabel": "QB", "label": "Quarterback" },
          "team": { "id": 38, "label": "Indiana" },
          "schoolYear": "Junior",
          "jerseyNum": 15,
          "stats": { "acceleration": {"value": 86}, "agility": {"value": 86} }
        }
      ],
      "totalItems": 11062
    }
  }
}
```

**Fields extracted:** firstName, lastName, overallRating (OVR), position.shortLabel, team.label, schoolYear, jerseyNum

**EA OVR to Talent Modifier Tier Mapping:**
```
EA >= 90 -> 1.4 (Elite)
EA >= 82 -> 1.2 (Strong)
EA >= 75 -> 1.0 (Average)
EA >= 68 -> 0.65 (Below Average)
EA < 68  -> 0.4 (Low)
```

**Gotchas:**
- **buildId is ephemeral.** Changes on every EA deployment. Must be re-discovered at the start of each scrape run. The script does this automatically.
- **Not all players are in the game.** Freshmen, mid-year transfers, and some walk-ons may be missing.
- **EA positions differ from ours.** LEDG, REDG, MIKE, WILL, SAM, FS, SS, HB — all need mapping.
- **EA ratings are opinions, not production data.** A player rated 90 in the game may have a production_score of 50. The Pearson correlation is 0.640 — moderate but far from perfect. Use EA as a FALLBACK only.
- **Team-specific queries return all players** — no pagination needed within a single team (typically 75-90 players per team).
- **Full 11,062-player scrape requires 111 pages** (100 per page). Only needed for cross-team transfer detection.

**Data freshness:** EA updates ratings weekly during the season ("Week X Ratings"). Preseason ratings available in July.

**Coverage:** 1,307 of our players matched across 16 teams (99.1% match rate).

---

## 5. 247Sports

**What it provides:** Composite recruiting rankings, composite scores (0-100 scale), star ratings (1-5), national/position/state rankings
**Access:** Data accessed indirectly via CFBD API (`/recruiting/players` endpoint pulls 247 composite data). Direct scraping of 247sports.com requires handling JavaScript rendering.
**How accessed:** Via CFBD API (preferred) or manual CSV export

**Fields extracted (via CFBD):** name, stars, rating (composite score, 0-1.0 scale in CFBD -> multiplied by 100 for our 0-100 scale), committedTo, position, city, stateProvince

**CSV format (for manual import via `import_recruiting_class.py --csv`):**
```csv
name,position,star_rating,composite_score,committed_school
Player Name,QB,5,0.9998,Georgia
```

**Gotchas:**
- **Composite scores from CFBD are 0-1.0 scale** (e.g., 0.9998). Our DB stores them as 0-100 scale (e.g., 99.98). Multiply by 100 when importing from CFBD.
- **Some recruits decommit.** A player committed to Georgia in December may flip to Alabama in January. Re-running import with updated data overwrites the old commitment.
- **Class year interpretation:** In the 247/recruiting context, "Class of 2027" means hs_grad_year=2027, not college class_year=3.
- **Only 4-star and 5-star recruits get valuations** in our engine (per eligibility gate). 3-star and below are tracked but get NULL valuations.

**Data freshness:** Rankings update weekly during recruiting season (Dec-Feb signing period). Rankings are finalized after National Signing Day.

---

## 6. ESPN

**What it provides:** Team rosters with player names, positions, jersey numbers, status
**API endpoint:** `https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/{espn_id}/roster?limit=500`
**Access:** Free, no API key. Public API.
**Rate limits:** 1.0s delay between requests.
**How accessed:** JSON API via `requests`

**ESPN Team IDs:**
```
Ohio State=194, Georgia=61, Alabama=333, Texas=251, Oregon=2483,
Michigan=130, USC=30, Washington=264, LSU=99, Tennessee=245,
Oklahoma=201, Florida=57, South Carolina=257, Miami=2390,
Clemson=228, Notre Dame=87
```

**JSON structure:**
```json
{
  "athletes": [
    {
      "position": "offense",
      "items": [
        { "displayName": "Player Name", "position": {"abbreviation": "QB"}, "status": {"name": "Active"} }
      ]
    }
  ]
}
```

**Gotchas:**
- **ESPN IDs don't match CFBD IDs.** They're completely separate ID systems. We use CFBD IDs as our primary external ID (`cfbd_id` column).
- **Position groups are broad:** "offense", "defense", "specialTeam". Individual positions are nested.
- **Roster may include inactive/suspended players.** Filter by `ACTIVE_GROUPS` to exclude practice squad etc.
- **Used primarily for initial roster import** (`ingest_espn_rosters.py`) and team assignment verification.

**Data freshness:** Updates within hours of roster moves processed by schools.

---

## 7. On3 (on3.com)

**What it provides:** NIL valuations (dollar estimates), social media follower counts (Instagram, Twitter/X, TikTok)
**URLs:**
- NIL valuations: `https://www.on3.com/nil/rankings/player/nil-valuations/`
- Social/college rankings: `https://www.on3.com/nil/rankings/player/college/football/`
**Access:** Free pages scraped via __NEXT_DATA__ JSON extraction. Pagination via Next.js data route with buildId.
**Rate limits:** 2.0s delay between pages. Will return 403 if too fast.
**How accessed:** JSON extraction from __NEXT_DATA__ in HTML

**Fields extracted:**
- Valuations: person.name, valuation.valuation (dollar amount)
- Socials: valuation.followers (total), valuation.socialValuations[].followers by platform

**Gotchas:**
- **On3 valuations are for COMPARISON ONLY.** We do NOT use them in our formula. They're stored in `on3_valuation` column and used by `identify_override_candidates.py` to flag players where On3 >> CFO (suggesting we need an override).
- **buildId is ephemeral.** Same as EA — must re-discover from page HTML on each run.
- **Social data may lag.** On3 doesn't update follower counts in real-time.
- **Only covers top ~1000 players.** Many of our tracked players won't appear.
- **Valuation format varies:** "$1.2M", "$850K", "$95,000", or raw integers.

**Data freshness:** Valuations update weekly. Social data updates monthly.

---

## 8. EADA (Equity in Athletics Data Analysis)

**What it provides:** Federal financial reporting data for universities — total athletics revenue, football revenue, football expenses
**Source files:**
- `python_engine/instLevel.xlsx` — institution-level aggregates (GRND_TOTAL_REVENUE)
- `python_engine/EADA_2024.xlsx` — sport-level breakdowns (football-specific)
**Access:** Downloadable from US Department of Education. Updated annually.
**How accessed:** Pandas read_excel, matched via alias map

**Fields extracted:** total_athletics_revenue, total_football_revenue, total_football_expenses
**Reporting year:** FY2023 (latest available as of April 2026)

**Gotchas:**
- **Institution names don't match our team names.** "The University of Alabama" vs "Alabama". The script has a 60+ entry alias map.
- **Data lags 2-3 years.** FY2023 is the latest available; FY2025 won't be available until late 2027.
- **Only used for team-level financial context.** Not directly used in valuation formula — market_multiplier is set manually.

---

## 9. Manual CSV Files

### 9.1 approved_overrides.csv
**Path:** `python_engine/data/approved_overrides.csv`
**Columns:** player_name, total_value, years, annualized_value, source_name, source_url, verified
**Used by:** `apply_overrides.py`
**Purpose:** Manually curated list of verified NIL deals that override the algorithm

### 9.2 draft_projections.csv
**Path:** `python_engine/data/draft_projections.csv`
**Columns:** player_name, position, school, projected_pick
**Used by:** `populate_draft_projections.py`
**Purpose:** Mock draft consensus data from Drafttek and other sources

### 9.3 Recruiting class CSVs
**Path:** `python_engine/data/recruits_{year}_full.csv`
**Columns:** name, position, star_rating/stars, composite_score/rating, committed_school/committedTo
**Used by:** `import_recruiting_class.py --csv`
**Purpose:** Backup import path when CFBD API data is incomplete

### 9.4 ea_ratings.csv (generated)
**Path:** `python_engine/data/ea_ratings.csv`
**Columns:** ea_name, ea_team, ea_position, ea_ovr, ea_school_year, matched_player_name, matched_player_id, match_confidence, cfo_position, cfo_valuation, depth_chart_rank, production_score
**Generated by:** `scrape_ea_ratings.py`
**Used by:** `populate_ea_ratings.py`
**Purpose:** Intermediate file mapping EA ratings to our player records

### 9.5 drafttek_matches.csv (generated)
**Path:** `python_engine/data/drafttek_matches.csv`
**Generated by:** `flag_draft_eligible.py`
**Purpose:** Report of Drafttek prospects matched to our players
