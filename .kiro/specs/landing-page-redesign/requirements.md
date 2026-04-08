# Requirements Document

## Introduction

This document defines the requirements for the InsideEdge landing page redesign. The redesign transforms the current dark-themed landing page into a professional, light-themed experience with four content sections, a match ticker carousel, and a redesigned navbar. The scope covers the landing page (`page.tsx`), root layout (`layout.tsx`), and theme (`globals.css`). Existing sub-pages are not modified.

## Glossary

- **Landing_Page**: The InsideEdge home page rendered at the root URL (`/`), composed of four content sections plus a navbar, ticker, and footer
- **Navbar**: The sticky top navigation bar containing the InsideEdge branding (Lucide icon), navigation links to core pages, and backdrop blur styling
- **Match_Ticker**: A horizontally scrollable carousel below the navbar displaying compact match score cards with tournament filter tabs
- **Match_Spotlight**: The hero section at the top of the landing page showcasing the most recent match in a full-width card format
- **Season_Summary**: A compact horizontal strip displaying season-level summary statistics (match count, top scorer, top wicket taker)
- **Latest_Results**: The left column component in Section 3 displaying the most recent 5-6 match results with scores and outcome badges
- **Top_Performers**: The right column component in Section 3 displaying Orange Cap (top batters) and Purple Cap (top bowlers) tables for the current season
- **Explore_Cards**: A grid of quick-link navigation cards (Players, Teams, Matches, Venues) in Section 4
- **Theme_System**: The CSS custom property system in `globals.css` that defines the color palette for the entire application
- **Skeleton**: A placeholder UI element rendered while data is being fetched from the API, preventing blank screens and layout shift
- **shortName**: A pure utility function that maps full team names to abbreviations (e.g., "Mumbai Indians" → "MI")
- **formatMatchResult**: A pure utility function that produces a human-readable match result string from a match object
- **groupMatchesByTournament**: A pure utility function that partitions an array of matches into groups keyed by tournament name
- **getLatestSeason**: A pure utility function that returns the most recent season string from an array of season counts
- **RecentMatch**: An extended match type that includes innings data (runs, wickets, overs per innings) alongside standard match metadata
- **API**: The FastAPI backend serving cricket data endpoints, hosted on Render free tier

## Requirements

### Requirement 1: Light Theme

**User Story:** As a visitor, I want the landing page to use a clean light theme, so that the site feels professional and modern.

#### Acceptance Criteria

1. THE Theme_System SHALL define `:root` CSS custom properties with light-palette values where background lightness exceeds 0.9 and foreground lightness is below 0.2
2. THE Theme_System SHALL preserve the cyan/teal hue (hue 190) for the `--primary` color, adapted for legibility on light backgrounds
3. THE Theme_System SHALL store the previous dark-palette values under a `.dark` CSS class for future toggle support
4. THE Theme_System SHALL define all color variables using the oklch color space

### Requirement 2: Navbar Redesign

**User Story:** As a visitor, I want a clean navigation bar with proper icons, so that I can navigate the site and recognize the brand.

#### Acceptance Criteria

1. THE Navbar SHALL render the InsideEdge branding using a Lucide React icon component and text, with no emoji characters in the output
2. THE Navbar SHALL provide navigation links to Matches, Players, and Teams pages using shadcn Button components with `variant="ghost"`
3. THE Navbar SHALL remain sticky at the top of the viewport with a backdrop blur effect and a subtle bottom border
4. WHEN a navigation link is clicked, THE Navbar SHALL navigate to the corresponding route (`/matches`, `/players`, `/teams`)

### Requirement 3: Match Ticker

**User Story:** As a cricket fan, I want to see recent match scores in a compact ticker, so that I can quickly scan results without scrolling through the full page.

#### Acceptance Criteria

1. THE Match_Ticker SHALL display recent match scores as compact horizontally-scrollable cards below the Navbar
2. WHEN the Match_Ticker renders a match card, THE Match_Ticker SHALL display team abbreviations (via shortName) and innings scores in `runs/wickets` format
3. WHEN a user clicks a match card in the Match_Ticker, THE Match_Ticker SHALL navigate to `/matches/{match_id}` where `match_id` corresponds to the clicked match
4. THE Match_Ticker SHALL provide left and right scroll buttons using Lucide ChevronLeft and ChevronRight icons
5. WHEN a scroll button is clicked, THE Match_Ticker SHALL scroll the container by a fixed pixel amount with smooth animation, clamped to valid scroll bounds
6. THE Match_Ticker SHALL display shadcn Tabs for tournament filtering with an "All" tab and one tab per unique tournament name
7. WHEN the "All" tab is active, THE Match_Ticker SHALL display all matches
8. WHEN a specific tournament tab is active, THE Match_Ticker SHALL display only matches whose `event_name` matches the selected tournament
9. IF a match has no innings data, THEN THE Match_Ticker SHALL display dashes instead of scores

