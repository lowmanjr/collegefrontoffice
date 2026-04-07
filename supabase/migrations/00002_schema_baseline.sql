-- ============================================================
-- 00002_schema_baseline.sql
-- Source-of-truth schema for CollegeFrontOffice database.
-- Safe to replay: uses CREATE TABLE IF NOT EXISTS throughout.
-- ============================================================

-- ── teams ────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS teams (
  id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  university_name     TEXT        NOT NULL,
  conference          TEXT,
  logo_url            TEXT,
  estimated_cap_space INTEGER     NOT NULL DEFAULT 20500000,
  active_payroll      INTEGER     NOT NULL DEFAULT 0,
  market_multiplier   NUMERIC(4,3) NOT NULL DEFAULT 1.000,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── players ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS players (
  id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name                 TEXT        NOT NULL,
  position             TEXT,
  star_rating          INTEGER     CHECK (star_rating BETWEEN 1 AND 5),
  -- 1-5 for college athletes (1=FR…5=5th yr); graduation year (2025+) for HS recruits
  class_year           TEXT,
  experience_level     TEXT,
  player_tag           TEXT,         -- 'College Athlete' | 'High School Recruit' | 'Portal'
  composite_score      NUMERIC(8,4),
  national_rank        INTEGER,
  high_school          TEXT,
  cfo_valuation        INTEGER,
  reported_nil_deal    INTEGER,
  is_on_depth_chart    BOOLEAN     NOT NULL DEFAULT false,
  is_public            BOOLEAN     NOT NULL DEFAULT true,
  is_override          BOOLEAN     NOT NULL DEFAULT false,
  status               TEXT,         -- e.g. 'Active', 'Inactive', 'Medical Exemption'
  nfl_draft_projection INTEGER,      -- projected draft round (1-7)
  production_score     NUMERIC(5,3),
  total_followers      INTEGER,
  ig_followers         INTEGER,
  x_followers          INTEGER,
  tiktok_followers     INTEGER,
  cfbd_id              INTEGER,
  hs_grad_year         INTEGER,      -- HS graduation year (2026, 2027, 2028). HS recruits only.
  depth_chart_rank     INTEGER,      -- 1=starter, 2=backup, etc. Position-aware.
  roster_status        TEXT        NOT NULL DEFAULT 'active',  -- active, departed_draft, departed_transfer, departed_graduated, departed_other
  on3_valuation        INTEGER,      -- On3 NIL Valuation (external reference data)
  team_id              UUID        REFERENCES teams (id) ON DELETE SET NULL,
  last_updated         TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── player_events ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS player_events (
  id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  player_id           UUID        NOT NULL REFERENCES players (id) ON DELETE CASCADE,
  event_type          TEXT        NOT NULL,
  event_date          DATE        NOT NULL,
  new_valuation       INTEGER,
  previous_valuation  INTEGER,
  reported_deal       INTEGER,
  description         TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── proposed_events ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS proposed_events (
  id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  player_id           UUID        NOT NULL REFERENCES players (id) ON DELETE CASCADE,
  event_type          TEXT        NOT NULL,
  event_date          DATE        NOT NULL,
  proposed_valuation  INTEGER     NOT NULL,
  current_valuation   INTEGER,
  reported_deal       INTEGER,
  description         TEXT,
  status              TEXT        NOT NULL DEFAULT 'pending',  -- 'pending' | 'approved' | 'rejected'
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── nil_overrides ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS nil_overrides (
  id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  player_id           UUID        NOT NULL REFERENCES players (id) ON DELETE CASCADE,
  annualized_value    INTEGER     NOT NULL,
  total_value         INTEGER     NOT NULL,
  years               NUMERIC(4,2) NOT NULL DEFAULT 1,
  source_name         TEXT,
  source_url          TEXT,
  verified_at         TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── indexes ───────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_players_team_id         ON players (team_id);
CREATE INDEX IF NOT EXISTS idx_players_player_tag      ON players (player_tag);
CREATE INDEX IF NOT EXISTS idx_players_cfo_valuation   ON players (cfo_valuation DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_players_name_trgm       ON players USING gin (name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_player_events_player_id ON player_events (player_id);
CREATE INDEX IF NOT EXISTS idx_player_events_date      ON player_events (event_date DESC);

CREATE INDEX IF NOT EXISTS idx_proposed_events_player  ON proposed_events (player_id);
CREATE INDEX IF NOT EXISTS idx_proposed_events_status  ON proposed_events (status) WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_nil_overrides_player_id ON nil_overrides (player_id);

CREATE INDEX IF NOT EXISTS idx_players_roster_status    ON players (roster_status);
CREATE INDEX IF NOT EXISTS idx_players_hs_grad_year     ON players (hs_grad_year) WHERE player_tag = 'High School Recruit';
