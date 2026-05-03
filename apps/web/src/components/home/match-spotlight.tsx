"use client";

import { useState, useCallback, useEffect, useMemo } from "react";
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
  checkLogoClash,
  analyzeLogoClashAsync,
} from "@/lib/team-logos";

interface MatchSpotlightProps {
  matches: RecentMatch[];
}

export function MatchSpotlight({ matches }: MatchSpotlightProps) {
  const [activeFilter, setActiveFilter] = useState("all");
  const [index, setIndex] = useState(0);
  const [clashMap, setClashMap] = useState<Record<string, boolean>>({});
  const [transitioning, setTransitioning] = useState(false);
  const [slideDir, setSlideDir] = useState<"left" | "right">("left");

  // Build tournament tabs from match data
  const tournamentCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const m of matches) {
      const key = m.event_name ?? "Other";
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    // Sort by count descending
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [matches]);

  const filtered = activeFilter === "all"
    ? matches
    : matches.filter((m) => (m.event_name ?? "Other") === activeFilter);

  // Reset index when filter changes
  useEffect(() => {
    setIndex(0);
  }, [activeFilter]);

  const navigate = useCallback((dir: "left" | "right") => {
    setSlideDir(dir);
    setTransitioning(true);
    setTimeout(() => {
      setIndex((i) => {
        if (dir === "left") return i === filtered.length - 1 ? 0 : i + 1;
        return i === 0 ? filtered.length - 1 : i - 1;
      });
      setTransitioning(false);
    }, 200);
  }, [filtered.length]);

  const prev = useCallback(() => navigate("right"), [navigate]);
  const next = useCallback(() => navigate("left"), [navigate]);

  const match = filtered[index];

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

  if (!match || filtered.length === 0) return null;

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
      {/* Tournament filter tabs */}
      <div className="flex flex-wrap gap-2 mb-4">
          <button
            type="button"
            onClick={() => setActiveFilter("all")}
            className={`px-3 py-1 rounded-full text-xs border transition-colors ${
              activeFilter === "all"
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border text-muted-foreground hover:text-foreground hover:bg-accent"
            }`}
          >
            All ({matches.length})
          </button>
          {tournamentCounts.map(([name, count]) => (
            <button
              key={name}
              type="button"
              onClick={() => setActiveFilter(name)}
              className={`px-3 py-1 rounded-full text-xs border transition-colors ${
                activeFilter === name
                  ? "bg-primary text-primary-foreground border-primary"
                  : "border-border text-muted-foreground hover:text-foreground hover:bg-accent"
              }`}
            >
              {name.length > 25 ? name.slice(0, 23) + "…" : name} ({count})
            </button>
          ))}
        </div>

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
            <div
              className="flex flex-col lg:flex-row items-stretch relative overflow-hidden min-h-[160px] lg:min-h-[180px] transition-all duration-200 ease-out"
              style={{
                opacity: transitioning ? 0 : 1,
                transform: transitioning
                  ? `translateX(${slideDir === "left" ? "-30px" : "30px"})`
                  : "translateX(0)",
              }}
            >

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
              <div className="flex-1 py-6 pl-4 pr-20 lg:pr-24 grid grid-cols-[180px] justify-end items-center relative overflow-hidden">
                <div className="flex flex-col items-center">
                  <Link href={`/teams/${encodeURIComponent(team1Name)}`} className="text-base lg:text-lg text-center text-foreground whitespace-nowrap hover:text-primary transition-colors">{team1Name}</Link>
                  <span className="text-2xl lg:text-3xl font-mono tabular-nums text-foreground">{inn1 ? `${inn1.total_runs}/${inn1.total_wickets}` : "-"}</span>
                  <span className="text-xs text-muted-foreground font-mono h-5">{inn1 ? `(${inn1.overs_played} ov)` : "\u00A0"}</span>
                  <span className="text-xs text-muted-foreground flex items-center gap-1 h-5">
                    {isTeam1Winner && match.player_of_match ? (<><Star className="h-2.5 w-2.5 text-amber-500 fill-amber-500" /><Link href={`/players/${encodeURIComponent(match.player_of_match)}`} className="hover:text-primary transition-colors">{match.player_of_match}</Link></>) : "\u00A0"}
                  </span>
                </div>
              </div>

              {/* Center — logo 1 | VS | logo 2 */}
              <div className="flex items-center justify-center gap-6 lg:gap-8 px-4 lg:px-6 py-3 lg:py-0 relative">
                {team1Logo ? (
                  <Link href={`/teams/${encodeURIComponent(team1Name)}`} className="h-[130px] w-[130px] lg:h-[160px] lg:w-[160px] p-2.5 lg:p-3 flex items-center justify-center transition-transform duration-200 hover:scale-110 hover:drop-shadow-lg relative overflow-visible">
                    <img src={team1Logo} alt={team1Name} className="object-contain max-h-full max-w-full relative" />
                  </Link>
                ) : (
                  <Link href={`/teams/${encodeURIComponent(team1Name)}`} className="h-[130px] w-[130px] lg:h-[160px] lg:w-[160px] rounded-full bg-white/20 flex items-center justify-center text-2xl font-semibold text-white transition-transform duration-200 hover:scale-110 hover:drop-shadow-lg relative overflow-visible">
                    {team1Name.slice(0, 2).toUpperCase()}
                  </Link>
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
                  <Link href={`/teams/${encodeURIComponent(team2Name)}`} className="h-[130px] w-[130px] lg:h-[160px] lg:w-[160px] p-2.5 lg:p-3 flex items-center justify-center transition-transform duration-200 hover:scale-110 hover:drop-shadow-lg relative overflow-visible">
                    <img src={team2Logo} alt={team2Name} className="object-contain max-h-full max-w-full relative" />
                  </Link>
                ) : (
                  <Link href={`/teams/${encodeURIComponent(team2Name)}`} className="h-[130px] w-[130px] lg:h-[160px] lg:w-[160px] rounded-full bg-white/20 flex items-center justify-center text-2xl font-semibold text-white transition-transform duration-200 hover:scale-110 hover:drop-shadow-lg relative overflow-visible">
                    {team2Name.slice(0, 2).toUpperCase()}
                  </Link>
                )}
              </div>

              {/* Team 2 side */}
              <div className="flex-1 py-6 pr-4 pl-20 lg:pl-24 grid grid-cols-[180px] justify-start items-center relative overflow-hidden">
                <div className="flex flex-col items-center">
                  <Link href={`/teams/${encodeURIComponent(team2Name)}`} className="text-base lg:text-lg text-center text-foreground whitespace-nowrap hover:text-primary transition-colors">{team2Name}</Link>
                  <span className="text-2xl lg:text-3xl font-mono tabular-nums text-foreground">{inn2 ? `${inn2.total_runs}/${inn2.total_wickets}` : "-"}</span>
                  <span className="text-xs text-muted-foreground font-mono h-5">{inn2 ? `(${inn2.overs_played} ov)` : "\u00A0"}</span>
                  <span className="text-xs text-muted-foreground flex items-center gap-1 h-5">
                    {isTeam2Winner && match.player_of_match ? (<><Star className="h-2.5 w-2.5 text-amber-500 fill-amber-500" /><Link href={`/players/${encodeURIComponent(match.player_of_match)}`} className="hover:text-primary transition-colors">{match.player_of_match}</Link></>) : "\u00A0"}
                  </span>
                </div>
              </div>
            </div>

            {/* Bottom bar */}
            <div className="border-t border-border px-6 lg:px-8 py-3 flex flex-col sm:flex-row items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-3">
                {match.event_name && (
                  <Link href={`/matches?season=${match.season}`}>
                    <Badge variant="secondary" className="hover:bg-secondary/80 transition-colors cursor-pointer">
                      {match.event_name}
                      {match.event_stage ? ` · ${match.event_stage}` : ""}
                    </Badge>
                  </Link>
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
                    <Link href={`/venues`} className="flex items-center gap-1 hover:text-primary transition-colors">
                      <MapPin className="h-3 w-3" />
                      {match.venue?.split(",")[0]}
                      {match.city ? `, ${match.city}` : ""}
                    </Link>
                  )}
                  {formattedDate && (
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {formattedDate}
                    </span>
                  )}
                </div>
                <span className="text-xs text-muted-foreground font-mono">
                  {index + 1}/{filtered.length}
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
