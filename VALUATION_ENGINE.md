# CFO Valuation Engine — Internal Technical Specification

> **Status:** Canonical (V3.5) | **Last Updated:** April 7, 2026
> **Audience:** Developers, Claude Code sessions, internal team only
> **⚠️ PROPRIETARY — Do not share externally or commit to a public repo.**

---

## 1. Overview

The CFO Valuation Engine produces a single integer dollar value (`cfo_valuation`) for every eligible college and high school football player in the system. This value represents College Front Office's proprietary estimate of a player's annualized NIL (Name, Image, Likeness) market value.

Two formula paths exist:
- **College Athlete Formula** — production/draft-based model for active college players on a depth chart
- **High School Recruit Formula** — composite-score-based model for 4★ and 5★ HS recruits

Both paths share market multiplier, experience multiplier, and social premium components.

The engine runs as a Python batch job (`calculate_cfo_valuations.py`) that reads player data from Supabase, computes valuations, and writes results back. It uses the **service role key** and bypasses RLS.

### Algorithm History

| Version | Status | Key Changes |
|---------|--------|-------------|
| V1 | **DEPRECATED** | Simple star_rating × position × experience. Never implemented. |
| V2 | **DEPRECATED** | `random.seed(name)` deterministic randomness. No logic basis. |
| V3 | **SUPERSEDED** | Draft-as-base model. No depth chart gate. Sentinel bugs. |
| V3.1 | **SUPERSEDED** | Position-base model, depth chart gate, star fallback, sentinel fixes. |
| V3.2 | **SUPERSEDED** | Steeper production tiers (0.65/0.40), flat depth chart multipliers (1.0/0.30/0.15/0.10). |
| V3.3 | **SUPERSEDED** | Position-aware depth chart with multi-starter counts, split single/multi multipliers, HS composite formula, updated experience curve. |
| V3.4 | **SUPERSEDED** | EA rating fallback in talent_modifier, recruiting pedigree floor in depth chart multiplier, TE=2-starter, ea_rating column. |
| V3.5 | **SUPERSEDED** | Position base value recalibration to 2025-26 market data. 2028 HS experience multiplier reduced (0.70→0.35). |
| V3.6b | **CANONICAL** | QB base $1.2M→$1.5M, DT/DL $500K→$600K. Talent modifier no-data default 1.0→0.70. Star proxy widened (5★ 1.30, 3★ 0.80, 1-2★ 0.65). Graduated starter multiplier (rank 2=0.90, rank 3=0.80, rank 4=0.75, rank 5=0.70). Documented below. |

---

## 2. Master Formula

### 2.0 Override Check (ALWAYS FIRST)

```
IF player.is_override = true AND nil_overrides row exists:
    cfo_valuation = nil_overrides.annualized_value
    STOP — overrides bypass ALL other logic including the eligibility gate
```

Overrides represent verified market data or market consensus that supersedes any algorithm. A player with a verified $3M deal gets $3M regardless of depth chart status, production score, or any other factor.

### 2.1 Eligibility Gate (after override check)

```
IF college athlete AND is_on_depth_chart ≠ true:
    cfo_valuation = NULL (no valuation — profile only)
    STOP

IF HS recruit AND star_rating < 4:
    cfo_valuation = NULL
    STOP
```

### 2.2 College Athlete Formula

```
football_value = position_base_value(position)
                 × draft_premium(nfl_draft_projection)
                 × talent_modifier(production_score, star_rating, ea_rating)
                 × market_multiplier(team.market_multiplier)
                 × experience_multiplier(player_tag, class_year, hs_grad_year)
                 × depth_chart_rank_multiplier(depth_chart_rank, is_on_depth_chart, position,
                                               star_rating, class_year)

social_premium = min(total_followers × $1.00, $150,000)

cfo_valuation = max(int(football_value + social_premium), 10_000)
```

### 2.3 High School Recruit Formula

```
football_value = hs_base_value(composite_score, star_rating)
                 × hs_position_premium(position)
                 × market_multiplier(team.market_multiplier)
                 × experience_multiplier(player_tag, class_year, hs_grad_year)

social_premium = min(total_followers × $1.00, $150,000)

cfo_valuation = max(int(football_value + social_premium), 10_000)
```

The HS formula does NOT use: draft_premium, talent_modifier, depth_chart_rank_multiplier. These are college-only concepts.

---

## 3. College Athlete — Component Breakdown

### 3.1 Override Check

```python
if player["is_override"] is True:
    overrides = fetch nil_overrides rows where player_id = player["id"]
    if overrides exist:
        best = max(overrides, key=lambda r: r["annualized_value"])
        return best["annualized_value"]
    else:
        log.warning(f"Player {player['name']} has is_override=True but no nil_overrides row.")
        # Fall through to eligibility gate and algorithm
```

