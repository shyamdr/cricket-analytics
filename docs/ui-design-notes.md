# InsideEdge — UI Design Notes

## Design Philosophy
- Broadcast-quality feel — like watching a match on TV, not reading a stats spreadsheet
- Minimalist at the top, dense stats as you scroll down
- Player headshots are central to the experience (humanizes the data)
- Dark theme, clean typography, cricket-focused

## Live Match Page (Phase 2 — the crown jewel)

### Top Section (above the fold — broadcast style)
- Clean, open background (stadium image or gradient, like the reference screenshot)
- Score in the center: team name, score/wickets (overs), run rate
- Team emblems/flags flanking the score

### Left Side — Batsmen
- Two player headshots stacked/overlapping
- Striker: larger, highlighted, in front
- Non-striker: slightly smaller, beside/behind, slightly shadowed
- Below headshots: R (B) 4s 6s for each batter

### Right Side — Bowler
- Bowler headshot (same size as striker)
- Below: O R W Econ

### Center (below score)
- Partnership: runs (balls)
- Extras
- Required rate (if chasing)

### Bottom Strip — Ball-by-ball
- Horizontal strip showing each ball of the current over
- Color-coded: dot (grey), 1-3 (white), 4 (blue), 6 (green), wicket (red), wide/noball (yellow)
- Shows the last 2-3 overs scrollable

### Below the Fold (scroll down for deep stats)
All of these in scrollable sections:
- Wagon wheel (building ball-by-ball from ESPN spatial data)
- Bowling map / pitch map (pitch_line × pitch_length heat map)
- Manhattan chart (runs per over, bar chart)
- Worm / heartbeat chart (cumulative runs over time)
- Partnership breakdown (who scored what, how many balls)
- Next to come (batting order, who's in the pavilion)
- Fall of wickets timeline
- Phase breakdown (powerplay/middle/death stats for both teams)
- Batting quality index (shot_control rolling window)
- Matchup stats (current batter vs current bowler, historical)

### Data Source for Live
- ESPN hs-consumer-api via Playwright route interception
- Poll every 20-25 seconds
- ~1-2 minute lag behind broadcast

### Player Headshots
- Source: ESPN player images (available via player profile pages)
- Cache locally / in CDN
- Fallback: initials in a colored circle (like Google contacts)

## Landing Page (Phase 1 — historical data)

### Section 1: Match Spotlight
- Most recent match (or current live match if available)
- Full-width hero card with scores, result, venue
- Broadcast-style layout (teams + scores, not just text)

### Section 2: Season at a Glance
- Compact horizontal strip: "IPL 2026 — 6 matches · Top scorer: V Kohli (287) · Top wickets: YS Chahal (12)"

### Section 3: Two-column
- Left: Latest 5-6 match results with scores
- Right: Orange Cap + Purple Cap (current season top 5)

### Section 4: Explore
- Quick link cards: Players, Teams, Matches, Venues

## General UI Principles
- Mobile-responsive (but desktop-first for the live experience)
- Loading skeletons for all async data (never blank screens)
- Smooth transitions and subtle animations
- No clutter — every element earns its space
- Cricket-first color language: green for win, red for loss/wicket, cyan for accent, orange for runs leader, purple for wickets leader

## Reference
- Screenshot reference: broadcast-style scoring app with stadium background, centered score, player headshots, ball-by-ball strip at bottom
- Inspiration: TV broadcast graphics (Star Sports, Sky Sports), not web dashboards
