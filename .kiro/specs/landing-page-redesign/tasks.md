# Implementation Plan: Landing Page Redesign

## Overview

Redesign the InsideEdge landing page from dark theme to light theme with four content sections, a match ticker carousel, and a redesigned navbar. All components use shadcn/ui primitives and Lucide icons exclusively. Implementation proceeds bottom-up: theme first, then shared utilities, then individual components, then page composition and wiring.

## Tasks

- [x] 1. Light theme and utility foundations
  - [x] 1.1 Update `globals.css` to light theme
    - Flip `:root` CSS custom properties to light-palette values (background lightness > 0.9, foreground < 0.2)
    - Preserve cyan/teal hue (190) for `--primary`, darkened for light backgrounds
    - Move current dark values to a `.dark` CSS class for future toggle support
    - All colors in oklch color space
    - Update scrollbar thumb colors for light backgrounds
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 1.2 Create shared utility functions in `apps/web/src/lib/landing-utils.ts`
    - Implement `shortName(teamName: string): string` — team abbreviation map (19 IPL teams)
    - Implement `formatMatchResult(match: RecentMatch): string` — result text with all outcome branches
    - Implement `groupMatchesByTournament(matches): Map<string, RecentMatch[]>` — partition by event_name, null → "Other"
    - Implement `getLatestSeason(seasons: SeasonCount[]): string | null` — max numeric season
    - Define `Innings` and `RecentMatch` interfaces extending existing `Match` type
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 16.3, 16.4_

  - [ ]* 1.3 Write property tests for utility functions (fast-check)
    - **Property 1: shortName idempotency** — `shortName(shortName(x)) === shortName(x)` for all strings
    - **Validates: Requirement 11.2**

  - [ ]* 1.4 Write property test for groupMatchesByTournament
    - **Property 2: Tournament grouping is a complete partition** — sum of group sizes equals input length, no duplicates, null event_name → "Other"
    - **Validates: Requirements 11.3, 11.4, 16.3**

  - [ ]* 1.5 Write property test for getLatestSeason
    - **Property 4: getLatestSeason returns the maximum** — returns season with highest numeric value, null for empty
    - **Validates: Requirement 11.5**

  - [ ]* 1.6 Write property test for formatMatchResult
    - **Property 5: formatMatchResult is a total function** — never throws, returns correct string per match_result_type
    - **Validates: Requirements 11.6, 11.7, 16.4**

- [x] 2. Navbar redesign
  - [x] 2.1 Update Navbar in `layout.tsx`
    - Replace 🏏 emoji with Lucide `Activity` icon
    - Replace plain `<Link>` nav items with shadcn `Button variant="ghost"` components
    - Add Lucide icons to each nav link (Trophy for Matches, Users for Players, Swords for Teams)
    - Keep sticky positioning, backdrop blur, and subtle border-b
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 12.1, 12.2_

- [x] 3. Checkpoint — Verify theme and navbar
  - Ensure the light theme renders correctly and navbar displays with Lucide icons, no emojis. Ask the user if questions arise.

- [x] 4. Match Ticker component
  - [x] 4.1 Create `apps/web/src/components/home/match-ticker.tsx`
    - Accept `matches: RecentMatch[]` as props
    - Render horizontally scrollable compact match cards with team abbreviations and `runs/wickets` scores
    - Add shadcn Tabs for tournament filtering ("All" + per-tournament tabs) using `groupMatchesByTournament`
    - Add left/right scroll buttons with Lucide ChevronLeft/ChevronRight
    - Implement smooth scroll (300px per click, clamped to valid bounds)
    - Each card links to `/matches/{match_id}`
    - Display dashes for matches with no innings data
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 12.1, 12.2, 13.1, 14.1, 14.2, 15.1, 15.2_

  - [ ]* 4.2 Write property test for tournament filter correctness
    - **Property 3: Tournament filter correctness** — "all" returns full array, specific tab returns only matching event_name, result length ≤ input length
    - **Validates: Requirements 3.7, 3.8**

