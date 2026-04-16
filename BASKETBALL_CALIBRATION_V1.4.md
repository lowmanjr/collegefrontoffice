# CFO Basketball Valuation Calibration — V1.4 Reference

> **Status:** Reference document (V1.4) | **Last Updated:** April 16, 2026
> **Audience:** Developers, future calibration sessions, internal team only
> **PROPRIETARY — Do not share externally or commit to a public repo.**

---

## 1. Purpose

This document captures a calibration snapshot comparing CFO valuations against On3's publicly reported NIL Valuations for the top ~100 college basketball players (April 2026). It serves as reference data for future formula adjustments and as a benchmark when evaluating V1.5+ changes.

**Key insight:** CFO and On3 measure fundamentally different things. Documenting where they diverge and why helps us evaluate whether future formula changes move us toward or away from market reality.

---

## 2. Methodology

- **Source:** On3 Top 100 College Basketball NIL Valuations (public rankings, April 2026)
- **Sample:** 89 of 100 On3 players fell within CFO's 82-team tracked universe
- **Matched:** 72 of 89 successfully matched in the CFO database (81% match rate)
- **Unmatched reasons:** Name format differences, mid-season transfers, players no longer on current roster
- **CFO state at time of comparison:** V1.4 engine, 82 teams, 848 valued players, 5 active overrides

---

## 3. Top-Tier Results (On3 $2M+)

The tightest cluster. Formula + overrides align well with market at the top.

| Player | School | On3 | CFO | Delta | % |
|---|---|---|---|---|---|
| AJ Dybantsa | BYU | $4,200,000 | $4,400,000 | +$200,000 | +5% |
| JT Toppin | Texas Tech | $2,800,000 | $1,444,014 | -$1,355,986 | -48% |
| Cameron Boozer | Duke | $2,200,000 | $2,200,000 | +$0 | 0% |
| Denzel Aberdeen | Florida | $2,200,000 | $1,919,640 | -$280,360 | -13% |
| Morez Johnson Jr. | Michigan | $2,000,000 | $2,000,000 | +$0 | 0% |
| Jayden Quaintance | Kentucky | $2,000,000 | $2,000,000 | +$0 | 0% |
| Yaxel Lendeborg | Michigan | $2,000,000 | $2,415,982 | +$415,982 | +21% |
| Milan Momcilovic | Iowa State | $2,000,000 | $1,646,568 | -$353,432 | -18% |
| Massamba Diop | Arizona State | $2,000,000 | $769,824 | -$1,230,176 | -62% |
| Caleb Wilson | North Carolina | $1,900,000 | $2,722,720 | +$822,720 | +43% |

**Average delta at top tier: ~-15%.** Overrides anchor the very top (Dybantsa, Boozer, Quaintance, Morez Johnson). The formula tracks the market within a reasonable band for players with draft projections.

**Outliers:**
- **JT Toppin (-48%):** High On3 due to social/brand value as a marquee transfer. CFO formula doesn't capture transfer narrative premium.
- **Massamba Diop (-62%):** On3 likely values incoming hype and Arizona State program visibility. CFO sees star tier with no draft projection.
- **Caleb Wilson (+43%):** CFO rewards franchise production (19.8 ppg) + draft #4 premium (3.50x). On3 may lag behind recent draft board risers.

---

## 4. Mid-Tier Results (On3 $1M–$2M)

Mixed alignment. Some tight matches, some significant divergences.

### Tight Matches (within +/-15%)

