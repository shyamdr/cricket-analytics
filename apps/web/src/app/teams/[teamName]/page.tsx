"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Spinner } from "@/components/loading";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface Team { team_name: string; current_franchise_name: string | null; total_matches: number; }
interface Match { match_id: string; match_date: string; venue: string; team1: string; team2: string; outcome_winner: string | null; winning_margin: string | null; }

const API = process.env.NEXT_PUBLIC_API_URL || "";

export default function TeamDetailPage() {
  const params = useParams();
  const name = decodeURIComponent(params.teamName as string);

  const [team, setTeam] = useState<Team | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const encoded = encodeURIComponent(name);
    Promise.all([
      fetch(`${API}/api/v1/teams/${encoded}`).then((r) => r.json()),
      fetch(`${API}/api/v1/teams/${encoded}/matches?limit=50`).then((r) => r.json()),
    ])
      .then(([t, m]) => { setTeam(t); setMatches(m); setLoading(false); })
      .catch(() => setLoading(false));
  }, [name]);

  if (loading) return <Spinner className="py-16" />;
  if (!team) {
    return (
      <div className="w-full px-6 lg:px-10 py-16 text-center">
        <p className="text-muted-foreground">Team &quot;{name}&quot; not found.</p>
        <Button variant="ghost" size="sm" nativeButton={false} render={<Link href="/teams" />} className="mt-2">
          <ArrowLeft className="h-4 w-4 mr-1" />Back to teams
        </Button>
      </div>
    );
  }

  const wins = matches.filter((m) => m.outcome_winner === name).length;
  const losses = matches.filter((m) => m.outcome_winner && m.outcome_winner !== name).length;

  return (
    <div className="w-full px-6 lg:px-10 py-8">
      <Button variant="ghost" size="sm" nativeButton={false} render={<Link href="/teams" />} className="-ml-2 mb-2">
        <ArrowLeft className="h-4 w-4 mr-1" />Back to teams
      </Button>
      <h1 className="text-3xl font-semibold text-foreground mb-1">{team.team_name}</h1>
      {team.current_franchise_name && team.current_franchise_name !== team.team_name && (
        <p className="text-muted-foreground mb-4">Now: {team.current_franchise_name}</p>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
        <Card>
          <CardContent className="pt-4 pb-3 px-4">
            <p className="text-xs text-muted-foreground uppercase">Matches</p>
            <p className="text-2xl font-semibold text-foreground mt-1 font-mono">{team.total_matches}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3 px-4">
            <p className="text-xs text-muted-foreground uppercase">Won</p>
            <p className="text-2xl font-semibold text-primary mt-1 font-mono">{wins}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3 px-4">
            <p className="text-xs text-muted-foreground uppercase">Lost</p>
            <p className="text-2xl font-semibold text-destructive mt-1 font-mono">{losses}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3 px-4">
            <p className="text-xs text-muted-foreground uppercase">Win %</p>
            <p className="text-2xl font-semibold text-foreground mt-1 font-mono">
              {matches.length > 0 ? Math.round((wins / matches.length) * 100) : 0}%
            </p>
          </CardContent>
        </Card>
      </div>

      <h2 className="text-xl font-semibold text-foreground mb-4">Recent Matches</h2>
      <div className="space-y-2">
        {matches.map((m) => {
          const opponent = m.team1 === name ? m.team2 : m.team1;
          const won = m.outcome_winner === name;
          const lost = m.outcome_winner && m.outcome_winner !== name;
          return (
            <Link key={m.match_id} href={`/matches/${m.match_id}`} className="block">
              <Card className="transition-all hover:shadow-md hover:border-primary/30">
                <CardContent className="flex items-center justify-between py-3 px-4">
                  <div>
                    <div className="flex items-center gap-2 text-sm text-foreground">
                      <span>vs {opponent}</span>
                      {won && <Badge className="bg-primary/10 text-primary border-primary/20 text-[10px] h-4 px-1.5">W</Badge>}
                      {lost && <Badge className="bg-destructive/10 text-destructive border-destructive/20 text-[10px] h-4 px-1.5">L</Badge>}
                      {!won && !lost && <Badge variant="secondary" className="text-[10px] h-4 px-1.5">NR</Badge>}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{m.venue?.split(",")[0]} · {m.match_date}</p>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {m.winning_margin ? `by ${m.winning_margin}` : ""}
                  </div>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