**Override data model:**
```
nil_overrides
├── player_id          UUID (FK → players)
├── name               TEXT
├── total_value         INTEGER (full reported deal, e.g. $12,000,000)
├── years              NUMERIC (contract length, e.g. 4)
├── annualized_value   INTEGER (total_value / years, e.g. $3,000,000)
├── source_name        TEXT (e.g. "Market Consensus", "The Athletic")
└── source_url         TEXT (verified article URL, or NULL if unverified)
```

**Source attribution rules:**
- `source_url` must be verified via HTTP request before storage — broken URLs are set to NULL
- Sources labeled "Market Consensus" indicate On3 algorithmic valuations without a specific article
- Sources with real article URLs are displayed as clickable links on the player profile
- The `apply_overrides.py` script validates URLs on ingestion and rejects 404s

Multiple rows per player allowed. Engine uses highest `annualized_value`. UI displays ALL sources.

---

### 3.2 Position Base Value

Average annualized NIL market value for a Power 4 starter at each position. Calibrated from ESPN's 2025 coaching survey (20+ GMs and agents), On3 GM interviews (Feb 2026), and The Athletic's market analysis. Recalibrated in V3.5 to reflect 2025-26 market growth.

```python
POSITION_BASE_VALUES = {
    "QB":   1_500_000,
    "OT":     800_000,
    "EDGE":   700_000,
    "DE":     700_000,
    "DT":     600_000,
    "DL":     600_000,
    "WR":     550_000,
    "CB":     500_000,
    "OG":     475_000,
    "C":      475_000,
    "IOL":    475_000,
    "OL":     475_000,
    "S":      450_000,
    "RB":     400_000,
    "TE":     325_000,
    "LB":     325_000,
    "K":      100_000,
    "P":      100_000,
    "ATH":    400_000,
    "LS":     100_000,
}

def position_base_value(position: str | None) -> int:
    if position is None:
        return 400_000
    return POSITION_BASE_VALUES.get(position.upper().strip(), 400_000)
```

---

### 3.3 Draft Premium

NFL draft projection as a **multiplier** on position base. Only activates when real data exists.

```python
def draft_premium(nfl_draft_projection: int | None) -> float:
    # Sentinel values treated as "no data"
    if nfl_draft_projection is None or nfl_draft_projection >= 500 or nfl_draft_projection == 0:
        return 1.0   # NO DATA → neutral

    if nfl_draft_projection <= 5:    return 2.5   # Top 5 pick
    elif nfl_draft_projection <= 15: return 1.9   # First round
    elif nfl_draft_projection <= 32: return 1.5   # Late first
    elif nfl_draft_projection <= 64: return 1.25  # Second round
    elif nfl_draft_projection <= 100: return 1.1  # Day 2
    elif nfl_draft_projection <= 180: return 1.0  # Mid-round
    else:                             return 0.9  # Late-round (181-499)
```

**Sentinel handling:** `999`, `0`, `None`, and any value `>= 500` are treated as "no data" → 1.0× neutral.

**Data source:** `python_engine/data/draft_projections.csv` from Drafttek consensus big board, imported via `populate_draft_projections.py`.

---

### 3.4 Talent Modifier (Production → EA Rating → Star Rating Fallback)

Three-tier talent assessment with fallback chain:

```python
def talent_modifier(production_score, star_rating, ea_rating=None):
    # Priority 1: production_score > 0 → use production tiers
    has_production = production_score is not None and float(production_score) > 0

    if has_production:
        ps = float(production_score)
        if ps >= 90:   return 1.4
        elif ps >= 75: return 1.2
        elif ps >= 50: return 1.0
        elif ps >= 25: return 0.65
        else:          return 0.40

    # Priority 2: EA rating exists → use EA OVR tiers (V3.4)
    if ea_rating is not None and int(ea_rating) > 0:
        ea = int(ea_rating)
        if ea >= 90:   return 1.4   # Elite
        elif ea >= 82: return 1.2   # Strong
        elif ea >= 75: return 1.0   # Average
        elif ea >= 68: return 0.65  # Below average
        else:          return 0.40  # Low

    # Priority 3: star rating proxy (widened band — V3.6b)
    star = star_rating or 0
    if star >= 5:    return 1.30
    elif star == 4:  return 1.0
    elif star == 3:  return 0.80
    elif star >= 1:  return 0.65
    else:            return 0.70  # no data → penalty (V3.6b)
```

**V3.4 change: EA rating fallback.** CFBD has no OL statistics, so all OL players previously fell through to the star_rating proxy. EA Sports College Football 26 OVR ratings (stored in `players.ea_rating`) now serve as an intermediate fallback between production and stars. EA OVR tiers are calibrated to roughly match production score tiers. Validation: Pearson r=0.640 between EA and production for players with both. Average EA is 77.8 vs average production 56.6 — EA skews higher. Position agreement rate: 46.3%.