### Requirement 4: Match Spotlight

**User Story:** As a visitor, I want to see the most recent match prominently displayed, so that I immediately know the latest result.

#### Acceptance Criteria

1. THE Match_Spotlight SHALL display the most recent match from the API response as a full-width shadcn Card with both innings scores, team names, venue, date, and event information
2. THE Match_Spotlight SHALL display the match result text using the formatMatchResult function output
3. THE Match_Spotlight SHALL provide a "View Scorecard" link that navigates to `/matches/{match_id}` for the displayed match
4. WHEN the Match_Spotlight mounts, THE Match_Spotlight SHALL apply a fade-in CSS animation using transforms and opacity only

### Requirement 5: Season Summary

**User Story:** As a visitor, I want a quick glance at the current season stats, so that I can see key highlights without navigating away.

#### Acceptance Criteria

1. THE Season_Summary SHALL display the latest season name, total match count, top scorer name with runs, and top wicket taker name with wickets in a compact horizontal strip
2. THE Season_Summary SHALL use Lucide icons (Calendar, Hash, Flame, Target) to visually label each stat
3. THE Season_Summary SHALL use shadcn Separator components between stat items
4. IF no season data is available, THEN THE Season_Summary SHALL render an empty state without layout shift

### Requirement 6: Latest Results

**User Story:** As a visitor, I want to see recent match results in a list, so that I can review outcomes of the last few matches.

#### Acceptance Criteria

1. THE Latest_Results SHALL display the 5-6 most recent match results inside a shadcn Card, with each row showing team abbreviations, innings scores, and a result badge
2. THE Latest_Results SHALL use shadcn Badge components to indicate match outcome status
3. THE Latest_Results SHALL provide a "View All Matches" link that navigates to `/matches`
4. IF the matches array is empty, THEN THE Latest_Results SHALL display a contextual empty state message

### Requirement 7: Top Performers

**User Story:** As a cricket fan, I want to see the top batters and bowlers for the current season, so that I can track who is leading the Orange and Purple Cap races.

#### Acceptance Criteria

1. THE Top_Performers SHALL display the top 5 batters in an Orange Cap shadcn Card with columns for rank, name, runs, strike rate, fours, and sixes
2. THE Top_Performers SHALL display the top 5 bowlers in a Purple Cap shadcn Card with columns for rank, name, wickets, economy, and bowling average
3. THE Top_Performers SHALL use shadcn Table components for stats display with rank badges using orange and purple color accents respectively
4. THE Top_Performers SHALL use Lucide icons (Flame for Orange Cap, Zap for Purple Cap) in the card headers
5. IF batting or bowling stats are unavailable, THEN THE Top_Performers SHALL display a compact "Stats unavailable" empty state for the affected card

### Requirement 8: Explore Cards

**User Story:** As a visitor, I want quick-link cards to major site sections, so that I can navigate to Players, Teams, Matches, or Venues easily.

#### Acceptance Criteria

1. THE Explore_Cards SHALL render a grid of 4 shadcn Card components linking to Players, Teams, Matches, and Venues pages
2. THE Explore_Cards SHALL display a Lucide icon, title, and short description on each card
3. WHEN a user hovers over an Explore Card, THE Explore_Cards SHALL apply a subtle scale and shadow CSS transition
4. WHEN a user clicks an Explore Card, THE Explore_Cards SHALL navigate to the corresponding route
5. THE Explore_Cards SHALL render as a 2x2 grid on viewports ≥ 1024px and a single column on smaller viewports

### Requirement 9: Data Fetching and Loading

**User Story:** As a visitor, I want the page to load quickly with visible progress, so that I am not staring at a blank screen while data loads.

#### Acceptance Criteria

