-- Add espn_id column to basketball_teams for explicit ESPN team ID storage.
-- Until this migration is run, scripts derive espn_id from logo_url pattern:
--   https://a.espncdn.com/i/teamlogos/ncaa/500/{espn_id}.png

ALTER TABLE basketball_teams ADD COLUMN IF NOT EXISTS espn_id TEXT;

UPDATE basketball_teams SET espn_id = '252' WHERE slug = 'byu';
UPDATE basketball_teams SET espn_id = '96'  WHERE slug = 'kentucky';
UPDATE basketball_teams SET espn_id = '41'  WHERE slug = 'uconn';
