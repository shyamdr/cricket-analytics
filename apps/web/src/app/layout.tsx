import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Image from "next/image";
import { Separator } from "@/components/ui/separator";
import { ThemeProvider } from "@/components/theme-provider";
import { Navbar } from "@/components/navbar";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "InsideEdge",
  description: "The detail that changes everything. Deep cricket analytics powered by ball-by-ball data.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} antialiased`} suppressHydrationWarning>
      <head />
      <body className="min-h-screen flex flex-col">
        <ThemeProvider>
          <Navbar />
          <main className="flex-1">{children}</main>
          <Separator />
          <footer className="py-6 px-6 lg:px-10">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <span className="relative h-7 w-[110px]">
                  <Image src="/logo/design_light.png" alt="InsideEdge" fill className="object-contain object-left dark:hidden" />
                  <Image src="/logo/design_dark.png" alt="InsideEdge" fill className="object-contain object-left hidden dark:block" />
                </span>
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
                <span>·</span>
                <a href="/about" className="text-primary hover:underline">
                  About
                </a>
              </div>
            </div>
          </footer>
        </ThemeProvider>
      </body>
    </html>
  );
}