| Player | School | On3 | CFO | Delta % |
|---|---|---|---|---|
| Braden Smith | Purdue | $1,700,000 | $1,625,183 | -4% |
| Isaiah Johnson | Colorado | $1,300,000 | $1,265,616 | -3% |
| Stefan Vaaks | Providence | $1,300,000 | $1,172,490 | -10% |
| Neoklis Avdalas | Virginia Tech | $1,200,000 | $1,045,440 | -13% |
| Denzel Aberdeen | Florida | $2,200,000 | $1,919,640 | -13% |
| Ebuka Okorie | Stanford | $1,200,000 | $1,297,296 | +8% |
| Dedan Thomas | LSU | $1,200,000 | $1,297,296 | +8% |
| Kingston Flemings | Houston | $1,500,000 | $1,710,720 | +14% |
| Markus Burton | Notre Dame | $1,200,000 | $1,368,576 | +14% |

### Significant Divergences

**CFO under On3:**
| Player | School | On3 | CFO | Delta % | Likely Reason |
|---|---|---|---|---|---|
| Mouhamed Sylla | Georgia Tech | $1,500,000 | $484,704 | -68% | Starter tier, no draft — On3 values incoming transfer hype |
| Eric Reibe | UConn | $1,100,000 | $440,640 | -60% | Rotation tier (6.8 ppg) — On3 values UConn brand premium |
| Samet Yigitoglu | SMU | $1,400,000 | $661,567 | -53% | Star tier, no draft — On3 values international profile |
| David Punch | TCU | $1,800,000 | $862,488 | -52% | Star tier, no draft — On3 values social reach |
| Magoon Gwath | SDSU | $1,100,000 | $551,760 | -50% | Starter tier at low-multiplier school |

**CFO over On3:**
| Player | School | On3 | CFO | Delta % | Likely Reason |
|---|---|---|---|---|---|
| Keaton Wagler | Illinois | $1,500,000 | $2,313,360 | +54% | Franchise + draft #5 (3.50x) — draft premium drives CFO up |
| Nate Ament | Tennessee | $1,200,000 | $1,808,664 | +51% | Franchise + draft #8 (2.60x) + strong market multiplier |
| Silas Demary Jr. | UConn | $1,100,000 | $1,599,672 | +45% | Star tier + strong PER at high-multiplier school |
| Thomas Haugh | Florida | $1,100,000 | $2,162,160 | +97% | Franchise + draft #13 (2.60x) — CFO draft premium is steep |
| Brayden Burries | Arizona | $1,400,000 | $1,877,616 | +34% | Star tier + draft #10 (2.60x) |

---

## 5. Lower-Tier Results (On3 $500K–$1M) — CFO Systematically Higher

This is the most important finding. For proven producers on non-blue-blood programs, CFO consistently values higher than On3.

| Player | School | On3 | CFO | Delta % | Role | PPG |
|---|---|---|---|---|---|---|
| Graham Ike | Gonzaga | $589,000 | $1,972,542 | +235% | franchise | 19.7 |
| Bruce Thornton | Ohio State | $675,000 | $2,076,360 | +208% | franchise | 20.2 |
| Ja'Kobi Gillespie | Tennessee | $812,000 | $2,160,576 | +166% | franchise | 18.0 |
| Donovan Dent | UCLA | $620,000 | $1,620,432 | +161% | franchise | 13.5 |
| Boogie Fland | Florida | $718,000 | $1,655,280 | +131% | franchise | 11.6 |
| Andrej Stojakovic | Illinois | $640,000 | $1,347,192 | +110% | star | 13.4 |
| Labaron Philon Jr. | Alabama | $923,000 | $1,858,427 | +101% | franchise | 21.7 |
| Jeremy Fears Jr. | Michigan State | $906,000 | $1,805,760 | +99% | franchise | 15.7 |
| Darius Acuff Jr. | Arkansas | $973,000 | $1,896,180 | +95% | franchise | 22.9 |
| Tyler Tanner | Vanderbilt | $704,000 | $1,328,184 | +89% | franchise | 19.1 |

**Pattern:** Franchise-tier production (2.20x role multiplier) + high PER (1.30x talent modifier) + strong market multiplier produces large valuations that On3 doesn't match. All 10 are franchise-tier players with 13+ ppg.

---

## 6. Root Cause Analysis

### CFO higher at bottom tier — why?