**Calibration example (Drew Bobo, Georgia C):**
- No production → star fallback (3★ = 0.90×): $495K
- EA 86 → Strong tier (1.2×): $657K
- On3 valuation: $701K — gap closed from 42% to 7%

**Data sources:**
- Production: `calculate_production_scores.py` via CFBD API
- EA rating: `scrape_ea_ratings.py` → `populate_ea_ratings.py` via EA.com Next.js API
- Stars: `enrich_star_ratings.py` via CFBD recruiting API

---

### 3.5 Team Market Multiplier

Reflects the financial ecosystem around a program. Stored as `teams.market_multiplier`. Clamped to 0.8–1.3.

```python
def market_multiplier(team_market_multiplier: float | None) -> float:
    if team_market_multiplier is None:
        return 1.0
    return max(0.8, min(1.3, float(team_market_multiplier)))
```

**Typical values:**

| Tier | Range | Examples |
|------|-------|---------|
| Top SEC/Big Ten | 1.25–1.30 | Ohio State, Alabama, Texas, Michigan |
| Strong P4 | 1.15–1.25 | Oregon, USC, Notre Dame, LSU |
| Mid P4 | 1.0–1.15 | Iowa, TCU, Miami, Arizona State |
| Lower P4 | 0.9–1.0 | Vanderbilt, Wake Forest, Kansas |
| Top G5 | 0.85–0.95 | Boise State, Memphis, Liberty |
| Small G5/FCS | 0.80–0.85 | — |

---

### 3.6 Experience Multiplier (Monotonically Increasing)

Experience always increases value. The curve never decreases with more experience.

```python
COLLEGE_YOE_MAP = {
    1: 0.90,   # Freshman
    2: 1.00,   # Sophomore (baseline)
    3: 1.10,   # Junior
    4: 1.15,   # Senior
    5: 1.20,   # Super Senior / 5th year
}

CURRENT_YEAR = 2026  # Update annually

def experience_multiplier(player_tag, class_year, hs_grad_year):
    tag = (player_tag or "").strip()

    if tag == "High School Recruit":
        if hs_grad_year is not None:
            if hs_grad_year <= CURRENT_YEAR + 1:   # 2027 = HS senior
                return 0.80
            elif hs_grad_year == CURRENT_YEAR + 2:  # 2028 = HS junior
                return 0.35
            else:
                return 0.25  # 2029+ = HS underclassman
        return 0.75  # unknown HS grad year

    # College athlete
    if class_year is not None and class_year in COLLEGE_YOE_MAP:
        return COLLEGE_YOE_MAP[class_year]
    return 1.0  # unknown
```

**Full experience curve:**

| Level | Identifier | Multiplier |
|-------|-----------|------------|
| HS Underclassman | hs_grad_year = 2029+ | 0.25 |
| HS Junior | hs_grad_year = 2028 | 0.35 |
| HS Senior | hs_grad_year = 2027 | 0.80 |
| HS Senior (enrolling) | hs_grad_year = 2026 | 0.80 |
| College Freshman | class_year = 1 | 0.90 |
| College Sophomore | class_year = 2 | 1.00 |
| College Junior | class_year = 3 | 1.10 |
| College Senior | class_year = 4 | 1.15 |
| Super Senior | class_year = 5 | 1.20 |

---

### 3.7 Depth Chart Rank Multiplier (Position-Aware)

This is the most complex multiplier. It accounts for two things:
1. **Multi-starter positions** — OL has 5 starters, LB has 3, WR has 3, etc. The 3rd-best LB at Georgia is still a starter, not a "third-stringer."
2. **Split tiers** — single-starter positions (QB, RB, TE) use steeper backup discounts than multi-starter positions (OL, WR, DL, LB, CB, S).

```python
POSITION_STARTER_COUNTS = {
    "QB": 1, "RB": 1, "TE": 2, "K": 1, "P": 1, "LS": 1,  # TE changed from 1→2 in V3.4
    "WR": 3,
    "OL": 5, "OT": 5, "OG": 5, "C": 5, "IOL": 5,
    "EDGE": 2, "DE": 2,
    "DT": 2, "DL": 2,
    "LB": 3,
    "CB": 2,
    "S": 2,
    "ATH": 1,
}

SINGLE_STARTER_POSITIONS = {"QB", "RB", "K", "P", "LS", "ATH"}  # TE removed in V3.4

def depth_chart_rank_multiplier(depth_chart_rank, is_on_depth_chart, position):
    if not is_on_depth_chart:
        return 0.12  # fallback — shouldn't reach here due to gate

    pos = (position or "").upper().strip()
    starter_count = POSITION_STARTER_COUNTS.get(pos, 1)
    is_single = pos in SINGLE_STARTER_POSITIONS

    # Graduated starter multiplier (V3.6b)
    STARTER_GRADIENT = {1: 1.0, 2: 0.90, 3: 0.80, 4: 0.75, 5: 0.70}

    if depth_chart_rank is None:
        return 0.55  # unknown rank

    if depth_chart_rank <= starter_count:
        if pos in SINGLE_STARTER_POSITIONS:
            return 1.0  # single-starter: rank 1 always 1.0
        return STARTER_GRADIENT.get(depth_chart_rank, 0.70)  # graduated

    backup_depth = depth_chart_rank - starter_count

    if is_single:
        # Steeper for single-starter positions
        if backup_depth == 1:   return 0.35
        elif backup_depth == 2: return 0.20
        else:                   return 0.12
    else:
        # Softer for multi-starter positions
        if backup_depth == 1:   return 0.55
        elif backup_depth == 2: return 0.40
        else:                   return 0.25
```

