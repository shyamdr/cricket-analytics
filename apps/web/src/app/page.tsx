"use client";

import { useEffect, useState } from "react";
import { MatchSpotlight } from "@/components/home/match-spotlight";
import { NewsFeed } from "@/components/home/news-feed";
import { TopPerformers } from "@/components/home/top-performers";
import { PointsTable } from "@/components/home/points-table";
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
          fetch(`${API}/api/v1/batting/top?season=${latest}&limit=5`)
            .then((r) => (r.ok ? r.json() : []))
            .catch(() => [] as BattingStats[]),
          fetch(`${API}/api/v1/bowling/top?season=${latest}&limit=5`)
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

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
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
      {/* Section 1: Match Spotlight */}
      <MatchSpotlight matches={matches} />

      {/* Two-column — news + top performers */}
      <div className="w-full px-6 lg:px-10 py-8 grid grid-cols-1 lg:grid-cols-5 gap-6 animate-section-3">
        <div className="lg:col-span-2">
          <NewsFeed />
        </div>
        <div className="lg:col-span-3">
          <TopPerformers
            batters={batters}
            bowlers={bowlers}
            season={latestSeason ?? ""}
          />
          {latestSeason && (
            <div className="mt-6">
              <PointsTable season={latestSeason} />
            </div>
          )}
        </div>
      </div>

      {/* Explore */}
      <div className="animate-section-4">
        <ExploreCards />
      </div>
    </div>
  );
}
