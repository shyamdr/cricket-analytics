"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { ArrowLeft, MapPin, Calendar as CalendarIcon, ChevronDown, Star } from "lucide-react";
import { Spinner } from "@/components/loading";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { AnalyticsTabs } from "@/components/analytics/analytics-tabs";
import { getTeamColor, fetchTeamMeta } from "@/lib/team-logos";

interface Match {
  match_id: string; team1: string; team2: string; venue: string;
  city: string | null; match_date: string; toss_winner: string;
  toss_decision: string; outcome_winner: string | null;
  winning_margin: string | null; match_result_type: string;
  event_name: string | null; event_stage: string | null;
  player_of_match: string | null; season: string | null;
}
interface MatchSummary {
  innings: number; batting_team: string; total_runs: number;
  total_wickets: number; overs_played: number; run_rate: number;
  total_fours: number; total_sixes: number;
}
interface BattingInnings {
  innings: number; batting_team: string; batter: string;
  runs_scored: number; balls_faced: number; fours: number;
  sixes: number; strike_rate: number; is_out: boolean;
  dismissal_kind: string | null; dismissed_by: string | null;
}
interface BowlingInnings {
  innings: number; batting_team: string; bowler: string;
  overs_bowled: number; runs_conceded: number; wickets: number;
  economy_rate: number;
}
interface Player {
  player_name: string; team: string; espn_player_id: number | null;
  batting_position: number | null; playing_role: string | null;
  is_captain: boolean | null; is_keeper: boolean | null;
  runs_scored: number | null; balls_faced: number | null;
  fours: number | null; sixes: number | null; strike_rate: number | null;
  dismissal_kind: string | null; dismissed_by: string | null; is_out: boolean | null;
  overs_bowled: number | null; runs_conceded: number | null;
  wickets: number | null; economy_rate: number | null; dot_balls: number | null;
}
interface PlayingXI {
  team1: { team_name: string; players: Player[] };
  team2: { team_name: string; players: Player[] };
}
interface Highlights {
  summary_text: string;
  player_of_match: string | null;
  outcome_winner: string | null;
  winning_margin: string | null;
  mvp: { match_mvp_player_name: string; match_mvp_total_impact: number } | null;
  dropped_catches: { innings: number; over_num: number; ball_num: number; batter: string; dropped_catch_fielders: string }[];
  top_scorers: { team: string; batter: string; runs: number; balls: number; fours: number; sixes: number }[];
  top_bowlers: { team: string; bowler: string; wickets: number; runs_conceded: number; overs: number }[];
  key_wickets: { innings: number; over_num: number; ball_num: number; batter: string; bowler: string; wicket_kind: string; wicket_player_out: string; batter_score_at_ball: number; team_score_at_ball: number; commentary_text: string | null }[];
}
interface TeamMeta { espn_team_id: number | null; team_name: string; }

const API = process.env.NEXT_PUBLIC_API_URL || "";
const IMAGE_CDN = process.env.NEXT_PUBLIC_IMAGE_CDN || `${API}/api/v1/images`;

function TypewriterText({ text }: { text: string }) {
  const [displayed, setDisplayed] = useState("");

  useEffect(() => {
    setDisplayed("");
    let i = 0;
    const interval = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) {
        clearInterval(interval);
      }
    }, 30);
    return () => clearInterval(interval);
  }, [text]);

  return (
    <p className="text-base text-muted-foreground leading-relaxed">{displayed}</p>
  );
}

function PlayerPhoto({ espnId, size = 96 }: { espnId: number | null; size?: number }) {
  if (!espnId) return <div className="bg-muted/30 rounded-lg" style={{ width: size, height: size }} />;
  return (
    <Image src={`${IMAGE_CDN}/players/${espnId}.png`} alt="" width={size} height={size}
      className="object-contain" style={{ background: "transparent" }} unoptimized />
  );
}