**Examples:**

| Player | Position | Rank | Starter Count | Relative | Multiplier |
|--------|----------|------|---------------|----------|------------|
| QB1 | QB | 1 | 1 | Starter | 1.0× |
| QB2 | QB | 2 | 1 | 1st backup (single) | 0.35× |
| QB3 | QB | 3 | 1 | 2nd backup (single) | 0.20× |
| WR1 | WR | 1 | 3 | Starter | 1.0× |
| WR3 | WR | 3 | 3 | Starter | 1.0× |
| WR4 | WR | 4 | 3 | 1st backup (multi) | 0.55× |
| OL5 | OL | 5 | 5 | Starter | 1.0× |
| OL6 | OL | 6 | 5 | 1st backup (multi) | 0.55× |
| LB3 | LB | 3 | 3 | Starter | 1.0× |
| LB4 | LB | 4 | 3 | 1st backup (multi) | 0.55× |
| CB2 | CB | 2 | 2 | Starter | 1.0× |
| CB3 | CB | 3 | 2 | 1st backup (multi) | 0.55× |

**V3.4 change: TE is now a 2-starter position.** Most modern offenses use 12 personnel (2 TE sets) regularly. TE rank 2 is now valued as a starter (1.0×) instead of a single-starter backup (0.35×).

**Calibration source:** Stress-tested against On3 Georgia roster valuations. Starters align at 0.94× On3, non-starters average 0.68× (improved from 0.36× before position-aware update). See Section 10 for details.

---

### 3.7.1 Recruiting Pedigree Floor (V3.4)

Elite recruits who haven't had a full opportunity to earn playing time keep a minimum depth chart multiplier. This prevents their value from being destroyed by a low depth chart rank when their recruiting pedigree IS the primary value signal.

```python
# Applied AFTER computing the raw depth chart multiplier:
if class_year <= 3 and star_rating >= 5:
    multiplier = max(raw_multiplier, 1.0)   # 5★ underclassmen: no penalty
elif class_year <= 3 and star_rating == 4:
    multiplier = max(raw_multiplier, 0.45)  # 4★ underclassmen: modest floor
# class_year >= 4 OR star_rating <= 3: no floor, raw multiplier applies
```

**Rules:**
- 5★, class_year ≤ 3 → floor 1.0× (no depth chart penalty at all)
- 4★, class_year ≤ 3 → floor 0.45×
- class_year ≥ 4 (seniors/5th years): no floor — they've had time to earn their spot
- star_rating ≤ 3: no floor — only elite recruits get protection
- The floor is a MAX operation: if the raw multiplier is already above the floor, the raw multiplier is used

**Rationale:** A 5-star sophomore sitting behind a senior starter still has enormous market value due to NFL draft potential and program importance. The depth chart ranking reflects current playing time, not market value. By class_year 4+, a player has had sufficient opportunity to prove themselves — if they're still a deep reserve, the market reflects that.

---

### 3.8 Social Premium

$1 per follower, hard cap at $150,000.

```python
SOCIAL_CAP = 150_000

def social_premium(total_followers: int | None) -> float:
    if total_followers is None or total_followers <= 0:
        return 0.0
    return min(float(total_followers) * 1.0, float(SOCIAL_CAP))
```

---

## 4. High School Recruit — Component Breakdown

### 4.1 HS Base Value (Composite-Driven)

Composite score is the primary talent signal for HS recruits, replacing production/draft data.

```python
HS_COMPOSITE_TIERS = [
    (99.0, 800_000),   # Elite 5-star
    (98.0, 575_000),   # High 5-star
    (97.0, 375_000),   # Mid 5-star
    (96.0, 275_000),   # Low 5-star
    (95.0, 200_000),   # High 4-star
    (94.0, 175_000),   # Mid 4-star
    (93.0, 150_000),   # Low 4-star
    (91.0, 125_000),   # 4-star
    (89.0, 100_000),   # Low 4-star
]

HS_STAR_FALLBACK = {
    5: 450_000,
    4: 150_000,
}

def hs_base_value(composite_score, star_rating):
    if composite_score is not None and float(composite_score) >= 89.0:
        cs = float(composite_score)
        for threshold, value in HS_COMPOSITE_TIERS:
            if cs >= threshold:
                return value

    star = star_rating or 0
    return HS_STAR_FALLBACK.get(star, 100_000)
```

