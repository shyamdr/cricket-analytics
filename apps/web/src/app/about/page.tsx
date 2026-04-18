import Image from "next/image";
import Link from "next/link";

export const metadata = {
  title: "About · InsideEdge",
  description: "The detail that changes everything. What InsideEdge is and why it exists.",
};

export default function AboutPage() {
  return (
    <div className="min-h-[calc(100vh-3.5rem)] flex flex-col items-center">
      {/* Hero — giant logo */}
      <div className="w-full flex items-center justify-center py-16 sm:py-24 lg:py-32 px-6">
        <div className="relative w-full max-w-3xl" style={{ aspectRatio: "4 / 1" }}>
          <Image
            src="/logo/design_light.png"
            alt="InsideEdge"
            fill
            className="object-contain dark:hidden"
            priority
          />
          <Image
            src="/logo/design_dark.png"
            alt="InsideEdge"
            fill
            className="object-contain hidden dark:block"
            priority
          />
        </div>
      </div>

      {/* Tagline */}
      <p className="text-2xl sm:text-3xl lg:text-4xl font-light text-muted-foreground tracking-tight text-center px-6">
        The detail that changes everything.
      </p>

      {/* About content */}
      <div className="max-w-2xl mx-auto px-6 py-16 space-y-8 text-base sm:text-lg leading-relaxed text-muted-foreground">
        <p>
          You watched the match. You saw the scorecard. You know who won.
          But do you know <span className="text-foreground font-medium">why</span> they won?
        </p>

        <p>
          Do you know the game was decided in overs 7 through 12 when the middle order
          couldn&apos;t rotate strike? That the bowler who took 2-for-30 actually bowled worse
          than the one who went wicketless? That the chaser had a 74% win rate at that venue
          in night games?
        </p>

        <p>
          In cricket, an <span className="text-foreground font-medium">inside edge </span> is
          when the ball barely grazes the inner face of the bat. It&apos;s the thinnest of margins —
          the difference between bowled and four runs, between a hero and a zero. Nobody in the
          crowd sees it happen. But it changes everything.
        </p>

        <p>
          That&apos;s what this is. The analytics and insights that casual viewers miss, but that
          change how you understand the game.
        </p>

        <p>
          Every ball. Every matchup. Every phase. Every pattern.
          Exposed, visualized, and <span className="text-foreground font-medium">free</span>.
        </p>

        {/* Stats strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 py-8 border-y border-border text-center">
          <div>
            <p className="text-2xl sm:text-3xl font-semibold text-foreground">280K+</p>
            <p className="text-sm text-muted-foreground mt-1">Deliveries</p>
          </div>
          <div>
            <p className="text-2xl sm:text-3xl font-semibold text-foreground">1,100+</p>
            <p className="text-sm text-muted-foreground mt-1">Matches</p>
          </div>
          <div>
            <p className="text-2xl sm:text-3xl font-semibold text-foreground">900+</p>
            <p className="text-sm text-muted-foreground mt-1">Players</p>
          </div>
          <div>
            <p className="text-2xl sm:text-3xl font-semibold text-foreground">18</p>
            <p className="text-sm text-muted-foreground mt-1">Seasons</p>
          </div>
        </div>

        <p>
          Built on ball-by-ball data from{" "}
          <a href="https://cricsheet.org" className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
            Cricsheet
          </a>{" "}
          (CC BY 4.0), enriched with ESPN match data, historical weather, and venue coordinates.
          Open source. No ads. No paywall. Just cricket, understood deeply.
        </p>

        <div className="flex items-center justify-center gap-4 pt-4">
          <Link
            href="/"
            className="inline-flex items-center px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            Explore matches
          </Link>
          <a
            href="https://github.com/shyamdr/cricket-analytics"
            className="inline-flex items-center px-5 py-2.5 rounded-lg border border-border text-sm font-medium hover:bg-accent transition-colors"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>
        </div>
      </div>
    </div>
  );
}
