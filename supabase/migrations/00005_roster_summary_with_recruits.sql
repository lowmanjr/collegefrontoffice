-- Migration: Update team_roster_summary to include incoming HS recruits
-- Run this in Supabase SQL Editor

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
  -- Active college athletes
  COALESCE(SUM(p.cfo_valuation) FILTER (
    WHERE p.roster_status = 'active' AND p.player_tag = 'College Athlete'
  ), 0)::bigint AS total_roster_value,
  COUNT(p.id) FILTER (
    WHERE p.roster_status = 'active' AND p.player_tag = 'College Athlete'
  )::int AS roster_count,
  COUNT(p.id) FILTER (
    WHERE p.roster_status = 'active' AND p.player_tag = 'College Athlete'
  )::int AS college_count,
  -- Incoming HS recruits (always included regardless of roster_status)
  COALESCE(SUM(p.cfo_valuation) FILTER (
    WHERE p.player_tag = 'High School Recruit'
  ), 0)::bigint AS incoming_recruit_value,
  COUNT(p.id) FILTER (
    WHERE p.player_tag = 'High School Recruit'
  )::int AS incoming_recruit_count,
  -- Combined total
  COALESCE(SUM(p.cfo_valuation) FILTER (
    WHERE (p.roster_status = 'active' AND p.player_tag = 'College Athlete')
       OR p.player_tag = 'High School Recruit'
  ), 0)::bigint AS total_program_value,
  -- Legacy columns
  COUNT(p.id) FILTER (WHERE p.player_tag = 'High School Recruit')::int AS recruit_count,
  COALESCE(AVG(p.cfo_valuation) FILTER (
    WHERE p.roster_status = 'active' AND p.player_tag = 'College Athlete'
  ), 0)::int AS avg_valuation,
  COALESCE(MAX(p.cfo_valuation) FILTER (
    WHERE p.roster_status = 'active'
  ), 0)::int AS max_valuation,
  COUNT(p.id) FILTER (WHERE p.roster_status != 'active' AND p.player_tag = 'College Athlete')::int AS departed_count
FROM teams t
LEFT JOIN players p ON p.team_id = t.id
GROUP BY t.id;