function PlayerRow({ p, align, mode = "batting" }: { p: Player; align: "left" | "right"; mode?: "batting" | "bowling" }) {
  const batted = p.runs_scored !== null;
  const bowled = p.overs_bowled !== null && p.overs_bowled > 0;

  const nameBlock = (
    <div className={`flex items-center gap-3 ${align === "right" ? "flex-row-reverse" : ""}`}>
      <PlayerPhoto espnId={p.espn_player_id} size={96} />
      <div className={align === "right" ? "text-right" : ""}>
        <div className={`flex items-center gap-1.5 ${align === "right" ? "justify-end" : ""}`}>
          <Link href={`/players/${encodeURIComponent(p.player_name)}`}
            className="text-base font-semibold text-foreground hover:text-primary transition-colors">
            {p.player_name}
          </Link>
          {p.is_captain && <Badge variant="outline" className="text-[10px] px-1 py-0">C</Badge>}
          {p.is_keeper && <Badge variant="outline" className="text-[10px] px-1 py-0">WK</Badge>}
        </div>
        {p.playing_role && <p className="text-sm text-muted-foreground">{p.playing_role}</p>}
      </div>
    </div>
  );

  const battingStats = (
    <div className={`space-y-0.5 ${align === "right" ? "text-left" : "text-right"}`}>
      {batted ? (
        <>
          <p>
            <span className="text-xl font-bold font-mono text-foreground">{p.runs_scored}</span>
            <span className="text-sm text-muted-foreground ml-1.5">({p.balls_faced}b)</span>
          </p>
          <p className="text-sm text-muted-foreground font-mono">
            SR {p.strike_rate} · {p.fours}×4 {p.sixes}×6
          </p>
          {p.dismissal_kind ? (
            <p className="text-sm text-muted-foreground">{p.dismissal_kind}{p.dismissed_by ? ` b ${p.dismissed_by}` : ""}</p>
          ) : (
            <p className="text-sm text-primary font-medium">not out</p>
          )}
        </>
      ) : (
        <p className="text-sm text-muted-foreground">Did not bat</p>
      )}
    </div>
  );

  const bowlingStats = (
    <div className={`space-y-0.5 ${align === "right" ? "text-left" : "text-right"}`}>
      {bowled ? (
        <>
          <p>
            <span className="text-xl font-bold font-mono text-foreground">{p.wickets}/{p.runs_conceded}</span>
            <span className="text-sm text-muted-foreground ml-1.5">({p.overs_bowled} ov)</span>
          </p>
          <p className="text-sm text-muted-foreground font-mono">
            Econ {p.economy_rate} · {p.dot_balls} dots
          </p>
        </>
      ) : (
        <p className="text-sm text-muted-foreground">Did not bowl</p>
      )}
    </div>
  );

  return (
    <div className={`flex items-center justify-between gap-4 py-3 rounded-lg px-2 transition-all duration-300 ease-out hover:bg-muted/30 hover:scale-[1.01] ${align === "right" ? "flex-row-reverse" : ""}`}>
      {nameBlock}
      {mode === "batting" ? battingStats : bowlingStats}
    </div>
  );
}