**Calibration source:** On3 HS Top 100 valuations. The 97-98 composite tier aligns at 0.92× On3, 96-97 at 1.11×. Overall MAPE: 34.1%. See Section 10.

---

### 4.2 HS Position Premium

Different from college position base values. Reflects the HS recruiting market where QBs and OTs command outsized premiums.

```python
HS_POSITION_PREMIUMS = {
    "QB":   2.0,
    "OT":   1.5,
    "OL":   1.2,
    "OG":   1.2,
    "C":    1.2,
    "IOL":  1.2,
    "WR":   1.1,
    "EDGE": 1.1,
    "DE":   1.1,
    "DT":   1.1,
    "DL":   1.1,
    "CB":   1.05,
    "LB":   1.0,
    "S":    1.0,
    "TE":   0.9,
    "RB":   0.85,
    "ATH":  1.0,
    "K":    0.5,
    "P":    0.5,
    "LS":   0.5,
}
```

**Calibration source:** The Athletic's Dec 2025 survey of GMs and agents on HS recruit compensation. "Five-star QBs typically get $750K–$1M annually." "700K is the number for a premium tackle."

---

### 4.3 Shared Components

HS recruits use the same **market_multiplier** (Section 3.5), **experience_multiplier** (Section 3.6), and **social_premium** (Section 3.8) as college athletes.

The HS formula does NOT use: position_base_value, draft_premium, talent_modifier, or depth_chart_rank_multiplier.

---

### 4.4 HS-to-College Transition

When a recruit enrolls and begins playing:
1. Their `player_tag` changes from "High School Recruit" to "College Athlete"
2. Their `class_year` is set to 1 (Freshman)
3. They enter the college formula path
4. Without production data, the talent_modifier falls back to star_rating (Section 3.4)
5. As production_score is populated from CFBD stats, the formula naturally transitions to production-based valuation
6. Their depth_chart_rank determines the multiplier once they appear on Ourlads depth charts

This transition happens automatically — no manual intervention required.

---

## 5. Sentinel Value Reference

| Field | Sentinel Values | Treatment |
|-------|----------------|-----------|
| `nfl_draft_projection` | `NULL`, `0`, `≥ 500` (including `999`) | → 1.0× neutral |
| `production_score` | `NULL`, `0`, `0.00` | → fall to star_rating proxy |
| `class_year` | `NULL` | → 1.0× neutral |
| `total_followers` | `NULL`, `0` | → $0 social premium |
| `star_rating` | `NULL`, `0` | → 1.0× neutral (when used as fallback) |
| `market_multiplier` | `NULL` | → 1.0× neutral |
| `hs_grad_year` | `NULL` | → 0.75× (conservative HS default) |
| `composite_score` | `NULL` | → fall to star_rating fallback |
| `ea_rating` | `NULL`, `0` | → skip to star_rating proxy |

---

## 6. Edge Cases & Business Rules

| Scenario | Behavior |
|----------|----------|
| Override player not on depth chart | Override still applies — overrides bypass eligibility gate |
| Override player departed | Override applies. Departure status is tracked separately via `roster_status`. |
| `is_override = true` but no `nil_overrides` row | Log warning, fall through to algorithm (if eligible) |
| Multiple `nil_overrides` rows for same player | Use highest `annualized_value`. Display all sources in UI. |
| `cfo_valuation` < $10,000 (from algorithm) | Floor at $10,000 |
| `cfo_valuation` > $10,000,000 | No ceiling |
| College athlete, `is_on_depth_chart = false` or `NULL` | `cfo_valuation = NULL`. Profile visible, no dollar figure. |
| HS recruit, `star_rating < 4` or `NULL` | `cfo_valuation = NULL`. |
| `status = "Medical Exemption"` | Still calculate if eligible. UI shows badge. |
| Position has whitespace/mixed case | Normalize: `position.upper().strip()` |
| `market_multiplier` outside 0.8–1.3 | Clamp to boundaries |
| Duplicate player records (HS + College) | Delete the HS record — player has enrolled |
| `name IS NULL` | Reject — NOT NULL constraint on players.name |

---

## 7. Roster Management

### 7.1 Roster Status

Players have a `roster_status` field tracking their relationship to their team:

| Status | Meaning |
|--------|---------|
| `active` | Currently on the team roster |
| `departed_transfer` | Entered transfer portal, left the team |
| `departed_draft` | Declared for NFL Draft |
| `departed_graduated` | Exhausted eligibility or graduated |
| `departed_other` | Left for other reasons |

