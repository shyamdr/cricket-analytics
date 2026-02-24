# Data Enrichment Strategy

## Problem Statement

Cricsheet provides excellent ball-by-ball data but lacks several dimensions that would
unlock deeper analytics, ML features, and a more complete cricket platform. Past attempts
at scraping ESPNcricinfo/Cricbuzz were fragile — scrapers broke within weeks as sites
changed their HTML structure.

## Current Data (Cricsheet)

What we have:
- 1,169 IPL matches (2008–2025), ball-by-ball delivery data
- Player names + identifiers (links to people.csv with cross-reference keys)
- Match metadata: date, venue, city, teams, toss, outcome, player of match
- Full batting/bowling scorecards derived from deliveries

What's missing:
- Captain / wicketkeeper per match
- Player roles (batter, bowler, allrounder, keeper)
- Venue coordinates (lat/lng)
- Weather conditions during the match
- Match timing (day/night, start time)
- Player age / date of birth
- Auction prices
- ICC or custom player/team ratings
- Pitch characteristics
- Advanced ball tracking (Hawk-Eye trajectory, spin, swing, fielding positions)
- Live/streaming data for ongoing matches

## Data Sources Evaluated

### ESPNcricinfo (via python-espncricinfo)

**Repo:** https://github.com/outside-edge/python-espncricinfo
**Method:** Playwright (headless WebKit) → extracts `__NEXT_DATA__` JSON from match pages
**Why it's more resilient than raw scraping:**
- Uses a real browser engine — Akamai CDN can't easily fingerprint/block it
- Reads `__NEXT_DATA__` which is a Next.js framework standard — ESPN would have to
  change their entire frontend framework to break this pattern
