import { fetchAPI } from "@/lib/api";
import { Team, Match } from "@/lib/types";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function TeamDetailPage({
  params,
}: {
  params: Promise<{ teamName: string }>;
}) {
  const { teamName } = await params;
  const name = decodeURIComponent(teamName);

  let team: Team | null = null;
  let matches: Match[] = [];

  try {
    [team, matches] = await Promise.all([
      fetchAPI<Team>(`/teams/${encodeURIComponent(name)}`),
      fetchAPI<Match[]>(`/teams/${encodeURIComponent(name)}/matches?limit=50`),
    ]);
  } catch {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <p className="text-muted">Team &quot;{name}&quot; not found.</p>
        <Link href="/teams" className="text-accent hover:underline text-sm mt-2 inline-block">
          ← Back to teams
        </Link>
      </div>
    );
  }

  const wins = matches.filter((m) => m.outcome_winner === name).length;
  const losses = matches.filter(
    (m) => m.outcome_winner && m.outcome_winner !== name
  ).length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Link href="/teams" className="text-sm text-muted hover:text-accent mb-2 inline-block">
        ← Back to teams
      </Link>

      <h1 className="text-3xl font-bold mb-1">{team?.team_name}</h1>
      {team?.current_franchise_name &&
        team.current_franchise_name !== team.team_name && (
          <p className="text-muted mb-4">Now: {team.current_franchise_name}</p>
        )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
        <div className="bg-card border border-card-border rounded-lg px-4 py-3">
          <p className="text-xs text-muted uppercase">Matches</p>
          <p className="text-2xl font-bold mt-1">{team?.total_matches}</p>
        </div>
        <div className="bg-card border border-card-border rounded-lg px-4 py-3">
          <p className="text-xs text-muted uppercase">Won</p>
          <p className="text-2xl font-bold mt-1 text-win">{wins}</p>
        </div>
        <div className="bg-card border border-card-border rounded-lg px-4 py-3">
          <p className="text-xs text-muted uppercase">Lost</p>
          <p className="text-2xl font-bold mt-1 text-loss">{losses}</p>
        </div>
        <div className="bg-card border border-card-border rounded-lg px-4 py-3">
          <p className="text-xs text-muted uppercase">Win %</p>
          <p className="text-2xl font-bold mt-1">
            {matches.length > 0
              ? Math.round((wins / matches.length) * 100)
              : 0}
            %
          </p>
        </div>
      </div>

      <h2 className="text-xl font-semibold mb-4">Recent Matches</h2>
      <div className="space-y-2">
        {matches.map((m) => {
          const opponent = m.team1 === name ? m.team2 : m.team1;
          const won = m.outcome_winner === name;
          const lost = m.outcome_winner && m.outcome_winner !== name;
          return (
            <Link
              key={m.match_id}
              href={`/matches/${m.match_id}`}
              className="flex items-center justify-between bg-card border border-card-border rounded-lg px-4 py-3 hover:border-accent/50 transition-colors"
            >
              <div>
                <div className="flex items-center gap-2 text-sm">
                  <span>vs {opponent}</span>
                  {won && <span className="text-xs text-win font-medium">W</span>}
                  {lost && <span className="text-xs text-loss font-medium">L</span>}
                  {!won && !lost && <span className="text-xs text-muted">NR</span>}
                </div>
                <p className="text-xs text-muted mt-1">
                  {m.venue} · {m.match_date}
                </p>
              </div>
              <div className="text-xs text-muted">
                {m.winning_margin ? `by ${m.winning_margin}` : ""}
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
