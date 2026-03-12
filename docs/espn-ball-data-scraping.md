# ESPN Ball-by-Ball Spatial Data — Scraping Research

## What This Data Is

ESPN Cricinfo stores proprietary ball-level spatial data that is NOT available in Cricsheet
or any other free/open source. This includes:

| Field | Description | Available From | Coverage |
|-------|-------------|----------------|----------|
| `wagonX` | X coordinate on wagon wheel (0-300 range) | 2008 | 100% of balls |
| `wagonY` | Y coordinate on wagon wheel (0-300 range) | 2008 | 100% of balls |
| `wagonZone` | Wagon wheel zone (0-8, 0=dot ball/no shot) | 2008 | 100% of balls |
| `pitchLine` | Line of delivery | ~2012-2015 | 100% from ~2015 |
| `pitchLength` | Length of delivery | ~2012-2015 | 100% from ~2015 |
| `shotType` | Type of shot played | 2008 | ~98%+ of balls |
| `shotControl` | Shot control rating (1=controlled, 2=uncontrolled) | ~2012-2015 | 100% from ~2015 |

### pitchLine values
`DOWN_LEG`, `ON_THE_STUMPS`, `OUTSIDE_OFFSTUMP`, `WIDE_DOWN_LEG`, `WIDE_OUTSIDE_OFFSTUMP`

### pitchLength values
`FULL`, `FULL_TOSS`, `GOOD_LENGTH`, `SHORT`, `SHORT_OF_A_GOOD_LENGTH`, `YORKER`

### shotType values (modern, 2015+)
`COVER_DRIVE`, `CUT_SHOT`, `DAB`, `DEFENDED`, `FLICK`, `HOOK`, `LEFT_ALONE`,
`LEG_GLANCE`, `ON_DRIVE`, `PULL`, `PUSH`, `RAMP`, `REVERSE_SWEEP`, `SLOG_SHOT`,
`SLOG_SWEEP`, `SQUARE_DRIVE`, `STEERED`, `STRAIGHT_DRIVE`, `SWEEP_SHOT`, `UPPER_CUT`

### shotType values (legacy, 2008-era)
Different naming convention: `CUT_SHOT_ON_BACK_FOOT`, `FORWARD_DEFENCE`,
`OFF_SIDE_DRIVE_ON_FRONT_FOOT`, `NO_SHOT`, etc. Will need a mapping table
to normalize old and new names.

### shotControl values
`1` = controlled, `2` = uncontrolled. Missing on wides (no shot played).

### Other fields available per ball (from the commentary API)
- `id` — unique ESPN ball ID
- `inningNumber` — 1 or 2
- `overNumber` — 1-indexed over number
- `ballNumber` — ball within the over
- `oversActual` — e.g. 17.6 (over.ball format)
- `oversUnique` — e.g. 17.06
- `batsmanPlayerId` — ESPN player ID for batter
- `bowlerPlayerId` — ESPN player ID for bowler
- `nonStrikerPlayerId` — ESPN player ID for non-striker
- `batsmanRuns` — runs scored by batter
- `totalRuns` — total runs off the ball
- `totalInningRuns` — cumulative innings total
- `totalInningWickets` — cumulative wickets
- `isFour`, `isSix`, `isWicket` — boolean flags
- `wides`, `noballs`, `byes`, `legbyes`, `penalties` — extras
- `dismissalType` — e.g. "caught", "bowled" (null if not out)
- `dismissalText` — human-readable dismissal description
- `outPlayerId` — ESPN player ID of dismissed batter
- `timestamp` — ISO timestamp of the ball
- `title` — human-readable ball description (e.g. "Bumrah to Kohli, FOUR")
- `commentTextItems` — array of commentary text objects
- `smartStats` — array of contextual stats shown during commentary
- `predictions` — win probability predictions (if available)

## Where The Data Lives

The data is served by ESPN's commentary API:
```
https://hs-consumer-api.espncricinfo.com/v1/pages/match/comments
  ?lang=en
  &seriesId={espn_series_id}
  &matchId={espn_match_id}
  &inningNumber={1|2}
  &commentType=ALL
  &sortDirection=DESC
  &fromInningOver={over_number}
```

The API returns paginated responses:
- ~12 balls per page (roughly 2 overs)
- `nextInningOver` field for pagination (null when no more data)
- Sorted descending (latest over first)
- A T20 innings (~120 balls) requires ~10 API pages

The initial page load (`__NEXT_DATA__`) also contains the last ~12 balls.

## What Works

### Working approach: Playwright route interception via scroll-triggered requests

The ONLY reliable way to get this data is:

1. Load the ESPN commentary page in Playwright (WebKit, headless)
2. Set up `page.route("**/hs-consumer-api**/comments**", handler)` to intercept API calls
3. In the handler, use `route.fetch()` to let the request through and capture the response
4. Scroll the page to trigger the page's own JavaScript to make API calls
5. The page uses an IntersectionObserver — when the user scrolls near the bottom,
   it fetches the next page of commentary

**Critical detail**: `route.fetch()` only succeeds (200) when intercepting a request
that the PAGE'S OWN JavaScript initiated. If you trigger a fetch from `page.evaluate()`,
the route still intercepts it, but `route.fetch()` gets 403 from ESPN's WAF.

### Scroll technique that works reliably

"Bounce scroll" — scroll to bottom, up a bit, then back down:
```python
height = await page.evaluate("document.body.scrollHeight")
await page.evaluate(f"window.scrollTo(0, {height})")        # bottom
await asyncio.sleep(0.4)
await page.evaluate(f"window.scrollTo(0, {height - 500})")  # up
await asyncio.sleep(0.2)
await page.evaluate(f"window.scrollTo(0, {height + 1000})") # back down
await asyncio.sleep(1.2)
```

