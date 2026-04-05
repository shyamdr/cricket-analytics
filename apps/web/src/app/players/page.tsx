import { fetchAPI } from "@/lib/api";
import { Player } from "@/lib/types";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function PlayersPage({
  searchParams,
}: {
  searchParams: Promise<{ search?: string }>;
}) {
  const params = await searchParams;
  const search = params.search || "";

  const players = await fetchAPI<Player[]>(
    search
      ? `/players?search=${encodeURIComponent(search)}&limit=100`
      : "/players?limit=100"
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold mb-6">Players</h1>

      {/* Search */}
      <form className="mb-6">
        <input
          type="text"
          name="search"
          defaultValue={search}
          placeholder="Search players..."
          className="w-full sm:w-80 bg-card border border-card-border rounded-lg px-4 py-2 text-sm text-foreground placeholder:text-muted focus:outline-none focus:border-accent"
        />
      </form>

      {/* Player grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {players.map((p) => (
          <Link
            key={p.player_id}
            href={`/players/${encodeURIComponent(p.player_name)}`}
            className="bg-card border border-card-border rounded-lg px-4 py-3 hover:border-accent/50 transition-colors"
          >
            <p className="font-medium">{p.player_name}</p>
            {p.unique_name && p.unique_name !== p.player_name && (
              <p className="text-xs text-muted">{p.unique_name}</p>
            )}
          </Link>
        ))}
      </div>

      {players.length === 0 && (
        <p className="text-muted text-center py-8">No players found.</p>
      )}
    </div>
  );
}
