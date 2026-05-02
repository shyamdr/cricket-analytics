"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface VenueRecord {
  matches: number;
  wins: number;
  losses: number;
  no_results: number;
  win_percentage: number | null;
}

interface RecentMatch {
  match_id: string;
  match_date: string;
  team1: string;
  team2: string;
  outcome_winner: string | null;
}

interface PhaseStats {
  phase: string;
  matches_sample_size: number;
  avg_runs: number | null;
  avg_wickets: number | null;
  avg_run_rate: number | null;
  boundary_pct: number | null;
  dot_ball_pct: number | null;
}

interface TeamData {
  team_name: string;
  recent_form: RecentMatch[];
  venue_record: VenueRecord;
  phase_stats: PhaseStats[];
}

interface HeadToHead {
  team_a: string;
  team_b: string;
  total_matches: number;
  team_a_wins: number;
  team_b_wins: number;
  no_results: number;
  ties: number;
  team_a_win_pct: number | null;
  last_5_winners: string[] | null;
}

interface TeamComparisonPanelProps {
  team1: TeamData;
  team2: TeamData;
  headToHead: HeadToHead | null;
}

function FormBadges({ team, matches }: { team: string; matches: RecentMatch[] }) {
  return (
    <div className="flex gap-1">
      {matches.map((m) => {
        const won = m.outcome_winner === team;
        const nr = !m.outcome_winner;
        return (
          <Badge
            key={m.match_id}
            variant={nr ? "secondary" : "outline"}
            className={`text-[10px] px-1.5 py-0 ${won ? "bg-green-500/10 text-green-600 border-green-500/30" : nr ? "" : "bg-red-500/10 text-red-600 border-red-500/30"}`}
          >
            {won ? "W" : nr ? "NR" : "L"}
          </Badge>
        );
      })}
    </div>
  );
}

function PhaseRow({ stats }: { stats: PhaseStats }) {
  return (
    <div className="grid grid-cols-5 gap-2 text-[11px] py-1">
      <span className="font-medium capitalize">{stats.phase}</span>
      <span className="font-mono text-right">{stats.avg_run_rate ?? "—"}</span>
      <span className="font-mono text-right">{stats.boundary_pct ?? "—"}%</span>
      <span className="font-mono text-right">{stats.dot_ball_pct ?? "—"}%</span>
      <span className="text-right text-muted-foreground">{stats.matches_sample_size}m</span>
    </div>
  );
}

function TeamCard({ team }: { team: TeamData }) {
  const vr = team.venue_record;
  return (
    <Card className="flex-1">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold">{team.team_name}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {/* Recent form */}
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">Recent Form</p>
          <FormBadges team={team.team_name} matches={team.recent_form} />
        </div>

        {/* Venue record */}
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">At This Venue</p>
          <div className="flex gap-3 text-[11px]">
            <span>{vr.matches} matches</span>
            <span className="text-green-600">{vr.wins}W</span>
            <span className="text-red-600">{vr.losses}L</span>
            {vr.win_percentage !== null && (
              <span className="font-mono">{vr.win_percentage}%</span>
            )}
          </div>
        </div>

        {/* Phase stats */}
        {team.phase_stats.length > 0 && (
          <div>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">Phase Averages</p>
            <div className="grid grid-cols-5 gap-2 text-[10px] text-muted-foreground pb-1 border-b">
              <span>Phase</span>
              <span className="text-right">RR</span>
              <span className="text-right">Bnd%</span>
              <span className="text-right">Dot%</span>
              <span className="text-right">Sample</span>
            </div>
            {team.phase_stats.map((ps) => (
              <PhaseRow key={ps.phase} stats={ps} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function TeamComparisonPanel({ team1, team2, headToHead }: TeamComparisonPanelProps) {
  return (
    <div className="space-y-4">
      {/* Head to head */}
      {headToHead && (
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between text-sm">
              <span className="font-semibold">{headToHead.team_a}</span>
              <div className="text-center">
                <span className="text-2xl font-bold font-mono">
                  {headToHead.team_a_wins} — {headToHead.team_b_wins}
                </span>
                <p className="text-[10px] text-muted-foreground">{headToHead.total_matches} matches</p>
              </div>
              <span className="font-semibold">{headToHead.team_b}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Side by side */}
      <div className="grid sm:grid-cols-2 gap-4">
        <TeamCard team={team1} />
        <TeamCard team={team2} />
      </div>
    </div>
  );
}
