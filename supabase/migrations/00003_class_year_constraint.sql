-- ============================================================
-- 00003_class_year_constraint.sql
-- Adds a CHECK constraint to players.class_year to enforce
-- the two valid formats:
--   • '1'–'5'  → college athlete year-of-eligibility
--   • '2025'+  → high school recruit graduation year
-- ============================================================

ALTER TABLE players
  ADD CONSTRAINT players_class_year_format
    CHECK (
      class_year IS NULL
      OR class_year ~ '^[1-5]$'
      OR class_year ~ '^20[2-9][0-9]$'
    );
