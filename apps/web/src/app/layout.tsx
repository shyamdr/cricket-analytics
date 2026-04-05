import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "InsideEdge",
  description: "The detail that changes everything. Deep cricket analytics powered by ball-by-ball data.",
};

function Navbar() {
  return (
    <nav className="border-b border-card-border bg-card/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-xl">🏏</span>
            <span className="font-semibold text-lg text-accent">InsideEdge</span>
          </Link>
          <div className="flex items-center gap-6 text-sm text-muted">
            <Link href="/matches" className="hover:text-foreground transition-colors">Matches</Link>
            <Link href="/players" className="hover:text-foreground transition-colors">Players</Link>
            <Link href="/teams" className="hover:text-foreground transition-colors">Teams</Link>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <Navbar />
        <main className="flex-1">{children}</main>
        <footer className="border-t border-card-border py-6 text-center text-xs text-muted">
          Data from{" "}
          <a href="https://cricsheet.org" className="text-accent hover:underline" target="_blank" rel="noopener noreferrer">
            Cricsheet
          </a>{" "}
          (CC BY 4.0) · Built by{" "}
          <a href="https://github.com/shyamdr/cricket-analytics" className="text-accent hover:underline" target="_blank" rel="noopener noreferrer">
            shyamdr
          </a>
        </footer>
      </body>
    </html>
  );
}
