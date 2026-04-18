import type { Match, SeasonCount } from "@/lib/types";

// ---------------------------------------------------------------------------
// Interfaces
// ---------------------------------------------------------------------------

export interface Innings {
  innings: number;
  batting_team: string;
  total_runs: number;
  total_wickets: number;
  overs_played: number;
}

export interface TopBatter {
  match_id: string;
  innings: number;
  batter: string;
  runs_scored: number;
  balls_faced: number;
}

export interface TopBowler {
  match_id: string;
  innings: number;
  bowler: string;
  wickets: number;
  runs_conceded: number;
  overs_bowled: number;
}

export interface RecentMatch extends Match {
  innings: Innings[];
  floodlit: string | null;
  player_of_match: string | null;
  team1_captain: string | null;
  team2_captain: string | null;
  top_batters: TopBatter[];
  top_bowlers: TopBowler[];
}

// ---------------------------------------------------------------------------
// Team abbreviation map — all 19 IPL teams (current + historical)
// ---------------------------------------------------------------------------

const TEAM_ABBREVIATIONS: Record<string, string> = {
  "Mumbai Indians": "MI",
  "Chennai Super Kings": "CSK",
  "Royal Challengers Bengaluru": "RCB",
  "Royal Challengers Bangalore": "RCB",
  "Kolkata Knight Riders": "KKR",
  "Delhi Capitals": "DC",
  "Delhi Daredevils": "DD",
  "Punjab Kings": "PBKS",
  "Kings XI Punjab": "KXIP",
  "Rajasthan Royals": "RR",
  "Sunrisers Hyderabad": "SRH",
  "Gujarat Titans": "GT",
  "Lucknow Super Giants": "LSG",
  "Rising Pune Supergiant": "RPS",
  "Rising Pune Supergiants": "RPS",
  "Gujarat Lions": "GL",
  "Kochi Tuskers Kerala": "KTK",
  "Pune Warriors": "PWI",
  "Deccan Chargers": "DCH",
};

// ---------------------------------------------------------------------------
// Utility functions
// ---------------------------------------------------------------------------

/**
 * Returns the short abbreviation for a team name if it exists in the map,
 * otherwise returns the original name unchanged.
 */
export function shortName(teamName: string): string {
  return TEAM_ABBREVIATIONS[teamName] ?? teamName;
}

/**
 * Produces a human-readable match result string.
 *
 * - "no_result" → "No result"
 * - winning_margin present → "{shortName(winner)} won by {margin}"
 * - outcome_winner present but no margin → "{shortName(winner)} won"
 * - otherwise → ""
 */
export function formatMatchResult(match: RecentMatch): string {
  if (match.match_result_type === "no_result") {
    return "No result";
  }

  if (match.outcome_winner && match.winning_margin) {
    return `${shortName(match.outcome_winner)} won by ${match.winning_margin}`;
  }

  if (match.outcome_winner) {
    return `${shortName(match.outcome_winner)} won`;
  }

  return "";
}

/**
 * Groups matches by their `event_name`. Matches with a null/undefined
 * event_name are placed under the key "Other".
 *
 * Returns a Map ordered by group size descending (largest first).
 */
export function groupMatchesByTournament(
  matches: RecentMatch[],
): Map<string, RecentMatch[]> {
  const groups = new Map<string, RecentMatch[]>();

  for (const match of matches) {
    const key = match.event_name ?? "Other";
    const group = groups.get(key);
    if (group) {
      group.push(match);
    } else {
      groups.set(key, [match]);
    }
  }

  // Sort by group size descending
  const sorted = new Map(
    [...groups.entries()].sort((a, b) => b[1].length - a[1].length),
  );

  return sorted;
}

/**
 * Returns the season string with the highest numeric value,
 * or null for an empty array.
 */
export function getLatestSeason(seasons: SeasonCount[]): string | null {
  if (seasons.length === 0) return null;

  let latest = seasons[0];
  for (const s of seasons) {
    if (Number(s.season) > Number(latest.season)) {
      latest = s;
    }
  }

  return latest.season;
}
