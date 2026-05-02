"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

interface Matchup {
  batter: string;
  bowler: string;
  balls_faced: number;
  runs_scored: number;
  dismissals: number;
  strike_rate: number;
  dot_ball_percentage: number;
  boundary_percentage: number;
  average: number | null;
  fours: number;
  sixes: number;
  matches: number;
}

interface MatchupTableProps {
  matchups: Matchup[];
  team1: string;
  team2: string;
}

export function MatchupTable({ matchups, team1, team2 }: MatchupTableProps) {
  if (!matchups.length) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground text-sm">
          No historical matchup data available for these playing XIs.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm text-muted-foreground uppercase tracking-wide">
          Key Batter vs Bowler Matchups — {team1} vs {team2}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Batter</TableHead>
              <TableHead>Bowler</TableHead>
              <TableHead className="text-right">Balls</TableHead>
              <TableHead className="text-right">Runs</TableHead>
              <TableHead className="text-right">Outs</TableHead>
              <TableHead className="text-right">SR</TableHead>
              <TableHead className="text-right">Dot%</TableHead>
              <TableHead className="text-right">Bnd%</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {matchups.slice(0, 20).map((m) => (
              <TableRow key={`${m.batter}-${m.bowler}`}>
                <TableCell className="text-foreground font-medium text-sm">{m.batter}</TableCell>
                <TableCell className="text-foreground text-sm">{m.bowler}</TableCell>
                <TableCell className="text-right font-mono text-sm">{m.balls_faced}</TableCell>
                <TableCell className="text-right font-mono text-sm font-semibold">{m.runs_scored}</TableCell>
                <TableCell className="text-right font-mono text-sm">{m.dismissals}</TableCell>
                <TableCell className="text-right font-mono text-sm">{m.strike_rate}</TableCell>
                <TableCell className="text-right font-mono text-sm text-muted-foreground">{m.dot_ball_percentage}</TableCell>
                <TableCell className="text-right font-mono text-sm text-muted-foreground">{m.boundary_percentage}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
