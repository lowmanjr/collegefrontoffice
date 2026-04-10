-- ============================================================
-- Basketball Schema Migration
-- Mirrors football tables (teams, players, nil_overrides, player_events)
-- with basketball-specific columns. Intentionally separate tables
-- to allow independent market_multiplier, cap values, and position sets.
-- ============================================================

-- ------------------------------------------------------------
-- basketball_teams
-- Same structure as teams, but market_multiplier is calibrated
-- per-sport (e.g. Duke basketball >> Duke football for NIL).
-- estimated_nil_pool replaces estimated_cap_space to reflect
-- the smaller roster economics of basketball.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS basketball_teams (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  university_name     TEXT NOT NULL,
  conference          TEXT,
  logo_url            TEXT,
  market_multiplier   NUMERIC(4,3) NOT NULL DEFAULT 1.000,
  estimated_nil_pool  INTEGER DEFAULT 2000000,
  active_payroll      INTEGER DEFAULT 0,
  slug                TEXT UNIQUE,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------
-- basketball_players
-- Key differences from football players table:
--   rotation_status  : 'starter'|'rotation'|'bench'|'inactive'
--   rotation_rank    : 1-13 integer (replaces depth_chart_rank)
--   role_tier        : 'franchise'|'star'|'starter'|'rotation'|'bench'
--                      derived from usage_rate, drives formula multiplier
--   usage_rate       : season usage% from ESPN box scores (0.0-1.0)
--   ppg/rpg/apg/per  : season averages for display + talent modifier fallback
--   nba_draft_projection : pick number (1-60), NULL if undrafted/unprojected
--   No cfbd_id (CFBD is football-only)
--   No ea_rating (NCAA football game only)
--   No nfl_draft_projection
--   No is_on_depth_chart (rotation_status covers this)
--   No production_score (may add later, not needed for v1)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS basketball_players (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name                  TEXT NOT NULL,
  position              TEXT,                          -- PG|SG|SF|PF|C (CG normalized to SG at ingest)
  role_tier             TEXT,                          -- franchise|star|starter|rotation|bench
  team_id               UUID REFERENCES basketball_teams(id) ON DELETE SET NULL,
  slug                  TEXT UNIQUE,
  player_tag            TEXT DEFAULT 'College Athlete', -- 'College Athlete'|'High School Recruit'|'Portal'
  class_year            TEXT,                          -- Freshman|Sophomore|Junior|Senior|Graduate
  experience_level      TEXT,                          -- maps to experience_multiplier
  hs_grad_year          INTEGER,
  cfo_valuation         INTEGER,
  is_override           BOOLEAN DEFAULT FALSE,
  roster_status         TEXT DEFAULT 'active',         -- active|departed_transfer|departed_draft|departed_graduated|departed_other
  rotation_status       TEXT,                          -- starter|rotation|bench|inactive
  rotation_rank         INTEGER,                       -- 1 (best) to 13
  usage_rate            NUMERIC(5,4),                  -- e.g. 0.2834 = 28.34%
  ppg                   NUMERIC(5,2),
  rpg                   NUMERIC(5,2),
  apg                   NUMERIC(5,2),
  per                   NUMERIC(5,2),                  -- Player Efficiency Rating
  nba_draft_projection  INTEGER,                       -- pick number 1-60, NULL if not projected
  star_rating           INTEGER,                       -- 1-5 (247Sports basketball composite)
  composite_score       NUMERIC(6,4),                  -- 247Sports composite (0.0-1.0)
  total_followers       INTEGER DEFAULT 0,
  ig_followers          INTEGER DEFAULT 0,
  x_followers           INTEGER DEFAULT 0,
  tiktok_followers      INTEGER DEFAULT 0,
  espn_athlete_id       TEXT,
  headshot_url          TEXT,
  is_public             BOOLEAN DEFAULT TRUE,
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------
-- basketball_nil_overrides
-- Same structure as nil_overrides.
-- annualized_value is a generated column for display convenience.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS basketball_nil_overrides (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  player_id        UUID NOT NULL REFERENCES basketball_players(id) ON DELETE CASCADE,
  total_value      NUMERIC(12,2),
  years            INTEGER DEFAULT 1,
  annualized_value NUMERIC(12,2) GENERATED ALWAYS AS (
    CASE WHEN years > 0 THEN total_value / years ELSE total_value END
  ) STORED,
  source_name      TEXT,
  source_url       TEXT,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------
-- basketball_player_events
-- Audit log for valuation and status changes.
-- Mirrors player_events exactly.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS basketball_player_events (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  player_id   UUID NOT NULL REFERENCES basketball_players(id) ON DELETE CASCADE,
  event_type  TEXT NOT NULL,   -- valuation_change|status_change|override_applied|transfer
  old_value   NUMERIC(12,2),
  new_value   NUMERIC(12,2),
  notes       TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------
-- Indexes
-- Mirrors the football players index strategy.
-- Trigram index for fuzzy name search.
-- Valuation DESC for leaderboard queries.
-- team_id for team roster queries.
-- slug for URL resolution (already UNIQUE, implicit index).
-- espn_athlete_id for enrichment script deduplication.
-- player_tag + roster_status for filtered leaderboard queries.
-- ------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_bball_players_name_trgm
  ON basketball_players USING GIN (name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_bball_players_team_id
  ON basketball_players (team_id);

CREATE INDEX IF NOT EXISTS idx_bball_players_valuation
  ON basketball_players (cfo_valuation DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_bball_players_player_tag
  ON basketball_players (player_tag);

CREATE INDEX IF NOT EXISTS idx_bball_players_roster_status
  ON basketball_players (roster_status);

CREATE INDEX IF NOT EXISTS idx_bball_players_espn_athlete_id
  ON basketball_players (espn_athlete_id);

CREATE INDEX IF NOT EXISTS idx_bball_players_hs_grad_year
  ON basketball_players (hs_grad_year);

CREATE INDEX IF NOT EXISTS idx_bball_teams_slug
  ON basketball_teams (slug);

-- ------------------------------------------------------------
-- updated_at trigger (mirrors football pattern)
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_basketball_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_basketball_teams_updated_at
  BEFORE UPDATE ON basketball_teams
  FOR EACH ROW EXECUTE FUNCTION update_basketball_updated_at();

CREATE TRIGGER trg_basketball_players_updated_at
  BEFORE UPDATE ON basketball_players
  FOR EACH ROW EXECUTE FUNCTION update_basketball_updated_at();

-- ------------------------------------------------------------
-- Seed: BYU basketball team (v1 launch team)
-- market_multiplier 1.08: Big 12 visibility + strong LDS fanbase.
-- Adjust after first valuation review.
-- estimated_nil_pool: basketball rosters are 13 players vs 85.
-- ------------------------------------------------------------
INSERT INTO basketball_teams (
  university_name,
  conference,
  logo_url,
  market_multiplier,
  estimated_nil_pool,
  slug
) VALUES (
  'BYU',
  'Big 12',
  'https://a.espncdn.com/i/teamlogos/ncaa/500/252.png',
  1.080,
  800000,
  'byu'
) ON CONFLICT (slug) DO NOTHING;
