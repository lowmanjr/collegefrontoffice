-- Add acquisition_type to basketball_players
-- Mirrors football players table pattern
-- Values: 'retained' | 'portal' | 'recruit'

ALTER TABLE basketball_players
ADD COLUMN IF NOT EXISTS acquisition_type TEXT DEFAULT 'retained';

CREATE INDEX IF NOT EXISTS idx_bball_players_acquisition_type
  ON basketball_players (acquisition_type);
