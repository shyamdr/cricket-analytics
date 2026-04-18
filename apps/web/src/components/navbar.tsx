"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { ChevronDown } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";

// ---------------------------------------------------------------------------
// Dropdown menu item types
// ---------------------------------------------------------------------------

interface DropdownItem {
  label: string;
  href: string;
}

interface DropdownSection {
  heading?: string;
  items: DropdownItem[];
}

interface NavTab {
  label: string;
  href?: string;
  sections?: DropdownSection[];
}

// ---------------------------------------------------------------------------
// Navigation structure
// ---------------------------------------------------------------------------

const NAV_TABS: NavTab[] = [
  {
    label: "Series",
    sections: [
      {
        heading: "Current",
        items: [
          { label: "Indian Premier League", href: "/matches?season=2026" },
        ],
      },
      {
        heading: "Archives",
        items: [
          { label: "All Seasons", href: "/matches" },
        ],
      },
    ],
  },
  {
    label: "Teams",
    sections: [
      {
        heading: "League",
        items: [
          { label: "All Teams", href: "/teams" },
        ],
      },
    ],
  },
  {
    label: "Stats",
    sections: [
      {
        items: [
          { label: "Batting", href: "/players" },
          { label: "Bowling", href: "/players" },
          { label: "Venues", href: "/venues" },
        ],
      },
    ],
  },
  {
    label: "Matches",
    href: "/matches",
  },
];

// ---------------------------------------------------------------------------
// Dropdown component
// ---------------------------------------------------------------------------

function NavDropdown({ tab, open, onToggle, onClose }: {
  tab: NavTab;
  open: boolean;
  onToggle: () => void;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open, onClose]);

  if (tab.href) {
    return (
      <Link
        href={tab.href}
        className="flex items-center gap-1 px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors rounded-md hover:bg-accent"
      >
        {tab.label}
      </Link>
    );
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={onToggle}
        className={`flex items-center gap-1 px-3 py-1.5 text-sm rounded-md transition-colors ${
          open ? "text-foreground bg-accent" : "text-muted-foreground hover:text-foreground hover:bg-accent"
        }`}
      >
        {tab.label}
        <ChevronDown className={`h-3 w-3 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && tab.sections && (
        <div className="absolute top-full left-0 mt-1 min-w-[200px] rounded-lg border border-border bg-popover shadow-lg py-2 z-50">
          {tab.sections.map((section, i) => (
            <div key={i}>
              {section.heading && (
                <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {section.heading}
                </p>
              )}
              {section.items.map((item) => (
                <Link
                  key={item.href + item.label}
                  href={item.href}
                  onClick={onClose}
                  className="block px-3 py-1.5 text-sm text-popover-foreground hover:bg-accent rounded-md mx-1 transition-colors"
                >
                  {item.label}
                </Link>
              ))}
              {i < tab.sections!.length - 1 && (
                <div className="my-1.5 border-t border-border" />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Navbar
// ---------------------------------------------------------------------------

export function Navbar() {
  const [openTab, setOpenTab] = useState<string | null>(null);

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur-md">
      <div className="w-full px-6 lg:px-10 flex items-center justify-between h-14">
        <Link href="/" className="flex items-center h-11 w-[180px] relative">
          <Image
            src="/logo/design_light.png"
            alt="InsideEdge"
            fill
            className="object-contain object-left dark:hidden"
            priority
          />
          <Image
            src="/logo/design_dark.png"
            alt="InsideEdge"
            fill
            className="object-contain object-left hidden dark:block"
            priority
          />
        </Link>
        <nav className="flex items-center gap-0.5">
          {NAV_TABS.map((tab) => (
            <NavDropdown
              key={tab.label}
              tab={tab}
              open={openTab === tab.label}
              onToggle={() => setOpenTab(openTab === tab.label ? null : tab.label)}
              onClose={() => setOpenTab(null)}
            />
          ))}
          <div className="ml-2">
            <ThemeToggle />
          </div>
        </nav>
      </div>
    </header>
  );
}
