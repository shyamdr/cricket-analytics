"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Trophy, BarChart3 } from "lucide-react";
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
import { getTeamLogoUrl } from "@/lib/team-logos";

interface Standing {
  team: string;
  played: number;
  won: number;
  lost: number;
  nr: number;
  points: number;
  nrr: number | null;
}

interface PointsTableProps {
  season: string;
}

const API = process.env.NEXT_PUBLIC_API_URL || "";

export function PointsTable({ season }: PointsTableProps) {
  const [standings, setStandings] = useState<Standing[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!season) { setLoading(false); return; }
    fetch(`${API}/api/v1/standings?season=${season}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => { setStandings(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [season]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Trophy className="h-5 w-5" />
            Points Table
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-6 bg-muted rounded" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Don't render if no standings (bilateral series or no data)
  if (standings.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Trophy className="h-5 w-5 text-amber-500" />
            Points Table
          </span>
          <Badge variant="secondary">{season}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8">#</TableHead>
              <TableHead>Team</TableHead>
              <TableHead className="text-right">P</TableHead>
              <TableHead className="text-right">W</TableHead>
              <TableHead className="text-right">L</TableHead>
              <TableHead className="text-right">NR</TableHead>
              <TableHead className="text-right">Pts</TableHead>
              <TableHead className="text-right">NRR</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {standings.map((s, idx) => {
              const logo = getTeamLogoUrl(s.team);
              return (
                <TableRow key={s.team}>
                  <TableCell>
                    <span className="inline-flex items-center justify-center h-5 w-5 rounded-full text-xs font-semibold text-muted-foreground bg-muted">
                      {idx + 1}
                    </span>
                  </TableCell>
                  <TableCell className="text-sm">
                    <Link
                      href={`/teams/${encodeURIComponent(s.team)}`}
                      className="flex items-center gap-2 hover:underline text-foreground"
                    >
                      {logo && (
                        <img src={logo} alt={s.team} className="h-5 w-5 object-contain shrink-0" />
                      )}
                      <span className={idx === 0 ? "font-medium" : ""}>{s.team}</span>
                    </Link>
                  </TableCell>
                  <TableCell className="text-right font-mono tabular-nums text-sm">{s.played}</TableCell>
                  <TableCell className="text-right font-mono tabular-nums text-sm">{s.won}</TableCell>
                  <TableCell className="text-right font-mono tabular-nums text-sm">{s.lost}</TableCell>
                  <TableCell className="text-right font-mono tabular-nums text-sm">{s.nr}</TableCell>
                  <TableCell className="text-right font-mono tabular-nums text-sm font-semibold">{s.points}</TableCell>
                  <TableCell className="text-right font-mono tabular-nums text-sm">
                    {s.nrr != null ? (s.nrr >= 0 ? `+${s.nrr.toFixed(3)}` : s.nrr.toFixed(3)) : "-"}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