**Rules:**
- Only `active` players appear in team roster views and payroll calculations
- Departed players retain their records (not deleted) for historical reference
- Override players are NEVER auto-flagged as departed — manual review required
- HS recruits are not subject to departure flagging
- The `sync_roster_status.py` script uses CFBD transfer portal data and roster cross-referencing to flag departures

### 7.2 Team Views

**Team roster page** (`app/teams/[id]/page.tsx`):
- Active college athletes in the main roster section
- Incoming 2026 recruits (hs_grad_year = 2026) in a separate "Incoming Recruits" section
- Departed players in a collapsed/grayed section
- 2027 and 2028 commits do NOT appear on team pages — they appear on the Futures page only

**Team summary view** (`team_roster_summary`):
- `total_roster_value`: sum of active college athlete valuations
- `incoming_recruit_value`: sum of 2026 HS recruit valuations
- `total_program_value`: active + incoming 2026 recruits
- `departed_count`: count of departed players

### 7.3 Depth Chart Ranking

Depth chart ranks are assigned by `sync_depth_charts.py` using production_score as the primary heuristic:
1. For each team + position group, rank players by production_score descending
2. Star rating breaks ties (higher = better rank)
3. Class year breaks further ties (more experienced = better rank)
4. Only players with `is_on_depth_chart = true` receive ranks

This heuristic approximates Ourlads depth chart ordering. For more accurate rankings, update from actual Ourlads data when available.

---

## 8. Data Pipelines

### 8.1 Main Valuation Script

**Script:** `python_engine/calculate_cfo_valuations.py`
**Auth:** `SUPABASE_SERVICE_ROLE_KEY` via `python_engine/supabase_client.py`
**Frequency:** After any data pipeline runs, or daily at 2 AM ET

**Execution order:**
1. Fetch all players with joined team data
2. Fetch all nil_overrides (one query)
3. For each player:
   a. Override check → if override, use annualized_value
   b. Eligibility gate → if ineligible, set cfo_valuation = NULL
   c. Route to HS or College formula based on player_tag
   d. Compute valuation
4. Batch upsert cfo_valuation + last_updated
5. Log summary

### 8.2 Production Scores

**Script:** `python_engine/calculate_production_scores.py`
**Source:** CFBD API (`/stats/player/season`)
**Coverage:** 984 of ~1,200 depth-chart players with cfbd_id
**Frequency:** Weekly during season, monthly in offseason

Position-specific composite scoring (0-100) using percentile ranking against all FBS players.

### 8.3 Draft Projections

**Script:** `python_engine/populate_draft_projections.py`
**Source:** CSV from Drafttek consensus big board (`python_engine/data/draft_projections.csv`)
**Coverage:** 79 players with projections
**Frequency:** Monthly during draft season

### 8.4 Recruiting Class Import

**Script:** `python_engine/import_recruiting_class.py`
**Source:** CSV from 247Sports composite rankings
**Usage:** `python import_recruiting_class.py --year 2027 --min-stars 4 --csv data/recruits_2027_full.csv`
**Coverage:** 2026: 480 recruits, 2027: 470 recruits, 2028: 160 recruits

### 8.5 Roster Status Sync

**Script:** `python_engine/sync_roster_status.py`
**Source:** CFBD transfer portal + roster endpoints
**Flags:** `--dry-run` for preview without changes
**Protection:** Override players are never auto-flagged

### 8.6 Depth Chart Sync

**Script:** `python_engine/sync_depth_charts.py`
**Source:** Production-score-based heuristic (future: Ourlads scraping)
**Writes:** `depth_chart_rank` for all depth-chart players

### 8.7 Override Management

**Identify candidates:** `python_engine/identify_override_candidates.py`
**Apply overrides:** `python_engine/apply_overrides.py`
**CSV input:** `python_engine/data/approved_overrides.csv`
**URL verification:** `python_engine/verify_override_urls.py`

**Override workflow:**
1. Run `identify_override_candidates.py` → flags players where On3 >= 2× our value
2. Review HIGH confidence candidates manually
3. Add approved overrides to `approved_overrides.csv` (name, value, years, source)
4. Run `apply_overrides.py` → creates nil_overrides rows, sets is_override = true
5. Run `calculate_cfo_valuations.py` → overrides take effect

**Source URL rules:**
- URLs are verified via HTTP request before storage
- Broken URLs (404s) are set to NULL
- "Market Consensus" source = On3 algorithmic value, no article URL
- Verified article URLs display as clickable links on player profiles
- Unverified sources display as non-clickable text labels

### 8.8 HS Graduation Year

**Script:** `python_engine/populate_hs_grad_year.py`
**Coverage:** All 1,110 HS recruits populated

---

## 9. UI Components

