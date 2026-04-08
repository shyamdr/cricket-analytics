import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { Activity, Trophy, Users, Swords } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "InsideEdge",
  description: "The detail that changes everything. Deep cricket analytics powered by ball-by-ball data.",
};

function Navbar() {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur-md">
      <div className="w-full px-6 lg:px-10 flex items-center justify-between h-14">
        <Link href="/" className="flex items-center gap-2.5">
          <Activity className="h-5 w-5 text-primary" />
          <div className="flex flex-col leading-tight">
            <span className="font-semibold text-base tracking-tight">InsideEdge</span>
            <span className="text-[10px] text-muted-foreground hidden sm:block -mt-0.5">The detail that changes everything</span>
          </div>
        </Link>
        <nav className="flex items-center gap-1">
          <Button variant="ghost" size="sm" nativeButton={false} render={<Link href="/matches" />}>
            <Trophy className="h-4 w-4 mr-1.5" />Matches
          </Button>
          <Button variant="ghost" size="sm" nativeButton={false} render={<Link href="/players" />}>
            <Users className="h-4 w-4 mr-1.5" />Players
          </Button>
          <Button variant="ghost" size="sm" nativeButton={false} render={<Link href="/teams" />}>
            <Swords className="h-4 w-4 mr-1.5" />Teams
          </Button>
        </nav>
      </div>
    </header>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} antialiased`} style={{ colorScheme: "light" }}>
      <body className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1">{children}</main>
        <Separator />
        <footer className="py-6 px-6 lg:px-10">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5 text-primary" />
              <span className="font-medium text-foreground">InsideEdge</span>
              <span>· Deep cricket analytics</span>
            </div>
            <div className="flex items-center gap-3">
              <span>
                Data from{" "}
                <a href="https://cricsheet.org" className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
                  Cricsheet
                </a>{" "}
                (CC BY 4.0)
              </span>
              <span>·</span>
              <a href="https://github.com/shyamdr/cricket-analytics" className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
                GitHub
              </a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
