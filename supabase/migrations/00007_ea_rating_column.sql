-- Migration: Add ea_rating column for EA Sports College Football 26 OVR ratings
-- Run this in Supabase SQL Editor

ALTER TABLE players ADD COLUMN IF NOT EXISTS ea_rating INTEGER;
COMMENT ON COLUMN players.ea_rating IS 'EA Sports College Football 26 overall rating (0-99)';
