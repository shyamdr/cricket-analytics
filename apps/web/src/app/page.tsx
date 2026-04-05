import { fetchAPI } from "@/lib/api";
import { Match, BattingStats, BowlingStats, SeasonCount } from "@/lib/types";
import Link from "next/link";

// Don't prerender — fetch fresh data on each request
export const dynamic = "force-dynamic";

export default async function Home() {
  let matches: Match[] = [];
  let seasons: SeasonCount[] = [];
  let topBatters: BattingStats[] = [];
  let topBowlers: BowlingStats[] = [];
  let error: string | null = null;

  try {
    [matches, seasons, topBatters, topBowlers] = await Promise.all([
      fetchAPI<Match[]>("/matches?limit=10"),
      fetchAPI<SeasonCount[]>("/matches/seasons"),
      fetchAPI<BattingStats[]>("/batting/top?limit=5"),
      fetchAPI<BowlingStats[]>("/bowling/top?limit=5"),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load data";
  }

  const totalMatches = seasons.reduce((sum, s) => sum + s.matches, 0);
  const totalSeasons = seasons.length;

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <h1 className="text-3xl font-bold mb-4">InsideEdge</h1>
        <p className="text-muted mb-2">Could not connect to the API.</p>
        <p className="text-sm text-muted font-mono">{error}</p>
        <p className="text-sm text-muted mt-4">
          Make sure FastAPI is running: <code className="text-accent">make api</code>
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Hero */}
      <div className="mb-10">
        <h1 className="text-4xl font-bold mb-2">InsideEdge</h1>
        <p className="text-muted text-lg">
          The detail that changes everything. {totalMatches.toLocaleString()} matches, {totalSeasons} seasons of ball-by-ball insights.
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
        <StatCard label="Matches" value={totalMatches.toLocaleString()} />
        <StatCard label="Seasons" value={totalSeasons.toString()} />
        <StatCard label="Latest Season" value={seasons.at(-1)?.season ?? "—"} />
        <StatCard
          label="Latest Match"
          value={matches[0]?.match_date ?? "—"}
        />
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Recent matches */}
        <div className="lg:col-span-2">
          <h2 className="text-xl font-semibold mb-4">Recent Matches</h2>
          <div className="space-y-3">
            {matches.map((m) => (
              <MatchCard key={m.match_id} match={m} />
            ))}
          </div>
          <Link
            href="/matches"
            className="inline-block mt-4 text-sm text-accent hover:underline"
          >
            View all matches →
          </Link>
        </div>

        {/* Leaderboards */}
        <div className="space-y-8">
          <div>
            <h2 className="text-xl font-semibold mb-4">Top Run Scorers</h2>
            <div className="bg-card border border-card-border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-card-border text-muted text-xs uppercase">
                    <th className="text-left px-4 py-2">Player</th>
                    <th className="text-right px-4 py-2">Runs</th>
                    <th className="text-right px-4 py-2">SR</th>
                  </tr>
                </thead>
                <tbody>
                  {topBatters.map((b, i) => (
                    <tr key={b.batter} className={i % 2 === 0 ? "" : "bg-background/30"}>
                      <td className="px-4 py-2">
                        <Link href={`/players/${encodeURIComponent(b.batter)}`} className="hover:text-accent transition-colors">
                          {b.batter}
                        </Link>
                      </td>
                      <td className="text-right px-4 py-2 font-mono">{b.total_runs.toLocaleString()}</td>
                      <td className="text-right px-4 py-2 font-mono text-muted">{b.avg_strike_rate}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div>
            <h2 className="text-xl font-semibold mb-4">Top Wicket Takers</h2>
            <div className="bg-card border border-card-border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-card-border text-muted text-xs uppercase">
                    <th className="text-left px-4 py-2">Player</th>
                    <th className="text-right px-4 py-2">Wkts</th>
                    <th className="text-right px-4 py-2">Econ</th>
                  </tr>
                </thead>
                <tbody>
                  {topBowlers.map((b, i) => (
                    <tr key={b.bowler} className={i % 2 === 0 ? "" : "bg-background/30"}>
                      <td className="px-4 py-2">
                        <Link href={`/players/${encodeURIComponent(b.bowler)}`} className="hover:text-accent transition-colors">
                          {b.bowler}
                        </Link>
                      </td>
                      <td className="text-right px-4 py-2 font-mono">{b.total_wickets}</td>
                      <td className="text-right px-4 py-2 font-mono text-muted">{b.avg_economy}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-card border border-card-border rounded-lg px-4 py-3">
      <p className="text-xs text-muted uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  );
}

function MatchCard({ match }: { match: Match }) {
  const isNoResult = match.match_result_type === "no_result";
  return (
    <Link
      href={`/matches/${match.match_id}`}
      className="block bg-card border border-card-border rounded-lg px-4 py-3 hover:border-accent/50 transition-colors"
    >
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 text-sm">
            <span className={match.outcome_winner === match.team1 ? "font-semibold text-win" : ""}>
              {match.team1}
            </span>
            <span className="text-muted">vs</span>
            <span className={match.outcome_winner === match.team2 ? "font-semibold text-win" : ""}>
              {match.team2}
            </span>
          </div>
          <p className="text-xs text-muted mt-1">
            {match.venue}{match.city ? `, ${match.city}` : ""} · {match.match_date}
          </p>
        </div>
        <div className="text-right text-xs">
          {isNoResult ? (
            <span className="text-muted">No Result</span>
          ) : match.winning_margin ? (
            <span className="text-muted">Won by {match.winning_margin}</span>
          ) : null}
        </div>
      </div>
    </Link>
  );
}