1. THE Landing_Page SHALL fetch match data and season data in parallel using `Promise.all` on initial load
2. WHEN the latest season is determined, THE Landing_Page SHALL fetch batting and bowling stats for that season in a second parallel batch
3. WHILE data is being fetched, THE Landing_Page SHALL render Skeleton components in place of each content section
4. IF the API is unreachable after 10 seconds, THEN THE Landing_Page SHALL display a subtle informational message indicating the API may be waking up
5. IF any single API call fails, THEN THE Landing_Page SHALL render the failed section with an empty state while other sections with successful data render normally

### Requirement 10: Responsive Layout

**User Story:** As a visitor on any device, I want the landing page to adapt to my screen size, so that the content is readable and usable.

#### Acceptance Criteria

1. WHILE the viewport width is ≥ 1024px, THE Landing_Page SHALL render Section 3 (Latest Results and Top Performers) as two columns in a 3:2 ratio
2. WHILE the viewport width is < 1024px, THE Landing_Page SHALL stack Section 3 components vertically
3. THE Match_Ticker SHALL be horizontally scrollable on all viewport widths

### Requirement 11: Utility Function Correctness

**User Story:** As a developer, I want reliable pure utility functions, so that match data is displayed consistently and correctly across all components.

#### Acceptance Criteria

1. THE shortName function SHALL return the abbreviation for any team name present in the abbreviation map, and return the original team name unchanged for any team name not in the map
2. THE shortName function SHALL be idempotent: applying shortName to its own output SHALL produce the same result
3. THE groupMatchesByTournament function SHALL partition matches such that the sum of all group sizes equals the input array length, with no match appearing in more than one group
4. THE groupMatchesByTournament function SHALL assign matches with a null `event_name` to a group keyed "Other"
5. THE getLatestSeason function SHALL return the season string with the highest numeric value, or null for an empty input array
6. THE formatMatchResult function SHALL return a string for any valid RecentMatch input and SHALL never throw an exception
7. THE formatMatchResult function SHALL return "No result" when `match_result_type` is "no_result", the winner abbreviation with margin when `winning_margin` is present, and an empty string when no outcome information exists

### Requirement 12: Component Library Constraint

**User Story:** As a developer, I want all UI primitives to come from shadcn/ui exclusively, so that the codebase has a consistent component foundation with no third-party UI library dependencies.

#### Acceptance Criteria

1. THE Landing_Page SHALL use only shadcn/ui components (Card, Button, Badge, Tabs, Table, Skeleton, Separator) imported from `@/components/ui/*` for all UI primitives
2. THE Landing_Page SHALL use only Lucide React components for all icons, with no emoji characters rendered anywhere in the output

### Requirement 13: Navigation Integrity

**User Story:** As a visitor, I want every clickable element to link to the correct page, so that I can trust the navigation throughout the landing page.

#### Acceptance Criteria

1. WHEN a match card is rendered in any section, THE Landing_Page SHALL link the card to `/matches/{match_id}` where `match_id` exactly matches the data source value
2. WHEN a player name is rendered in Top_Performers, THE Top_Performers SHALL link the name to `/players/{encoded_name}`

### Requirement 14: Score Display Accuracy

**User Story:** As a cricket fan, I want scores to exactly match the data source, so that I can trust the information displayed.

#### Acceptance Criteria

1. WHEN rendering a match score, THE Landing_Page SHALL display `total_runs` and `total_wickets` values that exactly match the corresponding API response values
2. WHEN rendering a completed match, THE Landing_Page SHALL visually distinguish the winning team from the losing team using bold text or foreground color differentiation

### Requirement 15: Animation Performance

**User Story:** As a visitor, I want smooth animations that do not cause jank, so that the page feels polished and responsive.

#### Acceptance Criteria

1. THE Landing_Page SHALL use only CSS `transform` and `opacity` properties for all animations and transitions
2. THE Landing_Page SHALL not animate layout-triggering properties (width, height, top, left, margin, padding)

### Requirement 16: Graceful Error Handling

**User Story:** As a visitor, I want the page to handle errors gracefully, so that I always see a usable interface even when data is unavailable.

#### Acceptance Criteria

1. IF the API returns a malformed response with missing fields, THEN THE Landing_Page SHALL use optional chaining and nullish coalescing to render degraded content without crashing
2. IF a match has no `innings` data, THEN THE Landing_Page SHALL display dashes in place of scores
3. IF a match has no `event_name`, THEN THE groupMatchesByTournament function SHALL group the match under "Other"
4. IF a match has no `winning_margin`, THEN THE formatMatchResult function SHALL display the winner name without margin details
