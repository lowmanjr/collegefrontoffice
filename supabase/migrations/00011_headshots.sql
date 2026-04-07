ALTER TABLE players ADD COLUMN IF NOT EXISTS espn_athlete_id INTEGER;
ALTER TABLE players ADD COLUMN IF NOT EXISTS headshot_url TEXT;

CREATE INDEX idx_players_espn_athlete_id ON players(espn_athlete_id) WHERE espn_athlete_id IS NOT NULL;
