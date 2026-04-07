-- Migration: Add roster_status column and update team_roster_summary view
-- Run this in Supabase SQL Editor before running sync_roster_status.py

-- 1. Add roster_status column
ALTER TABLE players ADD COLUMN IF NOT EXISTS roster_status TEXT DEFAULT 'active';
COMMENT ON COLUMN players.roster_status IS 'active, departed_draft, departed_transfer, departed_graduated, departed_other';

-- 2. Update team_roster_summary view to exclude departed players
CREATE OR REPLACE VIEW team_roster_summary AS
SELECT
  t.id,
  t.university_name,
  t.conference,
  t.logo_url,
  t.estimated_cap_space,
  t.active_payroll,
  t.market_multiplier,
  t.ncaa_revenue_share,
  t.football_allocation_pct,
  t.nil_collective_tier,
  t.total_athletics_revenue,
  t.total_football_revenue,
  t.total_football_expenses,
  t.reporting_year,
  COALESCE(SUM(p.cfo_valuation) FILTER (WHERE p.roster_status = 'active'), 0)::bigint AS total_roster_value,
  COUNT(p.id) FILTER (WHERE p.roster_status = 'active')::int AS roster_count,
  COUNT(p.id) FILTER (WHERE p.roster_status = 'active' AND p.player_tag = 'College Athlete')::int AS college_count,
  COUNT(p.id) FILTER (WHERE p.roster_status = 'active' AND p.player_tag = 'High School Recruit')::int AS recruit_count,
  COALESCE(AVG(p.cfo_valuation) FILTER (WHERE p.roster_status = 'active'), 0)::int AS avg_valuation,
  COALESCE(MAX(p.cfo_valuation) FILTER (WHERE p.roster_status = 'active'), 0)::int AS max_valuation,
  COUNT(p.id) FILTER (WHERE p.roster_status != 'active')::int AS departed_count
FROM teams t
LEFT JOIN players p ON p.team_id = t.id
GROUP BY t.id;
