import { fetchAPI } from "@/lib/api";
import { Team } from "@/lib/types";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function TeamsPage() {
  const teams = await fetchAPI<Team[]>("/teams");

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold mb-6">Teams</h1>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {teams.map((t) => (
          <Link
            key={t.team_name}
            href={`/teams/${encodeURIComponent(t.team_name)}`}
            className="bg-card border border-card-border rounded-lg px-4 py-4 hover:border-accent/50 transition-colors"
          >
            <p className="font-semibold text-lg">{t.team_name}</p>
            {t.current_franchise_name &&
              t.current_franchise_name !== t.team_name && (
                <p className="text-xs text-muted">
                  Now: {t.current_franchise_name}
                </p>
              )}
            <div className="flex gap-4 mt-2 text-sm text-muted">
              <span>{t.total_matches} matches</span>
              <span>
                {t.first_match_date?.slice(0, 4)}–{t.last_match_date?.slice(0, 4)}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
