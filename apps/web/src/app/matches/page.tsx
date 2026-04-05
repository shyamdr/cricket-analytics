import { fetchAPI } from "@/lib/api";
import { Match, SeasonCount } from "@/lib/types";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function MatchesPage({
  searchParams,
}: {
  searchParams: Promise<{ season?: string }>;
}) {
  const params = await searchParams;
  const season = params.season;

  const [seasons, matches] = await Promise.all([
    fetchAPI<SeasonCount[]>("/matches/seasons"),
    fetchAPI<Match[]>(
      season ? `/matches?season=${season}&limit=200` : "/matches?limit=50"
    ),
  ]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold mb-6">Matches</h1>

      {/* Season filter */}
      <div className="flex flex-wrap gap-2 mb-6">
        <Link
          href="/matches"
          className={`px-3 py-1 rounded-full text-sm border transition-colors ${
            !season
              ? "bg-accent text-background border-accent"
              : "border-card-border text-muted hover:text-foreground"
          }`}
        >
          All
        </Link>
        {seasons.map((s) => (
          <Link
            key={s.season}
            href={`/matches?season=${s.season}`}
            className={`px-3 py-1 rounded-full text-sm border transition-colors ${
              season === s.season
                ? "bg-accent text-background border-accent"
                : "border-card-border text-muted hover:text-foreground"
            }`}
          >
            {s.season} ({s.matches})
          </Link>
        ))}
      </div>

      {/* Match list */}
      <div className="space-y-2">
        {matches.map((m) => (
          <Link
            key={m.match_id}
            href={`/matches/${m.match_id}`}
            className="flex items-center justify-between bg-card border border-card-border rounded-lg px-4 py-3 hover:border-accent/50 transition-colors"
          >
            <div>
              <div className="flex items-center gap-2 text-sm">
                <span className={m.outcome_winner === m.team1 ? "font-semibold text-win" : ""}>
                  {m.team1}
                </span>
                <span className="text-muted">vs</span>
                <span className={m.outcome_winner === m.team2 ? "font-semibold text-win" : ""}>
                  {m.team2}
                </span>
                {m.event_stage && (
                  <span className="text-xs bg-accent-dim/30 text-accent px-2 py-0.5 rounded">
                    {m.event_stage}
                  </span>
                )}
              </div>
              <p className="text-xs text-muted mt-1">
                {m.venue}{m.city ? `, ${m.city}` : ""} · {m.match_date}
              </p>
            </div>
            <div className="text-right text-xs text-muted">
              {m.match_result_type === "no_result"
                ? "No Result"
                : m.winning_margin
                  ? `Won by ${m.winning_margin}`
                  : ""}
            </div>
          </Link>
        ))}
      </div>

      {matches.length === 0 && (
        <p className="text-muted text-center py-8">No matches found.</p>
      )}
    </div>
  );
}
