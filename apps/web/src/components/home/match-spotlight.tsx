"use client";

import { useState, useCallback, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { MapPin, Calendar, ArrowRight, ChevronLeft, ChevronRight, Star } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  type RecentMatch,
  formatMatchResult,
} from "@/lib/landing-utils";
import {
  getTeamLogoUrl,
  getTeamColor,
  getTeamGradientColor,
  getTeamAbbreviation,
  checkLogoClash,
  analyzeLogoClashAsync,
} from "@/lib/team-logos";

interface MatchSpotlightProps {
  matches: RecentMatch[];
}

export function MatchSpotlight({ matches }: MatchSpotlightProps) {
  const [index, setIndex] = useState(0);
  const [clashMap, setClashMap] = useState<Record<string, boolean>>({});

  const prev = useCallback(() => {
    setIndex((i) => (i === 0 ? matches.length - 1 : i - 1));
  }, [matches.length]);

  const next = useCallback(() => {
    setIndex((i) => (i === matches.length - 1 ? 0 : i + 1));
  }, [matches.length]);

  const match = matches[index];

  const inn1 = match?.innings?.find((i) => i.innings === 1);
  const inn2 = match?.innings?.find((i) => i.innings === 2);

  const team1Name = inn1?.batting_team ?? match?.team1 ?? "";
  const team2Name = inn2?.batting_team ?? match?.team2 ?? "";

  const team1Logo = getTeamLogoUrl(team1Name);
  const team2Logo = getTeamLogoUrl(team2Name);
  const team1Primary = getTeamColor(team1Name);
  const team2Primary = getTeamColor(team2Name);

  // Run canvas analysis when team/logo changes
  useEffect(() => {
    if (!match) return;

    const analyze = async () => {
      const updates: Record<string, boolean> = {};

      if (team1Logo) {
        const cached = checkLogoClash(team1Logo, team1Primary);
        if (cached === null) {
          updates[`${team1Name}`] = await analyzeLogoClashAsync(team1Logo, team1Primary);
        }
      }
      if (team2Logo) {
        const cached = checkLogoClash(team2Logo, team2Primary);
        if (cached === null) {
          updates[`${team2Name}`] = await analyzeLogoClashAsync(team2Logo, team2Primary);
        }
      }

      if (Object.keys(updates).length > 0) {
        setClashMap((prev) => ({ ...prev, ...updates }));
      }
    };

    analyze();
  }, [match, team1Name, team2Name, team1Logo, team2Logo, team1Primary, team2Primary]);

  if (!match || matches.length === 0) return null;

  const team1Clashes = clashMap[team1Name] ?? checkLogoClash(team1Logo ?? "", team1Primary) ?? false;
  const team2Clashes = clashMap[team2Name] ?? checkLogoClash(team2Logo ?? "", team2Primary) ?? false;

  const team1Color = getTeamGradientColor(team1Name, team1Clashes);
  const team2Color = getTeamGradientColor(team2Name, team2Clashes);

  const result = formatMatchResult(match);

  const formattedDate = match.match_date
    ? new Date(match.match_date).toLocaleDateString("en-US", {
        year: "numeric", month: "short", day: "numeric",
      })
    : null;

  const tossInfo = match.toss_winner && match.toss_decision
    ? `${match.toss_winner === team1Name || match.toss_winner === team2Name ? match.toss_winner : match.toss_winner} won toss · chose to ${match.toss_decision}`
    : null;

  const isTeam1Winner = match.outcome_winner === team1Name;
  const isTeam2Winner = match.outcome_winner === team2Name;

  return (
    <div className="w-full px-6 lg:px-10 py-6 animate-spotlight-fade-in">
      <div className="relative">
        {/* Left arrow */}
        <button
          type="button"
          onClick={prev}
          className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1/2 z-20 flex h-9 w-9 items-center justify-center rounded-full bg-background shadow-md ring-1 ring-border transition-colors hover:bg-secondary"
          aria-label="Previous match"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>

        {/* Right arrow */}
        <button
          type="button"
          onClick={next}
          className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 z-20 flex h-9 w-9 items-center justify-center rounded-full bg-background shadow-md ring-1 ring-border transition-colors hover:bg-secondary"
          aria-label="Next match"
        >
          <ChevronRight className="h-4 w-4" />
        </button>

        <Card className="overflow-hidden">
          <CardContent className="p-0">
            <div className="flex flex-col lg:flex-row items-stretch relative overflow-hidden">

              {/* Team 1 gradient — stops before center to leave a gap */}
              <div
                className="absolute inset-y-0 left-0 pointer-events-none transition-colors duration-300"
                style={{
                  width: "calc(50% - 6px)",
                  background: `linear-gradient(to left, ${team1Color} 0%, ${team1Color} 25%, transparent 55%)`,
                }}
              />
              {/* Team 2 gradient — stops before center to leave a gap */}
              <div
                className="absolute inset-y-0 right-0 pointer-events-none transition-colors duration-300"
                style={{
                  width: "calc(50% - 6px)",
                  background: `linear-gradient(to right, ${team2Color} 0%, ${team2Color} 25%, transparent 55%)`,
                }}
              />
              {/* Center divider — diamond VS handles the separation */}

              {/* Team 1 side */}
              <div className="flex-1 p-5 lg:p-6 flex flex-col items-center justify-center gap-1 relative overflow-hidden">
                <span className="text-lg lg:text-xl text-center text-foreground relative">
                  {team1Name}
                </span>
                <span className="text-3xl lg:text-4xl font-mono tabular-nums text-foreground relative">
                  {inn1 ? `${inn1.total_runs}/${inn1.total_wickets}` : "-"}
                </span>
                {inn1 && (
                  <span className="text-xs text-muted-foreground font-mono relative">({inn1.overs_played} overs)</span>
                )}
                {isTeam1Winner && match.player_of_match && (
                  <span className="text-[11px] text-muted-foreground flex items-center gap-1 mt-1 relative">
                    <Star className="h-3 w-3 text-amber-500 fill-amber-500" />
                    {match.player_of_match}
                  </span>
                )}
              </div>

              {/* Center — logo 1 | VS | logo 2 */}
              <div className="flex items-center justify-center gap-5 lg:gap-6 px-4 lg:px-6 py-3 lg:py-0 relative">
                {team1Logo ? (
                  <div className="h-[110px] w-[110px] lg:h-[140px] lg:w-[140px] p-2.5 lg:p-3 flex items-center justify-center">
                    <Image src={team1Logo} alt={team1Name} width={140} height={140} className="object-contain max-h-full max-w-full" />
                  </div>
                ) : (
                  <div className="h-[110px] w-[110px] lg:h-[140px] lg:w-[140px] rounded-full bg-white/20 flex items-center justify-center text-2xl font-semibold text-white">
                    {team1Name.slice(0, 2).toUpperCase()}
                  </div>
                )}

                <div className="flex flex-col items-center justify-center">
                  <span
                    className="text-3xl font-black tracking-tighter text-white select-none"
                    style={{
                      textShadow: "0 0 1px rgba(0,0,0,0.8), 0 0 3px rgba(0,0,0,0.5), 0 2px 6px rgba(0,0,0,0.4)",
                      WebkitTextStroke: "0.5px rgba(0,0,0,0.4)",
                    }}
                  >
                    VS
                  </span>
                </div>

                {team2Logo ? (
                  <div className="h-[110px] w-[110px] lg:h-[140px] lg:w-[140px] p-2.5 lg:p-3 flex items-center justify-center">
                    <Image src={team2Logo} alt={team2Name} width={140} height={140} className="object-contain max-h-full max-w-full" />
                  </div>
                ) : (
                  <div className="h-[110px] w-[110px] lg:h-[140px] lg:w-[140px] rounded-full bg-white/20 flex items-center justify-center text-2xl font-semibold text-white">
                    {team2Name.slice(0, 2).toUpperCase()}
                  </div>
                )}
              </div>

              {/* Team 2 side */}
              <div className="flex-1 p-5 lg:p-6 flex flex-col items-center justify-center gap-1 relative overflow-hidden">
                <span className="text-lg lg:text-xl text-center text-foreground relative">
                  {team2Name}
                </span>
                <span className="text-3xl lg:text-4xl font-mono tabular-nums text-foreground relative">
                  {inn2 ? `${inn2.total_runs}/${inn2.total_wickets}` : "-"}
                </span>
                {inn2 && (
                  <span className="text-xs text-muted-foreground font-mono relative">({inn2.overs_played} overs)</span>
                )}
                {isTeam2Winner && match.player_of_match && (
                  <span className="text-[11px] text-muted-foreground flex items-center gap-1 mt-1 relative">
                    <Star className="h-3 w-3 text-amber-500 fill-amber-500" />
                    {match.player_of_match}
                  </span>
                )}
              </div>
            </div>

            {/* Bottom bar */}
            <div className="border-t border-border px-6 lg:px-8 py-3 flex flex-col sm:flex-row items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-3">
                {match.event_name && (
                  <Badge variant="secondary">
                    {match.event_name}
                    {match.event_stage ? ` · ${match.event_stage}` : ""}
                  </Badge>
                )}
                {result && (
                  <span className="text-sm font-semibold text-primary">{result}</span>
                )}
                {tossInfo && (
                  <span className="text-xs text-muted-foreground">· {tossInfo}</span>
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
                <span className="text-xs text-muted-foreground font-mono">
                  {index + 1}/{matches.length}
                </span>
                <Button variant="outline" size="sm" nativeButton={false} render={<Link href={`/matches/${match.match_id}`} />}>
                  Scorecard
                  <ArrowRight className="h-3.5 w-3.5 ml-1" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