Our formula rewards production. A 19.7 ppg senior at Gonzaga with elite PER gets franchise tier (2.20x) + elite talent modifier (1.30x) + Gonzaga's 1.14x market multiplier. On3's market-based methodology says actual NIL earning power is much lower because:

- Limited social reach (no national profile despite production)
- No NBA draft stock (one-way production bump ceiling)
- Non-blue-blood program NIL pool is smaller
- Senior players don't get "brand-building" premium since they're leaving soon

### CFO lower at top tier — why?

On3 captures brand/endorsement/social media value for high-profile transfers that CFO's additive social premium doesn't fully model. JT Toppin ($2.8M On3 vs $1.4M CFO) is likely boosted by social following and marquee-transfer narrative that our formula doesn't weight heavily enough.

### Where they agree

Draft-projected players on Power 4 programs with strong production align well. The formula's combined_premium (max of draft and role) produces values that track market expectations when both signals are present:

- Braden Smith (Purdue, #45): -4%
- Isaiah Johnson (Colorado): -3%
- Zoom Diallo (Washington): -1%
- Jalen Haralson (Notre Dame): +1%
- Keanu Dawes (Utah): +2%

---

## 7. Interpretation

CFO and On3 measure different things by design:

- **CFO is closer to "what a player *should* be worth based on production and role."** This is an idealized valuation anchored to role, production, and draft stock.
- **On3 leans toward "what a player *would* actually be paid in the current NIL market."** This captures marketability, social reach, and brand effects.

Neither is wrong — they're complementary signals. The divergence pattern is informative, not a defect.

---

## 8. Candidate Adjustments for V1.5 (Not Implemented)

These are noted for future consideration. **None should be implemented without additional market anchors (more overrides, reported deals):**

1. **Cap franchise tier for non-drafted players.** A 2.20x franchise multiplier plus 1.30x elite talent plus strong market multiplier compounds to very large values. For players with no draft projection, consider capping combined_premium at star tier (1.65x).

2. **Senior/graduate multiplier review.** Current 1.10x/1.15x may be too high for players without pro stock. Their NIL earning ceiling is naturally limited because they're one-and-done at the college level.

3. **Social premium weight.** The current tiered additive social premium ($0-$150K) underweights players with massive social followings relative to their on-court role. Consider multiplicative weighting for very large social audiences.

4. **Blue-blood inflation watch.** Market multiplier applies uniformly across the roster. Bench players at Kentucky/Duke/Kansas may be overvalued relative to market reality. Future refinement could taper market multiplier for non-rotation players.

---

## 9. Calibration Confidence

**High confidence in formula at the top** (overrides + draft premium anchor within 15-20% of market).

**Medium confidence at mid-tier** (formula diverges up or down depending on player profile; no systematic bias).

**Lower confidence at bottom tier** (formula consistently higher than market for proven non-draftees on strong teams).

**Action:** Do not adjust V1.4 formula based on this snapshot alone. Revisit when:
- Override count grows from 5 to 20-30 across multiple schools
- More reported deal data becomes available
- Next season produces roster turnover for a second calibration point

---

## 10. Data Notes

- **Comparison date:** April 16, 2026
- **On3 methodology:** Public NIL Valuations, updated weekly
- **CFO snapshot state:** V1.4 engine, post-82-team expansion
- **Unmatched players (17):** Primarily name format mismatches and recent transfers
- **Out-of-universe players (11):** On3 top 100 players at schools not in CFO's 82-team universe (Saint Mary's, Austin Peay, Boise State, Mercer, USF, Toledo, New Mexico, College of Charleston, Bradley, Sacramento State, Davidson)

---

## 11. Related Documents

- `BASKETBALL_VALUATION_ENGINE.md` — Formula specification (V1.4)
- `BASKETBALL_OPERATIONS.md` — Pipeline runbook
- `python_engine/data/basketball_approved_overrides.csv` — Active market anchors
