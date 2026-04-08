import Link from "next/link";
import { Users, Swords, Trophy, MapPin, ArrowRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { LucideIcon } from "lucide-react";

interface ExploreCardData {
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
  stat?: string;
}

const cards: ExploreCardData[] = [
  {
    title: "Players",
    description: "Career stats, season breakdowns, and performance profiles",
    href: "/players",
    icon: Users,
    stat: "927 players",
  },
  {
    title: "Teams",
    description: "Head-to-head records, win rates, and season performance",
    href: "/teams",
    icon: Swords,
    stat: "19 teams",
  },
  {
    title: "Matches",
    description: "Full scorecards with ball-by-ball detail since 2008",
    href: "/matches",
    icon: Trophy,
    stat: "1,169 matches",
  },
  {
    title: "Venues",
    description: "Ground records, scoring patterns, and location analysis",
    href: "/venues",
    icon: MapPin,
    stat: "63 venues",
  },
];

export function ExploreCards() {
  return (
    <section className="w-full px-6 lg:px-10 py-8">
      <h2 className="text-lg font-semibold text-foreground mb-4">Explore</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((card) => (
          <Link key={card.href} href={card.href} className="group block">
            <Card className="h-full transition-all group-hover:shadow-md group-hover:border-primary/30">
              <CardContent className="flex flex-col gap-3 p-5">
                <div className="flex items-center justify-between">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <card.icon className="h-5 w-5 text-primary" />
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 -translate-x-1 transition-all group-hover:opacity-100 group-hover:translate-x-0" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground">{card.title}</h3>
                  <p className="text-sm text-muted-foreground mt-0.5">{card.description}</p>
                </div>
                {card.stat && (
                  <p className="text-xs text-muted-foreground font-mono">{card.stat}</p>
                )}
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </section>
  );
}
