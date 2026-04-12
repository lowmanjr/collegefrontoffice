-- Basketball transfer portal display table.
-- Rebuilt on each sync_bball_portal_display.py run.
-- Captures committed + evaluating players where origin or destination
-- is a CFO-tracked team.

CREATE TABLE IF NOT EXISTS basketball_portal_entries (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  player_name           TEXT NOT NULL,
  position              TEXT,
  origin_school         TEXT,
  destination_school    TEXT,
  origin_team_id        UUID REFERENCES basketball_teams(id) ON DELETE SET NULL,
  destination_team_id   UUID REFERENCES basketball_teams(id) ON DELETE SET NULL,
  status                TEXT NOT NULL DEFAULT 'evaluating',
  star_rating           INTEGER,
  cfo_valuation         INTEGER,
  on3_nil_value         INTEGER,
  headshot_url          TEXT,
  entry_date            TEXT,
  commitment_date       TEXT,
  on3_player_slug       TEXT,
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_portal_status
  ON basketball_portal_entries (status);
CREATE INDEX IF NOT EXISTS idx_portal_valuation
  ON basketball_portal_entries (cfo_valuation DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_portal_on3_slug
  ON basketball_portal_entries (on3_player_slug);
