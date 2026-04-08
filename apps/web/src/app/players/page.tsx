"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Spinner } from "@/components/loading";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

interface Player {
  player_id: string;
  player_name: string;
  unique_name: string | null;
}

const API = process.env.NEXT_PUBLIC_API_URL || "";

export default function PlayersPageWrapper() {
  return (
    <Suspense fallback={<Spinner className="py-16" />}>
      <PlayersPage />
    </Suspense>
  );
}

function PlayersPage() {
  const searchParams = useSearchParams();
  const search = searchParams.get("search") || "";

  const [players, setPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const url = search
      ? `${API}/api/v1/players?search=${encodeURIComponent(search)}&limit=100`
      : `${API}/api/v1/players?limit=100`;

    fetch(url)
      .then((r) => r.json())
      .then((data) => {
        setPlayers(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [search]);

  return (
    <div className="w-full px-6 lg:px-10 py-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-semibold text-foreground">Players</h1>
          {!loading && players.length > 0 && (
            <p className="text-sm text-muted-foreground mt-1">{players.length} players{search ? ` matching "${search}"` : ""}</p>
          )}
        </div>
        <form>
          <Input
            type="text"
            name="search"
            defaultValue={search}
            placeholder="Search players..."
            className="w-full sm:w-72"
          />
        </form>
      </div>

      {loading ? (
        <Spinner />
      ) : players.length === 0 ? (
        <p className="text-muted-foreground text-center py-8">No players found.</p>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {players.map((p) => (
            <Link key={p.player_id} href={`/players/${encodeURIComponent(p.player_name)}`} className="block">
              <Card className="transition-all hover:shadow-md hover:border-primary/30 h-full">
                <CardContent className="pt-4 pb-3 px-4">
                  <p className="font-medium text-foreground">{p.player_name}</p>
                  {p.unique_name && p.unique_name !== p.player_name && (
                    <p className="text-xs text-muted-foreground mt-0.5">{p.unique_name}</p>
                  )}
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
