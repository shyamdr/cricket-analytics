"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, TrendingUp, Target } from "lucide-react";
import { Spinner } from "@/components/loading";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

interface PlayerProfile { player_name: string; unique_name: string | null; }
interface CareerBatting { innings: number; total_runs: number; highest_score: number; avg_strike_rate: number; total_fours: number; total_sixes: number; fifties: number; centuries: number; }
interface CareerBowling { innings: number; total_wickets: number; avg_economy: number; best_wickets: number; }
interface SeasonBatting { season: string; innings: number; total_runs: number; highest_score: number; avg_strike_rate: number; fours: number; sixes: number; }

const API = process.env.NEXT_PUBLIC_API_URL || "";

export default function PlayerDetailPage() {
  const params = useParams();
  const name = decodeURIComponent(params.playerName as string);

  const [profile, setProfile] = useState<PlayerProfile | null>(null);
  const [batting, setBatting] = useState<CareerBatting | null>(null);
  const [bowling, setBowling] = useState<CareerBowling | null>(null);
  const [seasonBatting, setSeasonBatting] = useState<SeasonBatting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const encoded = encodeURIComponent(name);
    Promise.all([
      fetch(`${API}/api/v1/players/${encoded}`).then((r) => r.ok ? r.json() : null),
      fetch(`${API}/api/v1/batting/stats/${encoded}`).then((r) => r.json()),
      fetch(`${API}/api/v1/bowling/stats/${encoded}`).then((r) => r.json()),
      fetch(`${API}/api/v1/batting/season-breakdown/${encoded}`).then((r) => r.json()),
    ]).then(([p, bat, bowl, seasons]) => {
      setProfile(p); setBatting(bat?.[0] || null); setBowling(bowl?.[0] || null);
      setSeasonBatting(seasons || []); setLoading(false);
    }).catch(() => { setError(true); setLoading(false); });
  }, [name]);

  if (loading) return <Spinner className="py-16" />;
  if (error || !profile) {
    return (
      <div className="w-full px-6 lg:px-10 py-16 text-center">
        <p className="text-muted-foreground">Player &quot;{name}&quot; not found.</p>
        <Button variant="ghost" size="sm" nativeButton={false} render={<Link href="/players" />} className="mt-2">
          <ArrowLeft className="h-4 w-4 mr-1" />Back to players
        </Button>
      </div>
    );
  }

  return (
    <div className="w-full px-6 lg:px-10 py-8 space-y-8">
      <div>
        <Button variant="ghost" size="sm" nativeButton={false} render={<Link href="/players" />} className="-ml-2 mb-2">
          <ArrowLeft className="h-4 w-4 mr-1" />Back to players
        </Button>
        <h1 className="text-3xl font-semibold text-foreground">{profile.player_name}</h1>
        {profile.unique_name && profile.unique_name !== profile.player_name && (
          <p className="text-muted-foreground mt-0.5">{profile.unique_name}</p>
        )}
      </div>

      {batting && batting.innings > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="h-5 w-5 text-orange-500" />
            <h2 className="text-xl font-semibold text-foreground">Batting Career</h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            <StatCard label="Innings" value={batting.innings} />
            <StatCard label="Runs" value={batting.total_runs.toLocaleString()} highlight />
            <StatCard label="Highest" value={batting.highest_score} />
            <StatCard label="Strike Rate" value={batting.avg_strike_rate.toFixed(1)} />
            <StatCard label="50s / 100s" value={`${batting.fifties} / ${batting.centuries}`} />
          </div>
        </div>
      )}

      {bowling && bowling.innings > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Target className="h-5 w-5 text-purple-500" />
            <h2 className="text-xl font-semibold text-foreground">Bowling Career</h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard label="Innings" value={bowling.innings} />
            <StatCard label="Wickets" value={bowling.total_wickets} highlight />
            <StatCard label="Economy" value={bowling.avg_economy.toFixed(2)} />
            <StatCard label="Best" value={`${bowling.best_wickets}w`} />
          </div>
        </div>
      )}

      {seasonBatting.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Season by Season</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Season</TableHead>
                  <TableHead className="text-right">Inn</TableHead>
                  <TableHead className="text-right">Runs</TableHead>
                  <TableHead className="text-right">HS</TableHead>
                  <TableHead className="text-right">SR</TableHead>
                  <TableHead className="text-right">4s</TableHead>
                  <TableHead className="text-right">6s</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {seasonBatting.map((s) => (
                  <TableRow key={s.season}>
                    <TableCell className="font-mono">{s.season}</TableCell>
                    <TableCell className="text-right font-mono">{s.innings}</TableCell>
                    <TableCell className="text-right font-mono font-semibold">{s.total_runs}</TableCell>
                    <TableCell className="text-right font-mono">{s.highest_score}</TableCell>
                    <TableCell className="text-right font-mono text-muted-foreground">{s.avg_strike_rate}</TableCell>
                    <TableCell className="text-right font-mono text-muted-foreground">{s.fours}</TableCell>
                    <TableCell className="text-right font-mono text-muted-foreground">{s.sixes}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function StatCard({ label, value, highlight }: { label: string; value: string | number; highlight?: boolean }) {
  return (
    <Card>
      <CardContent className="pt-4 pb-3 px-4">
        <p className="text-xs text-muted-foreground uppercase tracking-wide">{label}</p>
        <p className={`text-xl font-semibold mt-1 font-mono tabular-nums ${highlight ? "text-primary" : "text-foreground"}`}>
          {value}
        </p>
      </CardContent>
    </Card>
  );
}
