"use client";

import { useEffect, useState } from "react";
import { MapPin } from "lucide-react";
import { Spinner } from "@/components/loading";
import { Card, CardContent } from "@/components/ui/card";

interface Venue {
  venue: string;
  city: string | null;
  total_matches: number;
}

const API = process.env.NEXT_PUBLIC_API_URL || "";

export default function VenuesPage() {
  const [venues, setVenues] = useState<Venue[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/v1/matches/venues`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => { setVenues(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div className="w-full px-6 lg:px-10 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-semibold text-foreground">Venues</h1>
        {!loading && venues.length > 0 && (
          <span className="text-sm text-muted-foreground">{venues.length} venues</span>
        )}
      </div>

      {loading ? (
        <Spinner />
      ) : venues.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground gap-3">
          <MapPin className="h-10 w-10" />
          <p className="text-sm">Venue data is not available yet.</p>
          <p className="text-xs">This page will show venue stats once the API endpoint is ready.</p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {venues.map((v) => (
            <Card key={v.venue} className="transition-all hover:shadow-md hover:border-primary/30">
              <CardContent className="pt-5 pb-4 px-5">
                <div className="flex items-start gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 shrink-0 mt-0.5">
                    <MapPin className="h-4 w-4 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-semibold text-foreground truncate">{v.venue}</p>
                    {v.city && <p className="text-xs text-muted-foreground mt-0.5">{v.city}</p>}
                    <p className="text-xs text-muted-foreground mt-1 font-mono">{v.total_matches} matches</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
