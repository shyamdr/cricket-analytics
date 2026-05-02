"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface PhaseDetail {
  phase: string;
  matches_sample_size: number;
  avg_runs_per_match: number | null;
  avg_wickets_per_match: number | null;
  run_rate: number | null;
  boundary_pct: number | null;
  dot_ball_pct: number | null;
}

interface PhaseComparisonProps {
  team1Name: string;
  team2Name: string;
  team1Phases: PhaseDetail[];
  team2Phases: PhaseDetail[];
  venuePhases: PhaseDetail[];
  venue: string;
}

function StatBar({ label, val1, val2, venueVal, higherIsBetter = true }: {
  label: string;
  val1: number | null;
  val2: number | null;
  venueVal: number | null;
  higherIsBetter?: boolean;
}) {
  const v1 = val1 ?? 0;
  const v2 = val2 ?? 0;
  const better1 = higherIsBetter ? v1 >= v2 : v1 <= v2;
  return (
    <div className="grid grid-cols-[1fr_60px_60px_60px] gap-2 text-[11px] py-0.5">
      <span className="text-muted-foreground">{label}</span>
      <span className={`font-mono text-right ${better1 ? "font-semibold text-foreground" : "text-muted-foreground"}`}>
        {val1 ?? "—"}
      </span>
      <span className={`font-mono text-right ${!better1 ? "font-semibold text-foreground" : "text-muted-foreground"}`}>
        {val2 ?? "—"}
      </span>
      <span className="font-mono text-right text-muted-foreground/60">{venueVal ?? "—"}</span>
    </div>
  );
}

export function PhaseComparison({ team1Name, team2Name, team1Phases, team2Phases, venuePhases, venue }: PhaseComparisonProps) {
  const phases = ["powerplay", "middle", "death"];

  const getPhase = (list: PhaseDetail[], phase: string) => list.find((p) => p.phase === phase);

  return (
    <div className="space-y-4">
      {phases.map((phase) => {
        const t1 = getPhase(team1Phases, phase);
        const t2 = getPhase(team2Phases, phase);
        const v = getPhase(venuePhases, phase);

        return (
          <Card key={phase}>
            <CardHeader className="pb-1">
              <CardTitle className="text-sm capitalize">{phase}</CardTitle>
            </CardHeader>
            <CardContent>
              {/* Header row */}
              <div className="grid grid-cols-[1fr_60px_60px_60px] gap-2 text-[10px] text-muted-foreground pb-1 border-b mb-1">
                <span />
                <span className="text-right">{team1Name.split(" ").pop()}</span>
                <span className="text-right">{team2Name.split(" ").pop()}</span>
                <span className="text-right">Venue</span>
              </div>
              <StatBar label="Run Rate" val1={t1?.run_rate ?? null} val2={t2?.run_rate ?? null} venueVal={v?.run_rate ?? null} />
              <StatBar label="Avg Runs" val1={t1?.avg_runs_per_match ?? null} val2={t2?.avg_runs_per_match ?? null} venueVal={v?.avg_runs_per_match ?? null} />
              <StatBar label="Boundary %" val1={t1?.boundary_pct ?? null} val2={t2?.boundary_pct ?? null} venueVal={v?.boundary_pct ?? null} />
              <StatBar label="Dot Ball %" val1={t1?.dot_ball_pct ?? null} val2={t2?.dot_ball_pct ?? null} venueVal={v?.dot_ball_pct ?? null} higherIsBetter={false} />
              <div className="text-[9px] text-muted-foreground/50 mt-1">
                Sample: {t1?.matches_sample_size ?? 0} / {t2?.matches_sample_size ?? 0} / {v?.matches_sample_size ?? 0} matches
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