- [x] 5. Match Spotlight component
  - [x] 5.1 Create `apps/web/src/components/home/match-spotlight.tsx`
    - Accept the most recent match as props
    - Render full-width shadcn Card with both innings scores, team names, venue, date, event info
    - Display result text via `formatMatchResult`
    - Add "View Scorecard" link to `/matches/{match_id}`
    - Apply fade-in CSS animation using transform and opacity only
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 12.1, 13.1, 14.1, 14.2, 15.1, 15.2_

- [x] 6. Season Summary component
  - [x] 6.1 Create `apps/web/src/components/home/season-summary.tsx`
    - Accept season name, match count, top scorer, top wicket taker as props
    - Render compact horizontal strip with Lucide icons (Calendar, Hash, Flame, Target)
    - Use shadcn Separator between stat items
    - Handle empty state without layout shift
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 12.1, 12.2_

- [x] 7. Checkpoint — Verify ticker, spotlight, and season summary
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Latest Results component
  - [x] 8.1 Create `apps/web/src/components/home/latest-results.tsx`
    - Accept recent matches as props, display 5-6 most recent results
    - Render inside shadcn Card with team abbreviations, innings scores, and shadcn Badge for result status
    - Add "View All Matches" link to `/matches`
    - Handle empty array with contextual empty state message
    - Visually distinguish winning team (bold/foreground color)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 12.1, 13.1, 14.1, 14.2_

- [x] 9. Top Performers component
  - [x] 9.1 Create `apps/web/src/components/home/top-performers.tsx`
    - Accept batters, bowlers, and season as props
    - Render Orange Cap card: top 5 batters with rank, name, runs, strike rate, fours, sixes using shadcn Table
    - Render Purple Cap card: top 5 bowlers with rank, name, wickets, economy, bowling average using shadcn Table
    - Use orange/purple color accents for rank badges
    - Use Lucide icons (Flame for Orange Cap, Zap for Purple Cap) in card headers
    - Link player names to `/players/{encoded_name}`
    - Handle empty stats with "Stats unavailable" empty state
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 12.1, 12.2, 13.2_

- [x] 10. Explore Cards component
  - [x] 10.1 Create `apps/web/src/components/home/explore-cards.tsx`
    - Render 4 shadcn Cards (Players, Teams, Matches, Venues) with Lucide icons, titles, descriptions
    - 2x2 grid on viewports ≥ 1024px, single column on smaller
    - Hover effect: subtle scale + shadow CSS transition (transform and opacity only)
    - Each card navigates to corresponding route
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 12.1, 12.2, 15.1, 15.2_

- [x] 11. Checkpoint — Verify all section components
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Page composition and data fetching
  - [x] 12.1 Rewrite `apps/web/src/app/page.tsx` with new landing page composition
    - Import all new section components (MatchTicker, MatchSpotlight, SeasonSummary, LatestResults, TopPerformers, ExploreCards)
    - Implement parallel data fetching: `Promise.all` for matches + seasons on initial load
    - Fetch batting/bowling stats in second parallel batch after latest season is determined
    - Render Skeleton components for each section while data loads
    - Show "API may be waking up" message after 10s timeout
    - Handle partial API failures: failed sections show empty state, successful sections render normally
    - Use optional chaining and nullish coalescing for malformed responses
    - Section 3 layout: two columns (3:2 ratio) on lg, stacked on mobile
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 10.1, 10.2, 10.3, 16.1, 16.2_

  - [x] 12.2 Delete old components
    - Delete `apps/web/src/components/home/recent-matches.tsx` (replaced by match-ticker + latest-results)
    - Delete `apps/web/src/components/home/tournament-sections.tsx` (replaced by explore-cards + season-summary)
    - _Requirements: 12.1_

- [x] 13. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests use fast-check and validate correctness properties from the design document
- All components use shadcn/ui primitives and Lucide icons exclusively — no emoji, no third-party UI libraries
- The design uses TypeScript/React (Next.js) throughout — no language selection needed
