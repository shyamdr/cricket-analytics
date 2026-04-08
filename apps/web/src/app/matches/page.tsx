"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Spinner } from "@/components/loading";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Match {
  match_id: string;
  season: string;
  match_date: string;
  city: string | null;
  venue: string;
  team1: string;
  team2: string;
  outcome_winner: string | null;
  match_result_type: string;
  winning_margin: string | null;
  event_stage: string | null;
}

interface SeasonCount {
  season: string;
  matches: number;
}

const API = process.env.NEXT_PUBLIC_API_URL || "";

export default function MatchesPageWrapper() {
  return (
    <Suspense fallback={<Spinner className="py-16" />}>
      <MatchesPage />
    </Suspense>
  );
}

function MatchesPage() {
  const searchParams = useSearchParams();
  const season = searchParams.get("season") || "";

  const [seasons, setSeasons] = useState<SeasonCount[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const matchUrl = season
      ? `${API}/api/v1/matches?season=${season}&limit=200`
      : `${API}/api/v1/matches?limit=50`;

    Promise.all([
      fetch(`${API}/api/v1/matches/seasons`).then((r) => r.json()),
      fetch(matchUrl).then((r) => r.json()),
    ])
      .then(([s, m]) => {
        setSeasons(s);
        setMatches(m);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [season]);

  return (
    <div className="w-full px-6 lg:px-10 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-semibold text-foreground">Matches</h1>
        {!loading && matches.length > 0 && (
          <span className="text-sm text-muted-foreground">{matches.length} matches</span>
        )}
      </div>

      <div className="flex flex-wrap gap-2 mb-6">
        <Link
          href="/matches"
          className={`px-3 py-1 rounded-full text-sm border transition-colors ${
            !season
              ? "bg-primary text-primary-foreground border-primary"
              : "border-border text-muted-foreground hover:text-foreground"
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
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            {s.season} ({s.matches})
          </Link>
        ))}
      </div>

      {loading ? (
        <Spinner />
      ) : matches.length === 0 ? (
        <p className="text-muted-foreground text-center py-8">
          {seasons.length === 0 ? "API is waking up... refresh in a moment." : "No matches found."}
        </p>
      ) : (
        <div className="space-y-2">
          {matches.map((m) => (
            <Link
              key={m.match_id}
              href={`/matches/${m.match_id}`}
              className="block"
            >
              <Card className="transition-all hover:shadow-md hover:border-primary/30">
                <CardContent className="flex items-center justify-between py-3 px-4">
                  <div>
                    <div className="flex items-center gap-2 text-sm text-foreground">
                      <span className={m.outcome_winner === m.team1 ? "font-semibold text-primary" : ""}>{m.team1}</span>
                      <span className="text-muted-foreground">vs</span>
                      <span className={m.outcome_winner === m.team2 ? "font-semibold text-primary" : ""}>{m.team2}</span>
                      {m.event_stage && (
                        <Badge variant="secondary" className="text-[10px]">{m.event_stage}</Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {m.venue}{m.city ? `, ${m.city}` : ""} · {m.match_date}
                    </p>
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    {m.match_result_type === "no_result" ? "No Result" : m.winning_margin ? `Won by ${m.winning_margin}` : ""}
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