- Actively maintained library (updated for ESPN's new site structure)

**Available data from ESPN `__NEXT_DATA__`:**
- `matchPlayers.teamPlayers` — playing XI with player roles (captain, keeper, batter, bowler, allrounder)
- `match.ground` — venue details including location info
- `match.floodlit` — day/night indicator
- `match.startDate` / `match.startTime` — match start time with timezone
- Full batting/bowling scorecards with ESPN player IDs
- `match.series` — series/tournament context
- Player profiles (DOB, batting/bowling style, teams) via Player class

**Mapping Cricsheet → ESPN:**
- people.csv has `key_cricinfo` for player ID mapping
- Match mapping: match on (date + team1 + team2) or build a match_id lookup table
- ESPN match IDs can be discovered via `Match.get_recent_matches(date=...)` or
  from the series pages

**Performance:** ~2-5 seconds per match (Playwright overhead). For 1,169 matches,
expect ~1.5-2 hours for a full historical scrape. Only new matches need scraping after that.

### Open-Meteo (Historical Weather)

**URL:** https://open-meteo.com/en/docs/historical-weather-api
**Method:** REST API, no authentication required
**Cost:** Free for non-commercial use
**Coverage:** Historical weather data back to 1940, hourly resolution
**Available fields:** temperature, humidity, wind speed/direction, precipitation,
cloud cover, pressure, dew point
**Reliability:** Open-source project, very stable API, no rate limits for reasonable use
**Requirement:** Venue coordinates (lat/lng) + match date + approximate time

### OpenStreetMap Nominatim (Geocoding)

**URL:** https://nominatim.openstreetmap.org
**Method:** REST API, no authentication required
**Cost:** Free (rate limit: 1 request/second)
**Use case:** Convert venue names → lat/lng coordinates
**Alternative:** For only 63 venues, a manually curated seed CSV is more reliable

### Cricbuzz

**Mobile app API** exists (e.g. `cricbuzz.com/api/html/cricket-scorecard/{match_id}`)
but is undocumented and less stable than ESPN's approach. Cricbuzz has some unique data
(playing conditions, detailed toss info) but ESPN covers most of what we need.
Keep as a secondary source if ESPN gaps are found.

### Hawk-Eye / Ball Tracking Data

**Status:** Not available for free. Proprietary data owned by BCCI/Star Sports/Hawk-Eye.
No public API or dataset exists. This includes ball trajectory, spin rate, swing,
fielding positions, wagon wheels, pitch maps, etc.

**Workaround:** Derive proxy metrics from existing Cricsheet data:
- Dot ball percentage by phase (powerplay/middle/death)
- Boundary frequency by over
- Scoring patterns (pace vs spin)
- Dismissal type distribution per venue (proxy for pitch behavior)
- Bowler variation metrics (wides as proxy for line/length inconsistency)

## Enrichment Roadmap

### Phase 1: Venue Coordinates + Weather (low effort, high value)

**Effort:** 1-2 days
**Dependencies:** None

1. Create `src/dbt/seeds/seed_venue_coordinates.csv` with 63 venues + lat/lng
   - Use Nominatim API for initial geocoding, manually verify
2. Build weather enrichment pipeline:
   - For each match: venue coords + match_date → Open-Meteo historical API
   - Store in `bronze.weather` table
   - dbt model: `silver.stg_weather` → join with `dim_matches`
3. New gold model: `dim_venues` enriched with coordinates
4. New gold model or enriched `dim_matches` with weather columns

### Phase 2: ESPN Enrichment (the big unlock)

**Effort:** 3-5 days
**Dependencies:** python-espncricinfo + Playwright

1. Build match ID mapping: Cricsheet match_id → ESPN match_id
   - Strategy: match on (date + team1 + team2) using ESPN series pages
   - Store mapping in a seed or bronze table
2. One-time historical scrape of all 1,169 matches:
   - Extract: captain, keeper, player roles, match start time, floodlit status
   - Rate limit: 1 request per 3-5 seconds
   - Store raw JSON in `bronze.espn_matches`
3. dbt models:
   - `silver.stg_espn_matches` — cleaned/typed ESPN enrichment data
   - Enrich `dim_matches` with captain, keeper, day/night, start_time
   - Enrich `dim_players` with roles, batting/bowling style
4. Incremental updates: only scrape new matches after initial bulk load

### Phase 3: Ratings + Auction + Player Profiles

**Effort:** 3-5 days
**Dependencies:** Phase 2 (for player DOB from ESPN)

1. **Elo rating system** — Python implementation:
   - Team Elo: start at 1500, adjust per match based on outcome + opponent strength
   - Player batting/bowling Elo: adjust per innings
   - Store historical ratings as a time series in DuckDB
   - Great portfolio piece — fully transparent, tunable parameters
2. **Auction prices** — seed CSVs per season:
   - Publicly available data from IPL auction results
   - ~50-100 rows per season × 18 seasons
   - Enables value-for-money analysis (runs per crore, etc.)
3. **Player DOB/age** — from ESPN Player profiles:
   - Use `key_cricinfo` from people.csv to fetch player pages
   - Calculate age at time of each match
   - Enables age-based performance analysis

### Phase 4: Derived Analytics (no new data needed)

**Effort:** 2-3 days
**Dependencies:** Phases 1-3 for full power, but can start with existing data

1. **Pitch profiles** — per-venue derived metrics:
   - Average first innings score, average wickets per match
   - Pace vs spin wicket ratio
   - Boundary percentage, dot ball percentage
   - Dew factor (1st vs 2nd innings performance at night matches)
2. **Advanced ball-by-ball metrics** from existing Cricsheet data:
   - Phase-wise analysis (powerplay/middle/death overs)
   - Matchup matrices (batter vs bowler type)
   - Pressure index (required run rate × wickets lost)
   - Clutch performance metrics (performance in close finishes)
3. **Day/night inference** (if ESPN data unavailable):
   - Two matches on same date → first is afternoon (3:30 PM IST), second is evening (7:30 PM IST)
   - Single match days → evening
   - Covers ~95% of IPL matches correctly

### Future: Live Data Pipeline

**Dependencies:** Running service during match hours

- CricAPI free tier (100 requests/day) for live scores
- Cricbuzz mobile API for ball-by-ball polling (~30 second intervals)
- Would need a lightweight service (could be a Dagster sensor) that activates during IPL season
- Not relevant for historical analysis — park for later

## Key Decisions

1. **ESPN over Cricbuzz** as primary enrichment source — more data, better library support
2. **Playwright-based scraping** over raw HTTP — resilient to CDN blocking
3. **One-time bulk scrape + incremental** — don't re-scrape historical data
4. **Seed files for small/stable datasets** (venues, auction prices) — more reliable than APIs
5. **Derived metrics over unavailable data** — pitch profiles from match data instead of
   waiting for Hawk-Eye data that will never be free
6. **Open-Meteo for weather** — genuinely free, reliable, no API key, data back to 1940

## About Cricsheet's Data Source

Cricsheet (maintained by Stephen Rushe) almost certainly sources its ball-by-ball data from
ESPNcricinfo's ball-by-ball commentary feed. Every ESPN match page has a "Ball by Ball" tab
with delivery-level data (batter, bowler, runs, extras, wickets) — this maps almost 1:1 to
Cricsheet's JSON structure. The project has been running since ~2012 when ESPN's API was
more open. The data is provided freely under a non-commercial license.
