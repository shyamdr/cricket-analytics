"use client";

import Link from "next/link";
import { MapPin, Calendar, ArrowRight, Trophy } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  type RecentMatch,
  formatMatchResult,
} from "@/lib/landing-utils";

interface MatchSpotlightProps {
  match: RecentMatch | null;
}

export function MatchSpotlight({ match }: MatchSpotlightProps) {
  if (!match) return null;

  const inn1 = match.innings?.find((i) => i.innings === 1);
  const inn2 = match.innings?.find((i) => i.innings === 2);

  const team1Name = inn1?.batting_team ?? match.team1;
  const team2Name = inn2?.batting_team ?? match.team2;

  const isTeam1Winner = match.outcome_winner === team1Name;
  const isTeam2Winner = match.outcome_winner === team2Name;

  const result = formatMatchResult(match);

  const formattedDate = match.match_date
    ? new Date(match.match_date).toLocaleDateString("en-US", {
        year: "numeric", month: "long", day: "numeric",
      })
    : null;

  return (
    <div className="w-full px-6 lg:px-10 py-6 animate-spotlight-fade-in">
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          <div className="flex flex-col lg:flex-row">
            {/* Team 1 side */}
            <div className={`flex-1 p-6 lg:p-8 flex flex-col items-center justify-center gap-2 ${isTeam1Winner ? "bg-primary/5" : ""}`}>
              {isTeam1Winner && <Trophy className="h-4 w-4 text-primary mb-1" />}
              <span className={`text-lg lg:text-xl ${isTeam1Winner ? "font-semibold text-foreground" : "text-muted-foreground"}`}>
                {team1Name}
              </span>
              <span className={`text-3xl lg:text-4xl font-mono tabular-nums ${isTeam1Winner ? "font-semibold text-foreground" : "text-muted-foreground"}`}>
                {inn1 ? `${inn1.total_runs}/${inn1.total_wickets}` : "-"}
              </span>
              {inn1 && (
                <span className="text-xs text-muted-foreground font-mono">({inn1.overs_played} overs)</span>
              )}
            </div>

            {/* Center divider */}
            <div className="flex items-center justify-center px-4 py-2 lg:py-0">
              <div className="flex flex-col items-center gap-2">
                <Separator className="h-8 hidden lg:block" orientation="vertical" />
                <span className="text-xs font-medium text-muted-foreground bg-muted rounded-full px-3 py-1">VS</span>
                <Separator className="h-8 hidden lg:block" orientation="vertical" />
              </div>
            </div>

            {/* Team 2 side */}
            <div className={`flex-1 p-6 lg:p-8 flex flex-col items-center justify-center gap-2 ${isTeam2Winner ? "bg-primary/5" : ""}`}>
              {isTeam2Winner && <Trophy className="h-4 w-4 text-primary mb-1" />}
              <span className={`text-lg lg:text-xl ${isTeam2Winner ? "font-semibold text-foreground" : "text-muted-foreground"}`}>
                {team2Name}
              </span>
              <span className={`text-3xl lg:text-4xl font-mono tabular-nums ${isTeam2Winner ? "font-semibold text-foreground" : "text-muted-foreground"}`}>
                {inn2 ? `${inn2.total_runs}/${inn2.total_wickets}` : "-"}
              </span>
              {inn2 && (
                <span className="text-xs text-muted-foreground font-mono">({inn2.overs_played} overs)</span>
              )}
            </div>
          </div>

          {/* Bottom bar — result, venue, date, link */}
          <div className="border-t border-border px-6 lg:px-8 py-4 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-3">
              {match.event_name && (
                <Badge variant="secondary">
                  {match.event_name}
                  {match.event_stage ? ` · ${match.event_stage}` : ""}
                </Badge>
              )}
              {result && (
                <span className="text-sm font-medium text-primary">{result}</span>
              )}
            </div>
            <div className="flex items-center gap-4">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                {(match.venue || match.city) && (
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3 w-3" />
                    {match.venue?.split(",")[0]}
                    {match.city ? `, ${match.city}` : ""}
                  </span>
                )}
                {formattedDate && (
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {formattedDate}
                  </span>
                )}
              </div>
              <Button variant="outline" size="sm" nativeButton={false} render={<Link href={`/matches/${match.match_id}`} />}>
                Scorecard
                <ArrowRight className="h-3.5 w-3.5 ml-1" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
