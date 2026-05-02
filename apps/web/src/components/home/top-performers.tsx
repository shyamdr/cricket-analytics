"use client";

import Link from "next/link";
import { TrendingUp, Target, BarChart3 } from "lucide-react";
import type { BattingStats, BowlingStats } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { getTeamColor } from "@/lib/team-logos";

interface TopPerformersProps {
  batters: BattingStats[];
  bowlers: BowlingStats[];
  season: string;
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-muted-foreground gap-2">
      <BarChart3 className="h-8 w-8" />
      <p className="text-sm">Stats unavailable</p>
    </div>
  );
}

function PlayerPhoto({ espnId, name }: { espnId: number | null; name: string }) {
  if (!espnId) {
    return (
      <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center text-[10px] font-semibold text-muted-foreground shrink-0">
        {name.slice(0, 2).toUpperCase()}
      </div>
    );
  }
  return (
    <img
      src={`${process.env.NEXT_PUBLIC_IMAGE_CDN || "/api/v1/images"}/players/${espnId}.png`}
      alt={name}
      className="h-8 w-8 rounded-full object-cover bg-muted shrink-0"
      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
    />
  );
}

export function TopPerformers({ batters, bowlers, season }: TopPerformersProps) {
  return (
    <div className="flex flex-col gap-6">
      {/* Most Runs */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-orange-500" />
              Most Runs
            </span>
            <Badge variant="secondary">{season}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {batters.length === 0 ? (
            <EmptyState />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8">#</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead className="text-right">Runs</TableHead>
                  <TableHead className="text-right">Inn</TableHead>
                  <TableHead className="text-right">SR</TableHead>
                  <TableHead className="text-right">6s</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {batters.slice(0, 5).map((batter, idx) => {
                  const isLeader = idx === 0;
                  const teamColor = batter.team ? getTeamColor(batter.team) : "#6B7280";
                  return (
                    <TableRow
                      key={batter.batter}
                      style={isLeader ? {
                        background: `linear-gradient(to right, ${teamColor}99 0%, transparent 60%)`,
                      } : undefined}
                    >
                      <TableCell>
                        <span className={`inline-flex items-center justify-center h-5 w-5 rounded-full text-xs font-semibold ${
                          isLeader ? "bg-primary text-primary-foreground" : "text-muted-foreground bg-muted"
                        }`}>
                          {idx + 1}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm">
                        <div className="flex items-center gap-2">
                          {isLeader && <PlayerPhoto espnId={batter.espn_player_id} name={batter.batter} />}
                          <div>
                            <Link
                              href={`/players/${encodeURIComponent(batter.batter)}`}
                              className="hover:underline text-foreground"
                            >
                              {batter.batter}
                            </Link>
                            {isLeader && batter.team && (
                              <p className="text-[10px] text-muted-foreground">{batter.team}</p>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className={`text-right font-mono tabular-nums text-sm ${isLeader ? "font-semibold" : ""}`}>
                        {batter.total_runs}
                      </TableCell>
                      <TableCell className="text-right font-mono tabular-nums text-sm">
                        {batter.innings}
                      </TableCell>
                      <TableCell className="text-right font-mono tabular-nums text-sm">
                        {batter.avg_strike_rate.toFixed(1)}
                      </TableCell>
                      <TableCell className="text-right font-mono tabular-nums text-sm">
                        {batter.total_sixes}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Most Wickets */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Target className="h-5 w-5 text-purple-500" />
              Most Wickets
            </span>
            <Badge variant="secondary">{season}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {bowlers.length === 0 ? (
            <EmptyState />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8">#</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead className="text-right">Wkts</TableHead>
                  <TableHead className="text-right">Inn</TableHead>
                  <TableHead className="text-right">Econ</TableHead>
                  <TableHead className="text-right">Avg</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {bowlers.slice(0, 5).map((bowler, idx) => {
                  const isLeader = idx === 0;
                  const teamColor = bowler.team ? getTeamColor(bowler.team) : "#6B7280";
                  return (
                    <TableRow
                      key={bowler.bowler}
                      style={isLeader ? {
                        background: `linear-gradient(to right, ${teamColor}99 0%, transparent 60%)`,
                      } : undefined}
                    >
                      <TableCell>
                        <span className={`inline-flex items-center justify-center h-5 w-5 rounded-full text-xs font-semibold ${
                          isLeader ? "bg-primary text-primary-foreground" : "text-muted-foreground bg-muted"
                        }`}>
                          {idx + 1}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm">
                        <div className="flex items-center gap-2">
                          {isLeader && <PlayerPhoto espnId={bowler.espn_player_id} name={bowler.bowler} />}
                          <div>
                            <Link
                              href={`/players/${encodeURIComponent(bowler.bowler)}`}
                              className="hover:underline text-foreground"
                            >
                              {bowler.bowler}
                            </Link>
                            {isLeader && bowler.team && (
                              <p className="text-[10px] text-muted-foreground">{bowler.team}</p>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className={`text-right font-mono tabular-nums text-sm ${isLeader ? "font-semibold" : ""}`}>
                        {bowler.total_wickets}
                      </TableCell>
                      <TableCell className="text-right font-mono tabular-nums text-sm">
                        {bowler.innings}
                      </TableCell>
                      <TableCell className="text-right font-mono tabular-nums text-sm">
                        {bowler.avg_economy.toFixed(2)}
                      </TableCell>
                      <TableCell className="text-right font-mono tabular-nums text-sm">
                        {bowler.bowling_avg != null ? bowler.bowling_avg.toFixed(2) : "-"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
