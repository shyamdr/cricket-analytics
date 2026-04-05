import { fetchAPI } from "@/lib/api";
import Link from "next/link";

export const dynamic = "force-dynamic";

interface PlayerProfile {
  player_id: string;
  player_name: string;
  unique_name: string | null;
  playing_roles: string | null;
  batting_styles: string | null;
  bowling_styles: string | null;
}

interface CareerBatting {
  batter: string;
  innings: number;
  total_runs: number;
  highest_score: number;
  avg_runs: number;
  avg_strike_rate: number;
  total_fours: number;
  total_sixes: number;
  fifties: number;
  centuries: number;
}

interface CareerBowling {
  bowler: string;
  innings: number;
  total_wickets: number;
  avg_economy: number;
  bowling_avg: number | null;
  best_wickets: number;
}

interface SeasonBatting {
  season: string;
  innings: number;
  total_runs: number;
  highest_score: number;
  avg_strike_rate: number;
  fours: number;
  sixes: number;
}

export default async function PlayerDetailPage({
  params,
}: {
  params: Promise<{ playerName: string }>;
}) {
  const { playerName } = await params;
  const name = decodeURIComponent(playerName);

  let profile: PlayerProfile | null = null;
  let batting: CareerBatting[] = [];
  let bowling: CareerBowling[] = [];
  let seasonBatting: SeasonBatting[] = [];

  try {
    [profile, batting, bowling, seasonBatting] = await Promise.all([
      fetchAPI<PlayerProfile>(`/players/${encodeURIComponent(name)}`),
      fetchAPI<CareerBatting[]>(`/batting/stats/${encodeURIComponent(name)}`),
      fetchAPI<CareerBowling[]>(`/bowling/stats/${encodeURIComponent(name)}`),
      fetchAPI<SeasonBatting[]>(`/batting/season-breakdown/${encodeURIComponent(name)}`),
    ]);
  } catch {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <p className="text-muted">Player &quot;{name}&quot; not found.</p>
        <Link href="/players" className="text-accent hover:underline text-sm mt-2 inline-block">
          ← Back to players
        </Link>
      </div>
    );
  }

  const bat = batting[0];
  const bowl = bowling[0];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Link href="/players" className="text-sm text-muted hover:text-accent mb-2 inline-block">
        ← Back to players
      </Link>

      <h1 className="text-3xl font-bold mb-1">{profile?.player_name}</h1>
      {profile?.unique_name && profile.unique_name !== profile.player_name && (
        <p className="text-muted mb-4">{profile.unique_name}</p>
      )}

      {/* Career batting */}
      {bat && bat.innings > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-3">Batting Career</h2>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <StatBox label="Innings" value={bat.innings.toString()} />
            <StatBox label="Runs" value={bat.total_runs.toLocaleString()} />
            <StatBox label="Highest" value={bat.highest_score.toString()} />
            <StatBox label="Strike Rate" value={bat.avg_strike_rate.toString()} />
            <StatBox label="50s / 100s" value={`${bat.fifties} / ${bat.centuries}`} />
          </div>
        </div>
      )}

      {/* Career bowling */}
      {bowl && bowl.innings > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-3">Bowling Career</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatBox label="Innings" value={bowl.innings.toString()} />
            <StatBox label="Wickets" value={bowl.total_wickets.toString()} />
            <StatBox label="Economy" value={bowl.avg_economy.toString()} />
            <StatBox label="Best" value={`${bowl.best_wickets}w`} />
          </div>
        </div>
      )}

      {/* Season breakdown */}
      {seasonBatting.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold mb-3">Season by Season</h2>
          <div className="bg-card border border-card-border rounded-lg overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-card-border text-muted text-xs uppercase">
                  <th className="text-left px-4 py-2">Season</th>
                  <th className="text-right px-4 py-2">Inn</th>
                  <th className="text-right px-4 py-2">Runs</th>
                  <th className="text-right px-4 py-2">HS</th>
                  <th className="text-right px-4 py-2">SR</th>
                  <th className="text-right px-4 py-2">4s</th>
                  <th className="text-right px-4 py-2">6s</th>
                </tr>
              </thead>
              <tbody>
                {seasonBatting.map((s, i) => (
                  <tr key={s.season} className={i % 2 === 0 ? "" : "bg-background/30"}>
                    <td className="px-4 py-2 font-mono">{s.season}</td>
                    <td className="text-right px-4 py-2 font-mono">{s.innings}</td>
                    <td className="text-right px-4 py-2 font-mono font-semibold">{s.total_runs}</td>
                    <td className="text-right px-4 py-2 font-mono">{s.highest_score}</td>
                    <td className="text-right px-4 py-2 font-mono text-muted">{s.avg_strike_rate}</td>
                    <td className="text-right px-4 py-2 font-mono text-muted">{s.fours}</td>
                    <td className="text-right px-4 py-2 font-mono text-muted">{s.sixes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-card border border-card-border rounded-lg px-4 py-3">
      <p className="text-xs text-muted uppercase tracking-wide">{label}</p>
      <p className="text-xl font-bold mt-1">{value}</p>
    </div>
  );
}
