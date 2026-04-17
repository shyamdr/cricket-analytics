"use client";

import { useEffect, useState } from "react";
import { MatchTicker } from "@/components/home/match-ticker";
import { MatchSpotlight } from "@/components/home/match-spotlight";
import { SeasonSummary } from "@/components/home/season-summary";
import { LatestResults } from "@/components/home/latest-results";
import { TopPerformers } from "@/components/home/top-performers";
import { ExploreCards } from "@/components/home/explore-cards";
import { Skeleton } from "@/components/ui/skeleton";
import { getLatestSeason } from "@/lib/landing-utils";
import { fetchTeamMeta } from "@/lib/team-logos";
import type { RecentMatch } from "@/lib/landing-utils";
import type { BattingStats, BowlingStats, SeasonCount } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL || "";

export default function Home() {
  const [matches, setMatches] = useState<RecentMatch[]>([]);
  const [seasons, setSeasons] = useState<SeasonCount[]>([]);
  const [batters, setBatters] = useState<BattingStats[]>([]);
  const [bowlers, setBowlers] = useState<BowlingStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [slowApi, setSlowApi] = useState(false);

  useEffect(() => {
    const slowTimer = setTimeout(() => setSlowApi(true), 10_000);

    async function loadData() {
      // Batch 1: matches + seasons + team metadata in parallel
      const [matchData, seasonData] = await Promise.all([
        fetch(`${API}/api/v1/matches/recent?limit=20`)
          .then((r) => (r.ok ? r.json() : []))
          .catch(() => [] as RecentMatch[]),
        fetch(`${API}/api/v1/matches/seasons`)
          .then((r) => (r.ok ? r.json() : []))
          .catch(() => [] as SeasonCount[]),
        fetchTeamMeta(),
      ]);

      setMatches(matchData);
      setSeasons(seasonData);

      // Batch 2: batting + bowling stats for latest season
      const latest = getLatestSeason(seasonData);
      if (latest) {
        const [battingData, bowlingData] = await Promise.all([
          fetch(`${API}/api/v1/batting/?season=${latest}&limit=5`)
            .then((r) => (r.ok ? r.json() : []))
            .catch(() => [] as BattingStats[]),
          fetch(`${API}/api/v1/bowling/?season=${latest}&limit=5`)
            .then((r) => (r.ok ? r.json() : []))
            .catch(() => [] as BowlingStats[]),
        ]);
        setBatters(battingData);
        setBowlers(bowlingData);
      }

      setLoading(false);
      clearTimeout(slowTimer);
    }

    loadData();
    return () => clearTimeout(slowTimer);
  }, []);

  const latestSeason = getLatestSeason(seasons);
  const latestSeasonCount =
    seasons.find((s) => s.season === latestSeason)?.matches ?? 0;

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        {/* Ticker skeleton */}
        <Skeleton className="w-full h-24" />

        {/* Spotlight skeleton */}
        <div className="w-full px-6 lg:px-10 py-6">
          <Skeleton className="w-full h-48 rounded-lg" />
        </div>

        {/* Season summary skeleton */}
        <Skeleton className="w-full h-10" />

        {/* Two-column skeleton */}
        <div className="w-full px-6 lg:px-10 py-8 grid grid-cols-1 lg:grid-cols-5 gap-6">
          <Skeleton className="lg:col-span-3 h-64 rounded-lg" />
          <Skeleton className="lg:col-span-2 h-64 rounded-lg" />
        </div>

        {/* Explore cards — static, no skeleton needed */}
        <ExploreCards />

        {slowApi && (
          <p className="text-center text-sm text-muted-foreground py-4">
            Data is loading — the API may be waking up
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Match Ticker — full width below navbar */}
      <MatchTicker matches={matches} />

      {/* Section 1: Match Spotlight */}
      <MatchSpotlight matches={matches} />

      {/* Section 2: Season Summary */}
      <div className="animate-section-2">
        <SeasonSummary
          season={latestSeason}
          matchCount={latestSeasonCount}
          topScorer={
            batters[0]
              ? { name: batters[0].batter, runs: batters[0].total_runs }
              : null
          }
          topWicketTaker={
            bowlers[0]
              ? { name: bowlers[0].bowler, wickets: bowlers[0].total_wickets }
              : null
          }
        />
      </div>

      {/* Section 3: Two-column — results + top performers */}
      <div className="w-full px-6 lg:px-10 py-8 grid grid-cols-1 lg:grid-cols-5 gap-6 animate-section-3">
        <div className="lg:col-span-3">
          <LatestResults matches={matches.slice(0, 6)} />
        </div>
        <div className="lg:col-span-2">
          <TopPerformers
            batters={batters}
            bowlers={bowlers}
            season={latestSeason ?? ""}
          />
        </div>
      </div>

      {/* Section 4: Explore */}
      <div className="animate-section-4">
        <ExploreCards />
      </div>
    </div>
  );
}