export default function MatchDetailPage() {
  const params = useParams();
  const matchId = params.matchId as string;
  const [match, setMatch] = useState<Match | null>(null);
  const [summary, setSummary] = useState<MatchSummary[]>([]);
  const [batting, setBatting] = useState<BattingInnings[]>([]);
  const [bowling, setBowling] = useState<BowlingInnings[]>([]);
  const [playingXI, setPlayingXI] = useState<PlayingXI | null>(null);
  const [highlights, setHighlights] = useState<Highlights | null>(null);
  const [teams, setTeams] = useState<TeamMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [summaryOpen, setSummaryOpen] = useState(true);
  const [scorecardMode, setScorecardMode] = useState<"batting" | "bowling">("batting");

  useEffect(() => {
    fetchTeamMeta().then(() => {
      Promise.all([
      fetch(`${API}/api/v1/matches/${matchId}`).then((r) => r.json()),
      fetch(`${API}/api/v1/matches/${matchId}/summary`).then((r) => r.json()),
      fetch(`${API}/api/v1/matches/${matchId}/batting`).then((r) => r.json()),
      fetch(`${API}/api/v1/matches/${matchId}/bowling`).then((r) => r.json()),
      fetch(`${API}/api/v1/matches/${matchId}/playing-xi`).then((r) => r.ok ? r.json() : null),
      fetch(`${API}/api/v1/teams`).then((r) => r.ok ? r.json() : []),
      fetch(`${API}/api/v1/matches/${matchId}/highlights`).then((r) => r.ok ? r.json() : null),
    ]).then(([m, s, bat, bowl, xi, t, h]) => {
      setMatch(m); setSummary(s); setBatting(bat); setBowling(bowl);
      setPlayingXI(xi); setTeams(t); setHighlights(h); setLoading(false);
    }).catch(() => { setError(true); setLoading(false); });
    });
  }, [matchId]);

  if (loading) return <Spinner className="py-16" />;
  if (error || !match) {
    return (
      <div className="w-full px-6 lg:px-10 py-16 text-center">
        <p className="text-muted-foreground">Could not load match. API may be waking up.</p>
        <Button variant="ghost" size="sm" nativeButton={false} render={<Link href="/matches" />}>
          <ArrowLeft className="h-4 w-4 mr-1" />Back to matches
        </Button>
      </div>
    );
  }

  const formattedDate = new Date(match.match_date).toLocaleDateString("en-US", {
    year: "numeric", month: "long", day: "numeric",
  });

  return (
    <div className="w-full px-6 lg:px-10 py-8 space-y-6">
      {/* Back link */}
      <Button variant="ghost" size="sm" nativeButton={false} render={<Link href="/matches" />} className="-ml-2">
        <ArrowLeft className="h-4 w-4 mr-1" />Back to matches
      </Button>

      {/* Match spotlight card — same design as home page */}
      {(() => {
        const inn1 = summary.find((i) => i.innings === 1);
        const inn2 = summary.find((i) => i.innings === 2);
        const team1Name = inn1?.batting_team ?? match.team1;
        const team2Name = inn2?.batting_team ?? match.team2;
        const team1Id = (teams.find((t: any) => t.team_name === team1Name) as any)?.espn_team_id ?? null;
        const team2Id = (teams.find((t: any) => t.team_name === team2Name) as any)?.espn_team_id ?? null;
        const team1Logo = team1Id ? `${IMAGE_CDN}/teams/${team1Id}.png` : null;
        const team2Logo = team2Id ? `${IMAGE_CDN}/teams/${team2Id}.png` : null;
        const isTeam1Winner = match.outcome_winner === team1Name;
        const isTeam2Winner = match.outcome_winner === team2Name;
        const result = match.winning_margin
          ? `${match.outcome_winner} won by ${match.winning_margin}`
          : match.match_result_type === "no_result" ? "No Result" : null;
        const tossInfo = `${match.toss_winner} won toss · chose to ${match.toss_decision}`;
        const team1Color = getTeamColor(team1Name);
        const team2Color = getTeamColor(team2Name);

        return (
          <Card className="overflow-hidden">
            <CardContent className="p-0">
              <div className="flex flex-col lg:flex-row items-stretch relative overflow-hidden min-h-[160px] lg:min-h-[180px]">
                {/* Team 1 gradient */}
                <div
                  className="absolute inset-y-0 left-0 pointer-events-none transition-colors duration-300"
                  style={{
                    width: "calc(50% - 6px)",
                    background: `linear-gradient(to left, ${team1Color} 0%, ${team1Color} 25%, transparent 55%)`,
                  }}
                />
                {/* Team 2 gradient */}
                <div
                  className="absolute inset-y-0 right-0 pointer-events-none transition-colors duration-300"
                  style={{
                    width: "calc(50% - 6px)",
                    background: `linear-gradient(to right, ${team2Color} 0%, ${team2Color} 25%, transparent 55%)`,
                  }}
                />
                {/* Team 1 side */}
                <div className="flex-1 py-6 pl-4 pr-20 lg:pr-24 grid grid-cols-[180px] justify-end items-center relative overflow-hidden">
                  <div className="flex flex-col items-center">
                    <Link href={`/teams/${encodeURIComponent(team1Name)}`} className="text-base lg:text-lg text-center text-foreground whitespace-nowrap hover:text-primary transition-colors">{team1Name}</Link>
                    <span className="text-2xl lg:text-3xl font-mono tabular-nums text-foreground">{inn1 ? `${inn1.total_runs}/${inn1.total_wickets}` : "-"}</span>
                    <span className="text-xs text-muted-foreground font-mono h-5">{inn1 ? `(${inn1.overs_played} ov)` : "\u00A0"}</span>
                    <span className="text-xs text-muted-foreground flex items-center gap-1 h-5">
                      {isTeam1Winner && match.player_of_match ? (<><Star className="h-2.5 w-2.5 text-amber-500 fill-amber-500" /><Link href={`/players/${encodeURIComponent(match.player_of_match)}`} className="hover:text-primary transition-colors">{match.player_of_match}</Link></>) : "\u00A0"}
                    </span>
                  </div>
                </div>

                {/* Center — logos + VS */}
                <div className="flex items-center justify-center gap-6 lg:gap-8 px-4 lg:px-6 py-3 lg:py-0 relative">
                  {team1Logo ? (
                    <Link href={`/teams/${encodeURIComponent(team1Name)}`} className="h-[130px] w-[130px] lg:h-[160px] lg:w-[160px] p-2.5 lg:p-3 flex items-center justify-center transition-transform duration-200 hover:scale-110 hover:drop-shadow-lg relative overflow-visible">
                      <img src={team1Logo} alt={team1Name} className="object-contain max-h-full max-w-full relative" />
                    </Link>
                  ) : (
                    <Link href={`/teams/${encodeURIComponent(team1Name)}`} className="h-[130px] w-[130px] lg:h-[160px] lg:w-[160px] rounded-full bg-white/20 flex items-center justify-center text-2xl font-semibold text-white transition-transform duration-200 hover:scale-110 hover:drop-shadow-lg relative overflow-visible">
                      {team1Name.slice(0, 2).toUpperCase()}
                    </Link>
                  )}

                  <span
                    className="text-3xl font-black tracking-tighter text-white select-none"
                    style={{
                      textShadow: "0 0 1px rgba(0,0,0,0.8), 0 0 3px rgba(0,0,0,0.5), 0 2px 6px rgba(0,0,0,0.4)",
                      WebkitTextStroke: "0.5px rgba(0,0,0,0.4)",
                    }}
                  >
                    VS
                  </span>

                  {team2Logo ? (
                    <Link href={`/teams/${encodeURIComponent(team2Name)}`} className="h-[130px] w-[130px] lg:h-[160px] lg:w-[160px] p-2.5 lg:p-3 flex items-center justify-center transition-transform duration-200 hover:scale-110 hover:drop-shadow-lg relative overflow-visible">
                      <img src={team2Logo} alt={team2Name} className="object-contain max-h-full max-w-full relative" />
                    </Link>
                  ) : (
                    <Link href={`/teams/${encodeURIComponent(team2Name)}`} className="h-[130px] w-[130px] lg:h-[160px] lg:w-[160px] rounded-full bg-white/20 flex items-center justify-center text-2xl font-semibold text-white transition-transform duration-200 hover:scale-110 hover:drop-shadow-lg relative overflow-visible">
                      {team2Name.slice(0, 2).toUpperCase()}
                    </Link>
                  )}
                </div>

                {/* Team 2 side */}
                <div className="flex-1 py-6 pr-4 pl-20 lg:pl-24 grid grid-cols-[180px] justify-start items-center relative overflow-hidden">
                  <div className="flex flex-col items-center">
                    <Link href={`/teams/${encodeURIComponent(team2Name)}`} className="text-base lg:text-lg text-center text-foreground whitespace-nowrap hover:text-primary transition-colors">{team2Name}</Link>
                    <span className="text-2xl lg:text-3xl font-mono tabular-nums text-foreground">{inn2 ? `${inn2.total_runs}/${inn2.total_wickets}` : "-"}</span>
                    <span className="text-xs text-muted-foreground font-mono h-5">{inn2 ? `(${inn2.overs_played} ov)` : "\u00A0"}</span>
                    <span className="text-xs text-muted-foreground flex items-center gap-1 h-5">
                      {isTeam2Winner && match.player_of_match ? (<><Star className="h-2.5 w-2.5 text-amber-500 fill-amber-500" /><Link href={`/players/${encodeURIComponent(match.player_of_match)}`} className="hover:text-primary transition-colors">{match.player_of_match}</Link></>) : "\u00A0"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Bottom bar */}
              <div className="border-t border-border px-6 lg:px-8 py-3 flex flex-col sm:flex-row items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-3">
                  {match.event_name && (
                    <Link href={`/matches?season=${match.season}`}>
                      <Badge variant="secondary" className="hover:bg-secondary/80 transition-colors cursor-pointer">
                        {match.event_name}
                        {match.event_stage ? ` · ${match.event_stage}` : ""}
                      </Badge>
                    </Link>
                  )}
                  {result && <span className="text-sm font-semibold text-primary">{result}</span>}
                  <span className="text-xs text-muted-foreground">· {tossInfo}</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <Link href="/venues" className="flex items-center gap-1 hover:text-primary transition-colors">
                    <MapPin className="h-3 w-3" />{match.venue}{match.city ? `, ${match.city}` : ""}
                  </Link>
                  <span className="flex items-center gap-1"><CalendarIcon className="h-3 w-3" />{formattedDate}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })()}

      {/* Match summary — collapsible with typewriter animation */}
      {highlights && highlights.summary_text && (
        <div>
          <button
            type="button"
            onClick={() => setSummaryOpen(!summaryOpen)}
            className="flex items-center gap-2 text-base font-semibold text-foreground hover:text-primary transition-colors w-full"
          >
            <ChevronDown className={`h-5 w-5 transition-transform ${summaryOpen ? "rotate-180" : ""}`} />
            Match Summary
          </button>
          {summaryOpen && (
            <div className="mt-3 pl-7">
              <TypewriterText text={highlights.summary_text} />
            </div>
          )}
        </div>
      )}

      {/* Scorecard — split view with batting/bowling filter */}
      {playingXI && (() => {
        return (
          <div>
            {/* Filter toggle */}
            <div className="flex items-center gap-2 mb-4">
              <button
                type="button"
                onClick={() => setScorecardMode("batting")}
                className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                  scorecardMode === "batting"
                    ? "bg-primary text-primary-foreground border-primary"
                    : "border-border text-muted-foreground hover:text-foreground hover:bg-accent"
                }`}
              >
                Batting
              </button>
              <button
                type="button"
                onClick={() => setScorecardMode("bowling")}
                className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                  scorecardMode === "bowling"
                    ? "bg-primary text-primary-foreground border-primary"
                    : "border-border text-muted-foreground hover:text-foreground hover:bg-accent"
                }`}
              >
                Bowling
              </button>
            </div>

            <div className="space-y-0">
              {/* Header row — team icons + names */}
              <div className="flex items-center gap-0 border-b-2 border-border pb-4 mb-1 transition-colors duration-300">
                <div className="flex-1 pr-6 flex items-center gap-4 justify-end">
                  <span className="text-xl font-bold text-foreground">{match.team1}</span>
                  {(() => {
                    const tid = (teams.find((t: any) => t.team_name === match.team1) as any)?.espn_team_id;
                    return tid ? <img src={`${IMAGE_CDN}/teams/${tid}.png`} alt="" className="h-12 w-12 object-contain" /> : null;
                  })()}
                </div>
                <div className="w-0.5 bg-border self-stretch shrink-0" />
                <div className="flex-1 pl-6 flex items-center gap-4">
                  {(() => {
                    const tid = (teams.find((t: any) => t.team_name === match.team2) as any)?.espn_team_id;
                    return tid ? <img src={`${IMAGE_CDN}/teams/${tid}.png`} alt="" className="h-12 w-12 object-contain" /> : null;
                  })()}
                  <span className="text-xl font-bold text-foreground">{match.team2}</span>
                </div>
              </div>
              {(() => {
                const t1 = playingXI.team1.players.filter(p =>
                  scorecardMode === "batting" ? p.runs_scored !== null : (p.overs_bowled !== null && p.overs_bowled > 0)
                );
                const t2 = playingXI.team2.players.filter(p =>
                  scorecardMode === "batting" ? p.runs_scored !== null : (p.overs_bowled !== null && p.overs_bowled > 0)
                );
                const maxLen = Math.max(t1.length, t2.length);
                const rows = [];
                for (let i = 0; i < maxLen; i++) {
                  rows.push(
                    <div key={`${scorecardMode}-${i}`} className="flex items-center gap-0 border-b border-border/20 last:border-0 animate-fade-in">
                      <div className="flex-1 pr-6">
                        {t1[i] ? <PlayerRow p={t1[i]} align="left" mode={scorecardMode} /> : <div className="py-3" />}
                      </div>
                      <div className="w-px bg-border/50 self-stretch shrink-0" />
                      <div className="flex-1 pl-6">
                        {t2[i] ? <PlayerRow p={t2[i]} align="right" mode={scorecardMode} /> : <div className="py-3" />}
                      </div>
                    </div>
                  );
                }
                return rows;
              })()}
            </div>
          </div>
        );
      })()}

      {/* Analytics */}
      <Separator className="my-4" />
      <h2 className="text-lg font-semibold text-foreground">Match Analytics</h2>
      <AnalyticsTabs matchId={matchId} team1={match.team1} team2={match.team2} />
    </div>
  );
}
