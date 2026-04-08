import { Calendar, Hash, Flame, Target } from "lucide-react";
import { Separator } from "@/components/ui/separator";

interface SeasonSummaryProps {
  season: string | null;
  matchCount: number;
  topScorer: { name: string; runs: number } | null;
  topWicketTaker: { name: string; wickets: number } | null;
}

export function SeasonSummary({
  season,
  matchCount,
  topScorer,
  topWicketTaker,
}: SeasonSummaryProps) {
  if (season === null) return null;

  return (
    <div className="border-y border-border bg-muted/30">
      <div className="w-full px-6 lg:px-10 py-3">
        <div className="flex items-center justify-center gap-4 text-sm">
          <div className="flex items-center gap-1.5 text-foreground">
            <Calendar className="h-3.5 w-3.5 text-primary" />
            <span className="font-medium">IPL {season}</span>
          </div>

          <Separator orientation="vertical" className="h-4" />

          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Hash className="h-3.5 w-3.5" />
            <span>{matchCount} matches</span>
          </div>

          {topScorer && (
            <>
              <Separator orientation="vertical" className="h-4" />
              <div className="flex items-center gap-1.5">
                <Flame className="h-3.5 w-3.5 text-orange-500" />
                <span className="text-muted-foreground">
                  Top scorer: <span className="text-foreground font-medium">{topScorer.name}</span> ({topScorer.runs})
                </span>
              </div>
            </>
          )}

          {topWicketTaker && (
            <>
              <Separator orientation="vertical" className="h-4" />
              <div className="flex items-center gap-1.5">
                <Target className="h-3.5 w-3.5 text-purple-500" />
                <span className="text-muted-foreground">
                  Top wickets: <span className="text-foreground font-medium">{topWicketTaker.name}</span> ({topWicketTaker.wickets})
                </span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
