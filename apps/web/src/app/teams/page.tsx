"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Spinner } from "@/components/loading";
import { Card, CardContent } from "@/components/ui/card";

interface Team {
  team_name: string;
  current_franchise_name: string | null;
  first_match_date: string;
  last_match_date: string;
  total_matches: number;
}

const API = process.env.NEXT_PUBLIC_API_URL || "";

export default function TeamsPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/v1/teams`)
      .then((r) => r.json())
      .then((data) => { setTeams(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div className="w-full px-6 lg:px-10 py-8">
      <h1 className="text-3xl font-semibold text-foreground mb-6">Teams</h1>
      {loading ? (
        <Spinner />
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {teams.map((t) => (
            <Link key={t.team_name} href={`/teams/${encodeURIComponent(t.team_name)}`} className="block">
              <Card className="transition-all hover:shadow-md hover:border-primary/30 h-full">
                <CardContent className="pt-5 pb-4 px-5">
                  <p className="font-semibold text-lg text-foreground">{t.team_name}</p>
                  {t.current_franchise_name && t.current_franchise_name !== t.team_name && (
                    <p className="text-xs text-muted-foreground mt-0.5">Now: {t.current_franchise_name}</p>
                  )}
                  <div className="flex gap-4 mt-3 text-sm text-muted-foreground">
                    <span>{t.total_matches} matches</span>
                    <span>{t.first_match_date?.slice(0, 4)}–{t.last_match_date?.slice(0, 4)}</span>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
