"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RadarChart } from "./radar-chart";

interface PlayerRating {
  player_name: string;
  playing_role: string | null;
  overall_rating: number;
  experience_score: number;
  age_score: number;
  batting_score: number;
  bowling_score: number;
  form_score: number;
  venue_score: number | null;
  pressure_score: number | null;
  vs_pace_score: number | null;
  vs_spin_score: number | null;
  adaptability_score: number | null;
  age_at_match: number | null;
  confidence: number;
  career_innings_batted_before: number | null;
  career_runs_before: number | null;
  career_batting_avg: number | null;
  career_batting_sr: number | null;
  career_innings_bowled_before: number | null;
  career_wickets_before: number | null;
  career_bowling_econ: number | null;
  career_bowling_sr: number | null;
}

interface PlayerRatingCardProps {
  player: PlayerRating;
  teamColor: string;
}

const roleLabel: Record<string, string> = {
  batter: "Batter",
  bowler: "Bowler",
  allrounder: "All-rounder",
  wicketkeeper: "Wicketkeeper",
  unknown: "Player",
};

export function PlayerRatingCard({ player, teamColor }: PlayerRatingCardProps) {
  const role = player.playing_role || "unknown";
  const isBatter = role === "batter" || role === "wicketkeeper";
  const isBowler = role === "bowler";

  const radarAxes = isBowler
    ? [
        { label: "Bowling", value: player.bowling_score, max: 100 },
        { label: "Form", value: player.form_score, max: 100 },
        { label: "Experience", value: player.experience_score, max: 100 },
        { label: "Age", value: player.age_score, max: 100 },
        { label: "Batting", value: player.batting_score, max: 100 },
      ]
    : [
        { label: "Batting", value: player.batting_score, max: 100 },
        { label: "Form", value: player.form_score, max: 100 },
        { label: "Experience", value: player.experience_score, max: 100 },
        { label: "Age", value: player.age_score, max: 100 },
        { label: "Bowling", value: player.bowling_score, max: 100 },
      ];

  return (
    <Card className="w-full">
      <CardContent className="pt-4 pb-3 px-4 space-y-2">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-semibold text-sm text-foreground">{player.player_name}</p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                {roleLabel[role]}
              </Badge>
              {player.age_at_match && (
                <span className="text-[10px] text-muted-foreground">Age {player.age_at_match}</span>
              )}
            </div>
          </div>
          <div className="text-right">
            <span className="text-2xl font-bold" style={{ color: teamColor }}>
              {player.overall_rating}
            </span>
            <p className="text-[10px] text-muted-foreground">Rating</p>
          </div>
        </div>

        <RadarChart axes={radarAxes} color={teamColor} size={150} />

        {/* Key career stats */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
          {isBatter || role === "allrounder" ? (
            <>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Avg</span>
                <span className="font-mono">{player.career_batting_avg ?? "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">SR</span>
                <span className="font-mono">{player.career_batting_sr ?? "—"}</span>
              </div>
            </>
          ) : null}
          {isBowler || role === "allrounder" ? (
            <>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Econ</span>
                <span className="font-mono">{player.career_bowling_econ ?? "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Wkts</span>
                <span className="font-mono">{player.career_wickets_before ?? "—"}</span>
              </div>
            </>
          ) : null}
          <div className="flex justify-between">
            <span className="text-muted-foreground">Innings</span>
            <span className="font-mono">
              {(player.career_innings_batted_before ?? 0) + (player.career_innings_bowled_before ?? 0)}
            </span>
          </div>
          {player.confidence < 1 && (
            <div className="col-span-2 text-[10px] text-amber-500">
              Low confidence ({Math.round(player.confidence * 100)}%) — limited career data
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
