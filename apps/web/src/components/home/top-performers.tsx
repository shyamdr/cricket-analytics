import Link from "next/link";
import { Flame, Zap, BarChart3 } from "lucide-react";
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

export function TopPerformers({ batters, bowlers, season }: TopPerformersProps) {
  return (
    <div className="flex flex-col gap-6">
      {/* Orange Cap — Top Batters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Flame className="h-5 w-5 text-orange-600" />
              Orange Cap
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
                  <TableHead className="text-right">SR</TableHead>
                  <TableHead className="text-right">4s</TableHead>
                  <TableHead className="text-right">6s</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {batters.slice(0, 5).map((batter, idx) => (
                  <TableRow key={batter.batter}>
                    <TableCell>
                      <span
                        className="inline-flex items-center justify-center h-5 w-5 rounded-full text-xs font-semibold text-orange-600 bg-orange-100"
                      >
                        {idx + 1}
                      </span>
                    </TableCell>
                    <TableCell className="text-sm">
                      <Link
                        href={`/players/${encodeURIComponent(batter.batter)}`}
                        className="hover:underline text-foreground"
                      >
                        {batter.batter}
                      </Link>
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums text-sm">
                      {batter.total_runs}
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums text-sm">
                      {batter.avg_strike_rate.toFixed(1)}
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums text-sm">
                      {batter.total_fours}
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums text-sm">
                      {batter.total_sixes}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Purple Cap — Top Bowlers */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-purple-600" />
              Purple Cap
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
                  <TableHead className="text-right">Econ</TableHead>
                  <TableHead className="text-right">Avg</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {bowlers.slice(0, 5).map((bowler, idx) => (
                  <TableRow key={bowler.bowler}>
                    <TableCell>
                      <span
                        className="inline-flex items-center justify-center h-5 w-5 rounded-full text-xs font-semibold text-purple-600 bg-purple-100"
                      >
                        {idx + 1}
                      </span>
                    </TableCell>
                    <TableCell className="text-sm">
                      <Link
                        href={`/players/${encodeURIComponent(bowler.bowler)}`}
                        className="hover:underline text-foreground"
                      >
                        {bowler.bowler}
                      </Link>
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums text-sm">
                      {bowler.total_wickets}
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums text-sm">
                      {bowler.avg_economy.toFixed(2)}
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums text-sm">
                      {bowler.bowling_avg != null
                        ? bowler.bowling_avg.toFixed(2)
                        : "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
