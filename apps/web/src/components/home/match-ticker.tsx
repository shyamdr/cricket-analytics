"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight, MapPin } from "lucide-react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  type RecentMatch,
  shortName,
  formatMatchResult,
  groupMatchesByTournament,
} from "@/lib/landing-utils";

interface MatchTickerProps {
  matches: RecentMatch[];
}

function abbreviateLabel(name: string): string {
  if (name === "Indian Premier League") return "IPL";
  return name.length > 20 ? name.slice(0, 18) + "…" : name;
}

export function MatchTicker({ matches }: MatchTickerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState("all");

  const tournamentGroups = groupMatchesByTournament(matches);

  const tabs = [
    { id: "all", label: `All (${matches.length})` },
    ...Array.from(tournamentGroups.entries()).map(([name, group]) => ({
      id: name,
      label: `${abbreviateLabel(name)} (${group.length})`,
    })),
  ];

  const filtered =
    activeTab === "all"
      ? matches
      : matches.filter((m) => (m.event_name ?? "Other") === activeTab);

  function scroll(direction: "left" | "right") {
    const container = scrollRef.current;
    if (!container) return;
    const scrollAmount = 400;
    const current = container.scrollLeft;
    const target =
      direction === "left"
        ? Math.max(0, current - scrollAmount)
        : Math.min(
            container.scrollWidth - container.clientWidth,
            current + scrollAmount,
          );
    container.scrollTo({ left: target, behavior: "smooth" });
  }

  return (
    <div className="w-full border-b border-border bg-secondary/50">
      <div className="w-full px-6 lg:px-10 py-3">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="h-8 mb-3">
            {tabs.map((tab) => (
              <TabsTrigger key={tab.id} value={tab.id} className="text-xs px-3">
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        <div className="relative">
          <button
            type="button"
            onClick={() => scroll("left")}
            className="absolute left-0 top-1/2 -translate-y-1/2 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-background shadow-md ring-1 ring-border transition-colors hover:bg-secondary"
            aria-label="Scroll left"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>

          <div
            ref={scrollRef}
            className="flex gap-3 overflow-x-auto scroll-smooth px-10 pb-1"
            style={{ scrollbarWidth: "none" }}
          >
            {filtered.map((match) => (
              <TickerCard key={match.match_id} match={match} />
            ))}
          </div>

          <button
            type="button"
            onClick={() => scroll("right")}
            className="absolute right-0 top-1/2 -translate-y-1/2 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-background shadow-md ring-1 ring-border transition-colors hover:bg-secondary"
            aria-label="Scroll right"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

function TickerCard({ match }: { match: RecentMatch }) {
  const inn1 = match.innings?.find((i) => i.innings === 1);
  const inn2 = match.innings?.find((i) => i.innings === 2);

  const team1Name = inn1?.batting_team ?? match.team1;
  const team2Name = inn2?.batting_team ?? match.team2;

  const isTeam1Winner = match.outcome_winner === team1Name;
  const isTeam2Winner = match.outcome_winner === team2Name;
  const isNoResult = match.match_result_type === "no_result";

  const venueName = match.venue?.split(",")[0] ?? "";

  return (
    <Link href={`/matches/${match.match_id}`} className="block flex-shrink-0">
      <div className="w-[280px] rounded-lg border border-border bg-background transition-all hover:shadow-md hover:border-primary/30 cursor-pointer">
        {/* Header — venue + status */}
        <div className="flex items-center justify-between px-4 pt-3 pb-1.5">
          <span className="text-[11px] text-muted-foreground flex items-center gap-1 truncate max-w-[180px]">
            <MapPin className="h-3 w-3 shrink-0" />
            {venueName}
          </span>
          <Badge variant={isNoResult ? "secondary" : "outline"} className="text-[10px] h-4 px-1.5">
            {isNoResult ? "NO RES" : "RESULT"}
          </Badge>
        </div>

        {/* Scores */}
        <div className="px-4 py-2 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className={`text-sm ${isTeam1Winner ? "font-semibold text-foreground" : "text-muted-foreground"}`}>
              {shortName(team1Name)}
            </span>
            <div className="flex items-center gap-1.5">
              <span className={`text-sm font-mono tabular-nums ${isTeam1Winner ? "font-semibold text-foreground" : "text-muted-foreground"}`}>
                {inn1 ? `${inn1.total_runs}/${inn1.total_wickets}` : "-"}
              </span>
              {inn1 && (
                <span className="text-[10px] text-muted-foreground font-mono">({inn1.overs_played})</span>
              )}
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className={`text-sm ${isTeam2Winner ? "font-semibold text-foreground" : "text-muted-foreground"}`}>
              {shortName(team2Name)}
            </span>
            <div className="flex items-center gap-1.5">
              <span className={`text-sm font-mono tabular-nums ${isTeam2Winner ? "font-semibold text-foreground" : "text-muted-foreground"}`}>
                {inn2 ? `${inn2.total_runs}/${inn2.total_wickets}` : "-"}
              </span>
              {inn2 && (
                <span className="text-[10px] text-muted-foreground font-mono">({inn2.overs_played})</span>
              )}
            </div>
          </div>
        </div>

        {/* Result */}
        <div className="px-4 pb-3 pt-1.5 border-t border-border/50">
          <p className="text-xs text-primary truncate font-medium">
            {formatMatchResult(match)}
          </p>
        </div>
      </div>
    </Link>
  );
}
