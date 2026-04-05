/**
 * TypeScript types matching the FastAPI response shapes.
 * These mirror the gold layer schema — update when schema changes.
 */

export interface Match {
  match_id: string;
  season: string;
  match_date: string;
  city: string | null;
  venue: string;
  team1: string;
  team2: string;
  toss_winner: string;
  toss_decision: string;
  outcome_winner: string | null;
  outcome_by_runs: number | null;
  outcome_by_wickets: number | null;
  outcome_result: string | null;
  match_result_type: string;
  winning_margin: string | null;
  event_name: string | null;
  event_stage: string | null;
  match_type: string;
}

export interface Player {
  player_id: string;
  player_name: string;
  unique_name: string | null;
}

export interface Team {
  team_name: string;
  current_franchise_name: string | null;
  first_match_date: string;
  last_match_date: string;
  total_matches: number;
}

export interface SeasonCount {
  season: string;
  matches: number;
}

export interface BattingStats {
  batter: string;
  innings: number;
  total_runs: number;
  avg_strike_rate: number;
  total_fours: number;
  total_sixes: number;
}

export interface BowlingStats {
  bowler: string;
  innings: number;
  total_wickets: number;
  avg_economy: number;
  bowling_avg: number | null;
}
