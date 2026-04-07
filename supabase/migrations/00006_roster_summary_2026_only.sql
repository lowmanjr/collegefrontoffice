-- Migration: Only count class of 2026 recruits in team totals
-- Run this in Supabase SQL Editor

DROP VIEW IF EXISTS team_roster_summary;

CREATE VIEW team_roster_summary AS
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
  COALESCE(SUM(p.cfo_valuation) FILTER (
    WHERE p.roster_status = 'active' AND p.player_tag = 'College Athlete'
  ), 0)::bigint AS total_roster_value,
  COUNT(p.id) FILTER (
    WHERE p.roster_status = 'active' AND p.player_tag = 'College Athlete'
  )::int AS roster_count,
  COUNT(p.id) FILTER (
    WHERE p.roster_status = 'active' AND p.player_tag = 'College Athlete'
  )::int AS college_count,
  COALESCE(SUM(p.cfo_valuation) FILTER (
    WHERE p.player_tag = 'High School Recruit' AND p.hs_grad_year = 2026
  ), 0)::bigint AS incoming_recruit_value,
  COUNT(p.id) FILTER (
    WHERE p.player_tag = 'High School Recruit' AND p.hs_grad_year = 2026
  )::int AS incoming_recruit_count,
  COALESCE(SUM(p.cfo_valuation) FILTER (
    WHERE (p.roster_status = 'active' AND p.player_tag = 'College Athlete')
       OR (p.player_tag = 'High School Recruit' AND p.hs_grad_year = 2026)
  ), 0)::bigint AS total_program_value,
  COUNT(p.id) FILTER (
    WHERE p.player_tag = 'High School Recruit' AND p.hs_grad_year = 2026
  )::int AS recruit_count,
  COALESCE(AVG(p.cfo_valuation) FILTER (
    WHERE p.roster_status = 'active' AND p.player_tag = 'College Athlete'
  ), 0)::int AS avg_valuation,
  COALESCE(MAX(p.cfo_valuation) FILTER (
    WHERE p.roster_status = 'active'
  ), 0)::int AS max_valuation,
  COUNT(p.id) FILTER (
    WHERE p.roster_status != 'active' AND p.player_tag = 'College Athlete'
  )::int AS departed_count
FROM teams t
LEFT JOIN players p ON p.team_id = t.id
GROUP BY t.id;

GRANT SELECT ON team_roster_summary TO anon;
GRANT SELECT ON team_roster_summary TO authenticated;