This reliably triggers the IntersectionObserver. With this approach, a full T20 innings
(~10 API pages) loads in about 20 seconds.

### Verified: complete innings capture

Tested on IPL 2025 Final (PBKS vs RCB, match 1473511):
- Inning 2: 123 balls captured (12 from __NEXT_DATA__ + 111 from 9 API pages)
- `nextInningOver` reached `None` — confirmed complete
- All spatial fields present on every ball

### Initial page data

The `__NEXT_DATA__` on the commentary page always contains:
- `content.comments` — last ~12 balls of the most recent innings (inning 2)
- `content.currentInningNumber` — always 2 (page defaults to most recent)
- `content.nextInningOver` — pagination cursor for the API
- `content.innings` — list of innings with team names and inning numbers

## What Does NOT Work

### 1. Direct API calls (any method) — 403

ESPN has a WAF (Web Application Firewall) that blocks all programmatic API calls:

- `page.evaluate("fetch(url)")` — 403
- `page.evaluate("new XMLHttpRequest()")` — 403
- `context.request.get(url)` (Playwright API context) — 403
- `page.goto(api_url)` (navigate directly to API) — 403
- `page.evaluate` with injected `window.__originalFetch` — 403
- iframe navigation to API URL — blocked (cross-origin)
- `fetch()` with `credentials: 'include'`, custom headers, `x-requested-with` — all 403

The WAF distinguishes between:
- Requests initiated by the page's own bundled JavaScript (allowed)
- Requests initiated by injected/evaluated JavaScript (blocked)

This is likely based on:
- Request origin/initiator chain tracking
- Anti-bot tokens embedded in the page's JS bundle
- TLS fingerprinting differences between Playwright's fetch and the browser's native fetch

### 2. Next.js `_next/data` endpoint — 403

ESPN is a Next.js app. Normally `_next/data/{buildId}/...json` returns the same data
as `__NEXT_DATA__` but as a JSON API. ESPN's WAF blocks this too.

### 3. URL query parameters for pagination — ignored

The commentary page URL ignores query parameters:
- `?innings=1`, `?inningNumber=1`, `?fromInningOver=5` — all ignored
- `__NEXT_DATA__` always returns the same data regardless of URL params
- The page is a single-page app; pagination is purely client-side via API

### 4. Innings switching via tab click — SOLVED (see below)

Initial attempts using tab clicks were unreliable. The correct approach uses the
dropdown button, not the tab. See "Working approach: Innings switching via dropdown".

## Recommended Implementation Strategy

### Working approach: Innings switching via dropdown (SOLVED)

The commentary page has a dropdown button showing the current team abbreviation
(e.g. "RCB"). Clicking it reveals a dropdown with both teams. Selecting the other
team triggers an API call for that innings' data, then scrolling loads the rest.

Steps:
1. Click `button:has-text("{current_team_abbr}")` to open the dropdown
2. Click `div.ds-cursor-pointer:has-text("{target_team_abbr}")` to switch
3. Wait ~2s for the API response, then scroll to load remaining balls

This approach is reliable and captures both innings in a single page session.

### Single-page, single-match flow

For each match, open ONE page instance:
1. Load commentary page -> get __NEXT_DATA__ (inning 2, last ~12 balls)
2. Set up route interception for commentary API
3. Scroll to load all remaining inning 2 balls
4. Open dropdown, click inning 1 team to switch innings
5. Scroll to load all inning 1 balls
6. Deduplicate and return all balls for both innings

Verified on RCB vs LSG (match 1422133): 248 balls total (126 inn1 + 122 inn2),
100% spatial data coverage, all 20 overs per innings, zero duplicates.
Runs in ~30 seconds per match.

### Performance estimate

Per match (~30 seconds):
- Page load: ~3-5 seconds
- Scroll inning 2: ~10 seconds
- Innings switch + scroll inning 1: ~15 seconds
- Rate limiting between matches: 4 seconds

For all 1169 matches: ~30s/match x 1169 = ~10 hours
Uses batch persistence (like existing ESPN enrichment) to avoid losing progress.

### Storage

New bronze table: `bronze.espn_ball_data`

Key columns to extract per ball:
- `cricsheet_match_id` (our FK)
- `espn_match_id`, `espn_ball_id` (ESPN's IDs)
- `inning_number`, `over_number`, `ball_number`
- `batsman_player_id`, `bowler_player_id` (ESPN player IDs)
- `batsman_runs`, `total_runs`, `is_four`, `is_six`, `is_wicket`
- `wagon_x`, `wagon_y`, `wagon_zone`
- `pitch_line`, `pitch_length`
- `shot_type`, `shot_control`
- `dismissal_type`, `out_player_id`
- `wides`, `noballs`, `byes`, `legbyes`
- `timestamp`

Estimated size: ~240 balls/match x 1169 matches = ~280K rows

### Browser requirements

- WebKit only (Chromium not installed, and WebKit works fine)
- Headless mode works
- User agent should mimic Safari on macOS
- Viewport height of 2000px helps (more content visible = fewer scroll iterations)

## Files Referenced

- `src/enrichment/ball_scraper.py` — production ball-by-ball scraper module
- `src/enrichment/run_ball_scraper.py` — CLI entry point for ball data scraping
- `src/enrichment/bronze_loader.py` — ESPN data loader (espn_matches + espn_ball_data)
- `src/enrichment/match_scraper.py` — ESPN match-level scorecard scraper
- `src/enrichment/series_resolver.py` — resolves ESPN series IDs
- `src/config.py` — centralized settings