| UI Location | What It Shows | Data Source |
|-------------|---------------|-------------|
| Homepage PlayerTable | Top players by cfo_valuation (active only) | `players` filtered by roster_status = active |
| Player Profile — header | cfo_valuation or "Not on depth chart" | `players.cfo_valuation` |
| Player Profile — College breakdown | Position base, draft, talent, market, experience, depth chart role, social | Recomputed via `lib/valuation.ts` |
| Player Profile — HS breakdown | Composite base, position premium, market, experience, social | Recomputed via `lib/valuation.ts` |
| Player Profile — Override | "Verified Market Report" with sources | `nil_overrides` join |
| Player Profile — Ineligible | "Not on active depth chart" message | When `cfo_valuation IS NULL` |
| Team Roster | Active players + incoming 2026 recruits + departed section | `players` filtered by team + status |
| Team Summary | Payroll breakdown: active + recruit + total | `team_roster_summary` view |
| CapSpaceBoard | Team payroll grid | `team_roster_summary` view |
| Futures Page | HS recruits by class | `players` WHERE player_tag = 'High School Recruit' |
| Methodology | Public explanation of approach | `app/methodology/page.tsx` |

---

## 10. Calibration & Validation

### 10.1 College Athletes — On3 Georgia Comparison (V3.5)

Stress-tested against 26 Georgia players with On3 subscriber data:

| Metric | V3.3 | V3.5 |
|--------|------|------|
| Average CFO/On3 | 0.73× | 2.20× |
| Starters (rank 1) | 0.94× | 1.07–1.41× |
| Drew Bobo (C) journey | $131K | $830K (On3: $701K = 1.18×) |
| Earnest Greene III (OT) | $552K | $969K (On3: $685K = 1.41×) |
| KJ Bolden (DB) | $553K | $712K (On3: $559K = 1.27×) |

**Note:** V3.5 base recalibration pushed starters above On3 on average. This is intentional — On3 valuations include non-football brand deals and social-media-weighted adjustments that compress star player values. Our football-first model correctly assigns higher values to high-production starters.

### 10.2 HS Recruits — On3 Top 50 Comparison (V3.5)

Stress-tested against 49 HS recruits from On3 data:

| Metric | Value |
|--------|-------|
| Average CFO/On3 | 1.08× |
| Median CFO/On3 | 1.00× |
| Within 40% of On3 | 31/49 (63%) |
| Best calibrated | Jared Curtis (QB, Vanderbilt): exactly 1.00× |
| Under 0.6× | 10 players |
| Over 1.4× | 8 players |

### 10.3 ESPN Market Validation (V3.5)

Position base values validated against market data:

| Position | Market Starter Range | Our Starter Avg | Assessment |
|----------|---------------------|----------------|------------|
| QB | $1.5M–$3M | $2.0M+ | ✅ Within range |
| OT | $600K–$1M | $800K+ | ✅ Within range |
| WR | $500K–$1M | $600K+ | ✅ Within range |
| DE/EDGE | $800K–$1.5M | $1.0M+ | ✅ Within range |
| LB | $300K–$600K | $450K+ | ✅ Within range |
| K/P | $50K–$200K | $117K | ✅ Within range |

### 10.4 V3.6b Team Calibration — Comparison CSV Workflow (April 2026)

Three teams calibrated via the On3 comparison CSV workflow: user pastes On3 NIL data, script generates side-by-side CSV (CFO vs On3), user fills Override Value column, overrides ingested to `nil_overrides`.

**Texas:** 9 overrides applied. Key players: Arch Manning ($6M), Cam Coleman ($3M), Ryan Wingo ($1.5M). Michael Terry III case study: $720K → $423K after enrichment (star_rating, class_year, EA rating populated via improved name matching).

**Texas Tech:** 7 overrides applied. Key finding: Brendan Sorsby (QB1, RS-SR) was missing from DB — found on Texas as a stale record, moved to Texas Tech, production_score 89.0 populated via CFBD. Pre-enrichment $997K → post-enrichment $2.05M (algorithmic) → override $3.2M.

**Georgia:** 32 overrides applied (including non-On3 players from owner domain knowledge). Juan Gaston position fix: OL ($475K base) → OT ($800K base), valuation $539K → $905K.

**OL→OT Position Mapping Fix:** `sync_ourlads_depth_charts.py` was mapping all Ourlads offensive line positions (LT, LG, C, RG, RT) to generic "OL" ($475K base). Tackles should be "OT" ($800K base). Fix: LT/RT → OT, LG/RG/C → OL. Impact: 178 tackles corrected across all 68 teams, $93.3M in recovered roster value.

**66 total overrides in system:** 18 original Market Consensus + 9 Texas + 7 Texas Tech + 32 Georgia.

### 10.5 Comparison CSV Workflow

Ongoing calibration process for any team:

1. Paste On3 team NIL rankings data into a `generate_{team}_comparison.py` script
2. Script queries Supabase for team roster, fuzzy-matches On3 names using `name_utils.fuzzy_match_player`
3. Outputs CSV with columns: Player, Position, CFO Valuation, On3 Valuation, Override Value
4. Owner fills Override Value column for players needing market corrections
5. Overrides ingested via direct Supabase upsert to `nil_overrides` + `is_override=true`
6. Run `calculate_cfo_valuations.py` to apply

