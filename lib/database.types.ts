// ─────────────────────────────────────────────────────────────────────────────
// lib/database.types.ts
// Single source of truth for all Supabase row types.
// Import these instead of writing local interfaces in page files.
// ─────────────────────────────────────────────────────────────────────────────

// ── Raw row types ─────────────────────────────────────────────────────────────

export interface TeamRow {
  id: string;
  university_name: string;
  conference: string | null;
  logo_url: string | null;
  estimated_cap_space: number;
  active_payroll: number;
  market_multiplier: number;
  slug: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlayerRow {
  id: string;
  name: string;
  position: string | null;
  star_rating: number | null;
  /** 1–5 for college athletes (1=FR…5=5th yr); graduation year (2025+) for HS recruits */
  class_year: string | null;
  experience_level: string | null;
  /** 'College Athlete' | 'High School Recruit' | 'Portal' */
  player_tag: string | null;
  composite_score: number | null;
  national_rank: number | null;
  high_school: string | null;
  cfo_valuation: number | null;
  reported_nil_deal: number | null;
  is_on_depth_chart: boolean;
  depth_chart_rank: number | null;
  /** 'active' | 'departed_draft' | 'departed_transfer' | 'departed_graduated' | 'departed_other' */
  roster_status: string | null;
  /** 'retained' | 'portal' | 'recruit' */
  acquisition_type: string;
  is_public: boolean;
  is_override: boolean;
  /** e.g. 'Active' | 'Inactive' | 'Medical Exemption' */
  status: string | null;
  nfl_draft_projection: number | null;
  production_score: number | null;
  total_followers: number | null;
  ig_followers: number | null;
  x_followers: number | null;
  tiktok_followers: number | null;
  cfbd_id: number | null;
  espn_athlete_id: number | null;
  headshot_url: string | null;
  hs_grad_year: number | null;
  team_id: string | null;
  slug: string | null;
  last_updated: string;
  created_at: string;
}

export interface PlayerEventRow {
  id: string;
  player_id: string;
  event_type: string;
  event_date: string;
  new_valuation: number | null;
  previous_valuation: number | null;
  reported_deal: number | null;
  description: string | null;
  created_at: string;
}

export interface ProposedEventRow {
  id: string;
  player_id: string;
  event_type: string;
  event_date: string;
  proposed_valuation: number;
  current_valuation: number | null;
  reported_deal: number | null;
  description: string | null;
  /** 'pending' | 'approved' | 'rejected' */
  status: string;
  created_at: string;
}

export interface NilOverrideRow {
  id: string;
  player_id: string;
  annualized_value: number;
  total_value: number;
  years: number;
  source_name: string | null;
  source_url: string | null;
  verified_at: string | null;
  created_at: string;
}

// ── Joined types ──────────────────────────────────────────────────────────────

/** Player row with its team joined (as returned by Supabase select with teams(...)) */
export interface PlayerWithTeam extends PlayerRow {
  teams: Pick<TeamRow, "university_name" | "logo_url"> | null;
}

/** Player row with team including market_multiplier (used on player profile page) */
export interface PlayerWithTeamFull extends PlayerRow {
  teams: Pick<TeamRow, "university_name" | "logo_url" | "market_multiplier"> | null;
}

/** Proposed event with the associated player's name and current valuation */
export interface ProposedEventWithPlayer extends ProposedEventRow {
  players: Pick<PlayerRow, "name" | "cfo_valuation"> | null;
}

// ── Basketball Types ──────────────────────────────────────────────────────────

export interface BasketballTeamRow {
  id: string;
  university_name: string;
  conference: string | null;
  logo_url: string | null;
  market_multiplier: number;
  estimated_nil_pool: number | null;
  active_payroll: number | null;
  slug: string | null;
  created_at: string;
  updated_at: string;
}

export interface BasketballPlayerRow {
  id: string;
  name: string;
  position: string | null;
  role_tier: string | null;
  team_id: string | null;
  slug: string | null;
  player_tag: string | null;
  class_year: string | null;
  experience_level: string | null;
  hs_grad_year: number | null;
  cfo_valuation: number | null;
  is_override: boolean;
  roster_status: string | null;
  rotation_status: string | null;
  rotation_rank: number | null;
  usage_rate: number | null;
  ppg: number | null;
  rpg: number | null;
  apg: number | null;
  per: number | null;
  nba_draft_projection: number | null;
  star_rating: number | null;
  composite_score: number | null;
  total_followers: number | null;
  ig_followers: number | null;
  x_followers: number | null;
  tiktok_followers: number | null;
  espn_athlete_id: string | null;
  headshot_url: string | null;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export interface BasketballNilOverrideRow {
  id: string;
  player_id: string;
  total_value: number | null;
  years: number | null;
  annualized_value: number | null;
  source_name: string | null;
  source_url: string | null;
  created_at: string;
}

export type BasketballPlayerWithTeam = BasketballPlayerRow & {
  basketball_teams: Pick<
    BasketballTeamRow,
    "university_name" | "slug" | "logo_url" | "conference"
  > | null;
};

export interface BasketballPortalEntryRow {
  id: string;
  player_name: string;
  position: string | null;
  origin_school: string | null;
  destination_school: string | null;
  origin_team_id: string | null;
  destination_team_id: string | null;
  status: "committed" | "evaluating";
  star_rating: number | null;
  cfo_valuation: number | null;
  on3_nil_value: number | null;
  headshot_url: string | null;
  entry_date: string | null;
  commitment_date: string | null;
  on3_player_slug: string | null;
  created_at: string;
  updated_at: string;
}

export type BasketballPortalEntryWithTeams = BasketballPortalEntryRow & {
  origin_team: Pick<BasketballTeamRow, "university_name" | "slug" | "logo_url"> | null;
  destination_team: Pick<BasketballTeamRow, "university_name" | "slug" | "logo_url"> | null;
};

/** Row type for the team_roster_summary database view */
export interface TeamRosterSummary {
  id: string;
  university_name: string | null;
  conference: string | null;
  logo_url: string | null;
  estimated_cap_space: number | null;
  active_payroll: number | null;
  market_multiplier: number | null;
  ncaa_revenue_share: number | null;
  football_allocation_pct: number | null;
  nil_collective_tier: string | null;
  total_athletics_revenue: number | null;
  total_football_revenue: number | null;
  total_football_expenses: number | null;
  reporting_year: string | null;
  total_roster_value: number;
  total_program_value: number;
  incoming_recruit_value: number;
  incoming_recruit_count: number;
  roster_count: number;
  college_count: number;
  recruit_count: number;
  avg_valuation: number;
  max_valuation: number;
  departed_count: number;
}
