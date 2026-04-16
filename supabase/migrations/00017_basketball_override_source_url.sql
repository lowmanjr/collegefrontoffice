-- Migration: 00017_basketball_override_source_url.sql
-- Add source URL attribution for manual valuation overrides

ALTER TABLE basketball_players
ADD COLUMN IF NOT EXISTS override_source_url TEXT;

COMMENT ON COLUMN basketball_players.override_source_url IS 'Reputable source URL supporting the override valuation. Only populated when is_override = true.';