Active CSVs: `texas_comparison.csv`, `texas_tech_comparison.csv`, `georgia_comparison.csv`

---

## 11. Database Schema Notes

### Key columns

| Column | Type | Notes |
|--------|------|-------|
| `cfo_valuation` | INTEGER | NULL for ineligible players |
| `depth_chart_rank` | INTEGER | 1 = starter at position. Position-aware interpretation. |
| `is_on_depth_chart` | BOOLEAN | Gate for college athlete eligibility |
| `is_override` | BOOLEAN | True = use nil_overrides value |
| `roster_status` | TEXT | 'active', 'departed_transfer', 'departed_draft', 'departed_graduated', 'departed_other' |
| `class_year` | INTEGER | 1-5 scale. CHECK constraint. |
| `hs_grad_year` | INTEGER | 2026, 2027, 2028. HS recruits only. |
| `production_score` | NUMERIC | 0-100. From CFBD stats pipeline. |
| `ea_rating` | INTEGER | 0-99. EA Sports CFB 26 OVR. From `scrape_ea_ratings.py`. |
| `nfl_draft_projection` | INTEGER | 1-260 projected pick. From Drafttek CSV. |
| `composite_score` | NUMERIC | 247Sports/On3 composite. HS recruits primarily. |
| `player_tag` | TEXT | "College Athlete" or "High School Recruit" |

### Constraints

- `players.name` NOT NULL
- `players.class_year` CHECK (class_year BETWEEN 1 AND 5)

---

## 12. TypeScript Mirror: lib/valuation.ts

Must stay **exactly in sync** with `calculate_cfo_valuations.py`. Both implementations are cross-validated by 265 unit tests (134 TypeScript, 131 Python) that verify identical outputs for identical inputs.

**College exports:**
- `isEligibleForValuation(playerTag, isOnDepthChart, starRating, isOverride): boolean`
- `getPositionBaseValue(position): { label, value }`
- `getDraftPremium(nflDraftProjection): { label, multiplier }`
- `getTalentModifier(productionScore, starRating, eaRating?): { label, modifier }`
- `getMarketMultiplier(teamMarketMultiplier): number`
- `getExperienceMultiplier(playerTag, classYear, hsGradYear): { label, multiplier }`
- `getDepthChartRankMultiplier(depthChartRank, isOnDepthChart, position?, starRating?, classYear?): { label, multiplier }`
- `calculateSocialPremium(totalFollowers): number`
- `calculateCfoValuation(player, teamMarketMultiplier): { breakdown, total } | null`

**HS exports:**
- `getHsBaseValue(compositeScore, starRating): { label, value }`
- `getHsPositionPremium(position): { label, multiplier }`

---

## 13. Testing

**TypeScript:** 134 tests in `lib/__tests__/valuation.test.ts`
**Python:** 131 tests in `python_engine/tests/test_valuations.py`

Tests cover:
- Every function with edge cases
- Sentinel value handling
- Multi-starter position logic (including TE=2 starter)
- HS composite tiers and fallbacks
- EA rating fallback tiers (production beats EA, EA beats star, label verification)
- Recruiting pedigree floor (5★/4★ underclass floors, senior no-floor, starter irrelevance)
- Full integration tests matching spec examples
- Cross-validation: identical-input tests verify Python = TypeScript output

**Run:** `npm test` (TypeScript) and `cd python_engine && python -m pytest tests/ -v` (Python)

---

## 14. Future Enhancements

- **Temporal decay:** Discount production_score for stats older than 1 season
- **Conference strength adjustment:** Nested within market_multiplier
- **Transfer portal premium:** Short-term valuation spike for portal entrants
- **Revenue sharing recalibration:** Position base values updated annually as $20.5M cap grows 4%/year
- **Admin UI for overrides:** Web form to input total_value, years, sources
- ~~**Ourlads depth chart scraping:**~~ ✅ DONE (V3.4) — `sync_ourlads_depth_charts.py` scrapes real Ourlads data
- ~~**OL production scores:**~~ ✅ DONE (V3.4) — EA rating fallback in talent_modifier. Drew Bobo: $131K → $657K (7% gap to On3)
- ~~**Composite score as HS production proxy:**~~ ✅ DONE (V3.3)
- **Snaps played:** Column exists, not yet populated or used in formula
- **South Carolina depth charts:** Team needs Ourlads data populated for valuations to work
- **Social media data refresh:** Tennessee followers are sparse — need On3 social scrape for Tennessee
- **PFF grade integration:** Premium data source for OL/DL performance metrics
- **2028 class monitoring:** Watch for On3 calibration drift as 2028 class approaches signing day
