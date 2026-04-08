"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, MapPin, Calendar as CalendarIcon } from "lucide-react";
import { Spinner } from "@/components/loading";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";

interface Match {
  match_id: string; team1: string; team2: string; venue: string;
  city: string | null; match_date: string; toss_winner: string;
  toss_decision: string; outcome_winner: string | null;
  winning_margin: string | null; match_result_type: string;
  event_name: string | null; event_stage: string | null;
}
interface MatchSummary {
  innings: number; batting_team: string; total_runs: number;
  total_wickets: number; overs_played: number; run_rate: number;
  total_fours: number; total_sixes: number;
}
interface BattingInnings {
  innings: number; batting_team: string; batter: string;
  runs_scored: number; balls_faced: number; fours: number;
  sixes: number; strike_rate: number; is_out: boolean;
  dismissal_kind: string | null; dismissed_by: string | null;
}
interface BowlingInnings {
  innings: number; batting_team: string; bowler: string;
  overs_bowled: number; runs_conceded: number; wickets: number;
  economy_rate: number;
}

const API = process.env.NEXT_PUBLIC_API_URL || "";

export default function MatchDetailPage() {
  const params = useParams();
  const matchId = params.matchId as string;
  const [match, setMatch] = useState<Match | null>(null);
  const [summary, setSummary] = useState<MatchSummary[]>([]);
  const [batting, setBatting] = useState<BattingInnings[]>([]);
  const [bowling, setBowling] = useState<BowlingInnings[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/v1/matches/${matchId}`).then((r) => r.json()),
      fetch(`${API}/api/v1/matches/${matchId}/summary`).then((r) => r.json()),
      fetch(`${API}/api/v1/matches/${matchId}/batting`).then((r) => r.json()),
      fetch(`${API}/api/v1/matches/${matchId}/bowling`).then((r) => r.json()),
    ]).then(([m, s, bat, bowl]) => {
      setMatch(m); setSummary(s); setBatting(bat); setBowling(bowl); setLoading(false);
    }).catch(() => { setError(true); setLoading(false); });
  }, [matchId]);

  if (loading) return <Spinner className="py-16" />;
  if (error || !match) {
    return (
      <div className="w-full px-6 lg:px-10 py-16 text-center">
        <p className="text-muted-foreground">Could not load match. API may be waking up.</p>
        <Button variant="ghost" size="sm" nativeButton={false} render={<Link href="/matches" />}>
          <ArrowLeft className="h-4 w-4 mr-1" />Back to matches
        </Button>
      </div>
    );
  }

  const formattedDate = new Date(match.match_date).toLocaleDateString("en-US", {
    year: "numeric", month: "long", day: "numeric",
  });

  return (
    <div className="w-full px-6 lg:px-10 py-8 space-y-6">
      {/* Back link */}
      <Button variant="ghost" size="sm" nativeButton={false} render={<Link href="/matches" />} className="-ml-2">
        <ArrowLeft className="h-4 w-4 mr-1" />Back to matches
      </Button>

      {/* Match header card */}
      <Card>
        <CardContent className="pt-6 space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            {match.event_name && <Badge variant="secondary">{match.event_name}</Badge>}
            {match.event_stage && <Badge variant="outline">{match.event_stage}</Badge>}
          </div>
          <h1 className="text-2xl font-semibold text-foreground">
            <span className={match.outcome_winner === match.team1 ? "text-primary" : ""}>{match.team1}</span>
            <span className="text-muted-foreground mx-2">vs</span>
            <span className={match.outcome_winner === match.team2 ? "text-primary" : ""}>{match.team2}</span>
          </h1>
          <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
            <span className="flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{match.venue}{match.city ? `, ${match.city}` : ""}</span>
            <span className="flex items-center gap-1"><CalendarIcon className="h-3.5 w-3.5" />{formattedDate}</span>
          </div>
          <Separator />
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <span className="text-foreground">Toss: {match.toss_winner} chose to {match.toss_decision}</span>
            {match.winning_margin && (
              <Badge className="bg-primary/10 text-primary border-primary/20">{match.outcome_winner} won by {match.winning_margin}</Badge>
            )}
            {match.match_result_type === "no_result" && <Badge variant="secondary">No Result</Badge>}
          </div>
        </CardContent>
      </Card>

      {/* Innings summary cards */}
      <div className="grid sm:grid-cols-2 gap-4">
        {summary.map((s) => (
          <Card key={s.innings}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-foreground">{s.batting_team}</h3>
                <div className="text-right">
                  <span className="text-2xl font-semibold font-mono text-foreground">{s.total_runs}/{s.total_wickets}</span>
                  <span className="text-sm text-muted-foreground ml-1.5">({s.overs_played} ov)</span>
                </div>
              </div>
              <div className="flex gap-4 text-xs text-muted-foreground">
                <span>RR: {s.run_rate}</span>
                <Separator orientation="vertical" className="h-3" />
                <span>4s: {s.total_fours}</span>
                <Separator orientation="vertical" className="h-3" />
                <span>6s: {s.total_sixes}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Scorecard per innings */}
      {summary.map((s) => {
        const innBatting = batting.filter((b) => b.innings === s.innings);
        const innBowling = bowling.filter((b) => b.innings === s.innings);
        return (
          <div key={s.innings} className="space-y-4">
            <h2 className="text-lg font-semibold text-foreground">
              {s.batting_team} — {s.total_runs}/{s.total_wickets} ({s.overs_played} ov)
            </h2>

            {/* Batting */}
            <Card>
              <CardHeader className="pb-0">
                <CardTitle className="text-sm text-muted-foreground uppercase tracking-wide">Batting</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Batter</TableHead>
                      <TableHead className="text-right">R</TableHead>
                      <TableHead className="text-right">B</TableHead>
                      <TableHead className="text-right">4s</TableHead>
                      <TableHead className="text-right">6s</TableHead>
                      <TableHead className="text-right">SR</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {innBatting.map((b) => (
                      <TableRow key={`${b.batter}-${s.innings}`}>
                        <TableCell>
                          <Link href={`/players/${encodeURIComponent(b.batter)}`} className="hover:text-primary transition-colors text-foreground">
                            {b.batter}
                          </Link>
                          {b.dismissal_kind && (
                            <span className="text-xs text-muted-foreground ml-2">{b.dismissal_kind}{b.dismissed_by ? ` b ${b.dismissed_by}` : ""}</span>
                          )}
                          {!b.is_out && <span className="text-xs text-primary ml-2">not out</span>}
                        </TableCell>
                        <TableCell className="text-right font-mono font-semibold">{b.runs_scored}</TableCell>
                        <TableCell className="text-right font-mono text-muted-foreground">{b.balls_faced}</TableCell>
                        <TableCell className="text-right font-mono text-muted-foreground">{b.fours}</TableCell>
                        <TableCell className="text-right font-mono text-muted-foreground">{b.sixes}</TableCell>
                        <TableCell className="text-right font-mono text-muted-foreground">{b.strike_rate}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            {/* Bowling */}
            <Card>
              <CardHeader className="pb-0">
                <CardTitle className="text-sm text-muted-foreground uppercase tracking-wide">Bowling</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Bowler</TableHead>
                      <TableHead className="text-right">O</TableHead>
                      <TableHead className="text-right">R</TableHead>
                      <TableHead className="text-right">W</TableHead>
                      <TableHead className="text-right">Econ</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {innBowling.map((b) => (
                      <TableRow key={`${b.bowler}-${s.innings}`}>
                        <TableCell>
                          <Link href={`/players/${encodeURIComponent(b.bowler)}`} className="hover:text-primary transition-colors text-foreground">
                            {b.bowler}
                          </Link>
                        </TableCell>
                        <TableCell className="text-right font-mono">{b.overs_bowled}</TableCell>
                        <TableCell className="text-right font-mono">{b.runs_conceded}</TableCell>
                        <TableCell className="text-right font-mono font-semibold">{b.wickets}</TableCell>
                        <TableCell className="text-right font-mono text-muted-foreground">{b.economy_rate}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        );
      })}
    </div>
  );
}
