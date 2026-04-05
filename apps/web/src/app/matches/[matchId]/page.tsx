import { fetchAPI } from "@/lib/api";
import { Match } from "@/lib/types";
import Link from "next/link";

export const dynamic = "force-dynamic";

interface MatchSummary {
  match_id: string;
  innings: number;
  batting_team: string;
  total_runs: number;
  total_wickets: number;
  overs_played: number;
  run_rate: number;
  total_fours: number;
  total_sixes: number;
}

interface BattingInnings {
  batter: string;
  runs_scored: number;
  balls_faced: number;
  fours: number;
  sixes: number;
  strike_rate: number;
  is_out: boolean;
  dismissal_kind: string | null;
  dismissed_by: string | null;
}

interface BowlingInnings {
  bowler: string;
  overs_bowled: number;
  runs_conceded: number;
  wickets: number;
  economy_rate: number;
  dot_balls: number;
  wides: number;
  noballs: number;
}

export default async function MatchDetailPage({
  params,
}: {
  params: Promise<{ matchId: string }>;
}) {
  const { matchId } = await params;

  const [match, summary, batting, bowling] = await Promise.all([
    fetchAPI<Match>(`/matches/${matchId}`),
    fetchAPI<MatchSummary[]>(`/matches/${matchId}/summary`),
    fetchAPI<BattingInnings[]>(`/matches/${matchId}/batting`),
    fetchAPI<BowlingInnings[]>(`/matches/${matchId}/bowling`),
  ]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Match header */}
      <div className="mb-8">
        <Link href="/matches" className="text-sm text-muted hover:text-accent mb-2 inline-block">
          ← Back to matches
        </Link>
        <h1 className="text-2xl font-bold">
          <span className={match.outcome_winner === match.team1 ? "text-win" : ""}>
            {match.team1}
          </span>
          {" vs "}
          <span className={match.outcome_winner === match.team2 ? "text-win" : ""}>
            {match.team2}
          </span>
        </h1>
        <p className="text-muted mt-1">
          {match.venue}{match.city ? `, ${match.city}` : ""} · {match.match_date}
          {match.event_name ? ` · ${match.event_name}` : ""}
          {match.event_stage ? ` — ${match.event_stage}` : ""}
        </p>
        <p className="text-sm mt-2">
          Toss: {match.toss_winner} chose to {match.toss_decision}
          {match.winning_margin && (
            <span className="ml-3 text-win font-medium">
              {match.outcome_winner} won by {match.winning_margin}
            </span>
          )}
          {match.match_result_type === "no_result" && (
            <span className="ml-3 text-muted">No Result</span>
          )}
        </p>
      </div>

      {/* Innings summaries */}
      <div className="grid sm:grid-cols-2 gap-4 mb-8">
        {summary.map((s) => (
          <div key={s.innings} className="bg-card border border-card-border rounded-lg px-4 py-3">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold">{s.batting_team}</h3>
              <span className="text-xl font-bold font-mono">
                {s.total_runs}/{s.total_wickets}
                <span className="text-sm text-muted ml-1">({s.overs_played} ov)</span>
              </span>
            </div>
            <div className="flex gap-4 text-xs text-muted">
              <span>RR: {s.run_rate}</span>
              <span>4s: {s.total_fours}</span>
              <span>6s: {s.total_sixes}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Scorecard tabs — show both innings */}
      {summary.map((s) => {
        const innBatting = batting.filter(
          (b) => summary.findIndex((ss) => ss.batting_team === s.batting_team) ===
                 summary.indexOf(s) &&
                 batting.indexOf(b) >= 0
        );
        // Filter batting/bowling by innings number
        const innIdx = s.innings;
        const batters = batting.filter((_, i) => {
          // Group by innings order — first N batters are innings 1, rest innings 2
          const inn1Count = batting.filter(
            (bb) => summary[0] && bb.batter !== undefined
          ).length;
          return true; // Show all for now, we'll refine
        });

        return (
          <div key={s.innings} className="mb-8">
            <h2 className="text-lg font-semibold mb-3">
              {s.batting_team} — {s.total_runs}/{s.total_wickets} ({s.overs_played} ov)
            </h2>

            {/* Batting */}
            <div className="bg-card border border-card-border rounded-lg overflow-x-auto mb-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-card-border text-muted text-xs uppercase">
                    <th className="text-left px-4 py-2">Batter</th>
                    <th className="text-right px-4 py-2">R</th>
                    <th className="text-right px-4 py-2">B</th>
                    <th className="text-right px-4 py-2">4s</th>
                    <th className="text-right px-4 py-2">6s</th>
                    <th className="text-right px-4 py-2">SR</th>
                  </tr>
                </thead>
                <tbody>
                  {batting
                    .filter((_, idx) => {
                      // Simple split: first half = innings 1, second half = innings 2
                      const midpoint = batting.length / summary.length;
                      const start = (s.innings - 1) * midpoint;
                      const end = s.innings * midpoint;
                      return idx >= start && idx < end;
                    })
                    .map((b) => (
                      <tr key={b.batter} className="border-b border-card-border/50">
                        <td className="px-4 py-2">
                          <Link
                            href={`/players/${encodeURIComponent(b.batter)}`}
                            className="hover:text-accent transition-colors"
                          >
                            {b.batter}
                          </Link>
                          {b.dismissal_kind && (
                            <span className="text-xs text-muted ml-2">
                              {b.dismissal_kind}
                              {b.dismissed_by ? ` b ${b.dismissed_by}` : ""}
                            </span>
                          )}
                          {!b.is_out && <span className="text-xs text-win ml-2">not out</span>}
                        </td>
                        <td className="text-right px-4 py-2 font-mono font-semibold">{b.runs_scored}</td>
                        <td className="text-right px-4 py-2 font-mono text-muted">{b.balls_faced}</td>
                        <td className="text-right px-4 py-2 font-mono text-muted">{b.fours}</td>
                        <td className="text-right px-4 py-2 font-mono text-muted">{b.sixes}</td>
                        <td className="text-right px-4 py-2 font-mono text-muted">{b.strike_rate}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>

            {/* Bowling */}
            <div className="bg-card border border-card-border rounded-lg overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-card-border text-muted text-xs uppercase">
                    <th className="text-left px-4 py-2">Bowler</th>
                    <th className="text-right px-4 py-2">O</th>
                    <th className="text-right px-4 py-2">R</th>
                    <th className="text-right px-4 py-2">W</th>
                    <th className="text-right px-4 py-2">Econ</th>
                  </tr>
                </thead>
                <tbody>
                  {bowling
                    .filter((_, idx) => {
                      const midpoint = bowling.length / summary.length;
                      const start = (s.innings - 1) * midpoint;
                      const end = s.innings * midpoint;
                      return idx >= start && idx < end;
                    })
                    .map((b) => (
                      <tr key={b.bowler} className="border-b border-card-border/50">
                        <td className="px-4 py-2">
                          <Link
                            href={`/players/${encodeURIComponent(b.bowler)}`}
                            className="hover:text-accent transition-colors"
                          >
                            {b.bowler}
                          </Link>
                        </td>
                        <td className="text-right px-4 py-2 font-mono">{b.overs_bowled}</td>
                        <td className="text-right px-4 py-2 font-mono">{b.runs_conceded}</td>
                        <td className="text-right px-4 py-2 font-mono font-semibold">{b.wickets}</td>
                        <td className="text-right px-4 py-2 font-mono text-muted">{b.economy_rate}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}
    </div>
  );
}
