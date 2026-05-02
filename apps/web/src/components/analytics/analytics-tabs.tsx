"use client";

import { useEffect, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { PlayerRatingCard } from "./player-rating-card";
import { TeamComparisonPanel } from "./team-comparison-panel";
import { MatchupTable } from "./matchup-table";
import { PhaseComparison } from "./phase-comparison";

const API = process.env.NEXT_PUBLIC_API_URL || "";

interface AnalyticsTabsProps {
  matchId: string;
  team1: string;
  team2: string;
  team1Color?: string;
  team2Color?: string;
}

export function AnalyticsTabs({ matchId, team1, team2, team1Color = "#3b82f6", team2Color = "#ef4444" }: AnalyticsTabsProps) {
  const [ratings, setRatings] = useState<any[]>([]);
  const [teamComparison, setTeamComparison] = useState<any>(null);
  const [matchups, setMatchups] = useState<any[]>([]);
  const [phaseComparison, setPhaseComparison] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const base = `${API}/api/v1/matches/${matchId}/analytics`;
    Promise.all([
      fetch(`${base}/player-ratings`).then((r) => r.ok ? r.json() : []),
      fetch(`${base}/team-comparison`).then((r) => r.ok ? r.json() : null),
      fetch(`${base}/matchups`).then((r) => r.ok ? r.json() : []),
      fetch(`${base}/phase-comparison`).then((r) => r.ok ? r.json() : null),
    ])
      .then(([r, tc, m, pc]) => {
        setRatings(r); setTeamComparison(tc); setMatchups(m); setPhaseComparison(pc);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [matchId]);

  if (loading) {
    return (
      <div className="py-8 text-center text-sm text-muted-foreground">
        Loading analytics...
      </div>
    );
  }

  const team1Ratings = ratings.filter((r: any) => {
    // Match players to teams via the matchups or ratings data
    // For now, split by first half / second half (ratings are ordered by overall_rating desc)
    // A better approach: use the team_comparison data to identify which players belong to which team
    return true;
  });

  return (
    <Tabs defaultValue="ratings">
      <TabsList variant="line">
        <TabsTrigger value="ratings">Player Ratings</TabsTrigger>
        <TabsTrigger value="comparison">Team Comparison</TabsTrigger>
        <TabsTrigger value="matchups">Matchups</TabsTrigger>
        <TabsTrigger value="phases">Phase Breakdown</TabsTrigger>
      </TabsList>

      <TabsContent value="ratings" className="mt-4">
        {ratings.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            Player ratings not available for this match.
          </p>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {ratings.map((r: any) => (
              <PlayerRatingCard
                key={r.player_name}
                player={r}
                teamColor={team1Color}
              />
            ))}
          </div>
        )}
      </TabsContent>

      <TabsContent value="comparison" className="mt-4">
        {teamComparison ? (
          <TeamComparisonPanel
            team1={teamComparison.team1}
            team2={teamComparison.team2}
            headToHead={teamComparison.head_to_head}
          />
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">
            Team comparison not available.
          </p>
        )}
      </TabsContent>

      <TabsContent value="matchups" className="mt-4">
        <MatchupTable matchups={matchups} team1={team1} team2={team2} />
      </TabsContent>

      <TabsContent value="phases" className="mt-4">
        {phaseComparison ? (
          <PhaseComparison
            team1Name={phaseComparison.team1.team_name}
            team2Name={phaseComparison.team2.team_name}
            team1Phases={phaseComparison.team1.phases}
            team2Phases={phaseComparison.team2.phases}
            venuePhases={phaseComparison.venue_averages.phases}
            venue={phaseComparison.venue_averages.venue}
          />
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">
            Phase comparison not available.
          </p>
        )}
      </TabsContent>
    </Tabs>
  );
}
