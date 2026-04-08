import Link from "next/link";
import { ArrowRight, Calendar } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  type RecentMatch,
  shortName,
  formatMatchResult,
} from "@/lib/landing-utils";

interface LatestResultsProps {
  matches: RecentMatch[];
}

export function LatestResults({ matches }: LatestResultsProps) {
  if (matches.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Latest Results</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-muted-foreground gap-2">
            <Calendar className="h-8 w-8" />
            <p className="text-sm">No recent matches</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const displayMatches = matches.slice(0, 6);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Latest Results</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-0">
        {displayMatches.map((match, idx) => (
          <MatchResultRow
            key={match.match_id}
            match={match}
            isLast={idx === displayMatches.length - 1}
          />
        ))}
        <div className="pt-3">
          <Button variant="ghost" size="sm" nativeButton={false} render={<Link href="/matches" />} className="w-full">
            View All Matches
            <ArrowRight className="h-3.5 w-3.5 ml-1" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function MatchResultRow({ match, isLast }: { match: RecentMatch; isLast: boolean }) {
  const inn1 = match.innings?.find((i) => i.innings === 1);
  const inn2 = match.innings?.find((i) => i.innings === 2);

  const team1Name = inn1?.batting_team ?? match.team1;
  const team2Name = inn2?.batting_team ?? match.team2;

  const isTeam1Winner = match.outcome_winner === team1Name;
  const isTeam2Winner = match.outcome_winner === team2Name;
  const isNoResult = match.match_result_type === "no_result";

  const result = formatMatchResult(match);

  return (
    <Link
      href={`/matches/${match.match_id}`}
      className={`block py-3 -mx-2 px-2 rounded-md transition-colors hover:bg-muted/50 ${
        !isLast ? "border-b border-border/50" : ""
      }`}
    >
      <div className="flex items-center justify-between text-sm">
        <span className={isTeam1Winner ? "font-semibold text-foreground" : "text-muted-foreground"}>
          {shortName(team1Name)}
        </span>
        <div className="flex items-center gap-1.5">
          <span className={`font-mono tabular-nums text-xs ${isTeam1Winner ? "font-semibold text-foreground" : "text-muted-foreground"}`}>
            {inn1 ? `${inn1.total_runs}/${inn1.total_wickets}` : "-"}
          </span>
          {inn1 && <span className="text-[10px] text-muted-foreground font-mono">({inn1.overs_played})</span>}
        </div>
      </div>
      <div className="flex items-center justify-between text-sm mt-1">
        <span className={isTeam2Winner ? "font-semibold text-foreground" : "text-muted-foreground"}>
          {shortName(team2Name)}
        </span>
        <div className="flex items-center gap-1.5">
          <span className={`font-mono tabular-nums text-xs ${isTeam2Winner ? "font-semibold text-foreground" : "text-muted-foreground"}`}>
            {inn2 ? `${inn2.total_runs}/${inn2.total_wickets}` : "-"}
          </span>
          {inn2 && <span className="text-[10px] text-muted-foreground font-mono">({inn2.overs_played})</span>}
        </div>
      </div>
      <div className="flex items-center gap-2 mt-1.5">
        <Badge variant="secondary" className="text-[10px] px-1.5 h-4">
          {isNoResult ? "NO RES" : "RESULT"}
        </Badge>
        {result && <span className="text-xs text-primary">{result}</span>}
      </div>
    </Link>
  );
}
