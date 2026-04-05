# IPL Auction Data — Research & Implementation Notes

## Problem Statement
Add IPL auction price data to the cricket-analytics platform to enable
value-for-money analysis (runs per crore, wickets per crore), team spending
patterns, and player valuation trends across seasons.

## Sources Evaluated

### iplt20.com (CHOSEN — primary source for 2013-2026)
- URL pattern: `https://www.iplt20.com/auction/{year}`
- Coverage: 2013-2026 (14 seasons)
- Data: server-rendered HTML tables (no JSON API — data is embedded in DOM)
- Extraction: Playwright renders the page, then we extract table data via JS `evaluate()`
- Available years in the dropdown: 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026

#### Table Structure (varies by year)

**Format A (2013-2020):**
- Sold tables: `class="sold-players"`, team from table ID
- Headers: `SR. NO., PLAYER, TYPE, PRICE PAID`
- No base price, no nationality, no capped/uncapped
- 2013 prices in USD (e.g., "625,000"), later years in INR with ₹ prefix
- 8-9 team tables (franchise count varied)

**Format B (2022, 2024):**
- Sold tables: `id="t1-{team-slug}"`, `class="auction-tbl t1"`
- Headers: `SR. NO., PLAYER, NATIONALITY, TYPE, PRICE PAID`
- Has nationality (Indian/Overseas) but no base price
- 2022 also has a special overview table with `TEAM, PLAYER, TYPE, PRICE` headers

**Format C (2025-2026):**
- Sold tables: `id="t3-{team-slug}"`, `class="sold-players t3"`
- Headers: `Sr. No., Player, Base Price, Winning Bid, Capped/Uncapped`
- Richest format: has base price, winning bid, and capped status
- 10 team tables

**Unsold players (all years):**
- Table ID: `t5` (2024-2026) or `t2` (2022)
- Headers vary but always include PLAYER and BASE PRICE
- 2025 had 395 unsold players, 2022 had 396

**Top buys (all years):**
- Table ID: `t4`
- Headers: `SR. NO., TEAM, PLAYER, BASE PRICE, WINNING BID` (or similar)
- Top 20 most expensive purchases

#### Key Observations
- No API endpoint — all data is in the initial HTML response
- DataTables.js is used for client-side sorting/filtering but data is server-rendered
- No player IDs of any kind — only text names
- Price format: Indian numbering (₹27,00,00,000 = 27 crore)
- 2013 used USD pricing, all other years use INR

### ESPNcricinfo
- Squad pages (`/series/ipl-2025-{id}/{team}-squad-{id}/series-squads`): list players with
  role, age, batting/bowling style — but NO auction prices
- `__NEXT_DATA__` JSON on squad pages: confirmed no price/auction/cost/salary fields anywhere
- One static auction page exists for 2014 only: `espncricinfo.com/ipl2014_auction/content/site/ipl2014_auction/index.html`
  - Has structured HTML tables with player, country, type, cost in lakhs and USD
  - Includes retained players (marked NA)
  - URL pattern does NOT work for any other year (404 for 2013, 2015, 2016, 2018, etc.)
- Live blogs exist for recent auctions (e.g., `/live-blog/ipl-2024-auction-as-it-happened-1413398`)
  but these are unstructured text commentary, not tabular data

### Kaggle / GitHub
- No comprehensive all-years IPL auction dataset found
- Various single-year analysis projects exist but none with clean multi-year CSV
- Most projects focus on match data, not auction data

### Wikipedia
- Has auction tables for every year (2008-2026) under "List of {year} Indian Premier League personnel changes"
- Consistent coverage but HTML table format varies year to year
- Scraping Wikipedia tables is fragile and format-dependent
- Could be used as a fallback/validation source

### Team franchise websites (delhicapitals.in, mumbaiindians.com, lucknowsupergiants.in)
- Some have auction pages with Vue.js/Angular templates
- Data loaded via internal APIs (template variables like `{{moneyConverter(player.auction_price)}}`)
- Not practical as a primary source — each franchise has different tech stack

## Player Identity Mapping Challenge

The core challenge: iplt20.com provides only player names (no IDs), while our data
platform uses Cricsheet player_id (8-char hex) and ESPN espn_player_id (numeric).

### Available identifiers per source
| Source | Player ID | Name Format | Example |
|--------|-----------|-------------|---------|
| Cricsheet (people.csv) | `identifier` (hex) | Short name | "V Kohli" |
| Cricsheet (people.csv) | `key_cricinfo` | — | ESPN numeric ID |
| ESPN (__NEXT_DATA__) | `espn_player_id` (numeric) | Full name | "Virat Kohli" |
| iplt20.com | NONE | Full name | "Virat Kohli" |

### Mapping strategy (implemented)
Join path: iplt20.com `player_name` → ESPN `player_long_name` → `espn_player_id` → `dim_players`

Both iplt20.com and ESPN use full names, so the first hop is relatively reliable.
Known edge cases:
- Initials: "T. Natarajan" (iplt20) vs "Thangarasu Natarajan" (ESPN)
- Abbreviations: "KL Rahul" vs "Lokesh Rahul"
- Spelling variations: "Ravichandaran Ashwin" (iplt20) vs "Ravichandran Ashwin" (ESPN)

Estimated accuracy: ~90-95% on name matching. A manual override seed CSV can handle
the remaining mismatches.

### Alternative approaches (not implemented)
1. **Fuzzy matching (Levenshtein/Jaro-Winkler)** — could improve matching but adds
   complexity and still won't be 100%
2. **ESPN squad page scraping** — squad pages have espn_player_id per player but no
   auction prices, so this doesn't help directly
3. **Manual seed CSV for all players** — accurate but not scalable (1500+ players across
   14 seasons)
4. **Bid-by-bid history** — not available in any structured form. Only exists in live TV
   broadcasts and ESPN live blog text commentary. Would require NLP to extract.

## Implementation

### Scraper: `src/enrichment/auction_scraper.py`
- Playwright-based, renders iplt20.com auction pages
- Handles all 3 HTML formats (A/B/C) via format detection
- Extracts both sold and unsold players
- Normalizes prices from Indian format to integer
- Maps table ID slugs to canonical team names

### Bronze: `bronze.auction_results`
- 10 columns: season, player_name, team, player_type, base_price, sold_price,
  nationality, capped_status, status, _auction_key
- Dedup on composite key: season + player_name + status
- 4,042 total rows: 1,480 sold + 2,562 unsold across 19 seasons (2008-2026)
- 2008-2012: from seed CSV (Wikipedia source, USD prices)
- 2013-2026: from iplt20.com scraper (2013 USD, 2014+ INR)
- 100% of sold players have team names

### Runner: `src/enrichment/run_auction_scraper.py`
- CLI: `python -m src.enrichment.run_auction_scraper [--years 2025 2026]`
- Defaults to all years (2013-2026)

### Coverage gaps
- 2008-2012: loaded from manually curated seed CSV (Wikipedia source). 105 rows.
- 2008-2013 prices are in USD, 2014+ in INR — silver layer must handle currency normalization
- Some years have incomplete unsold data (2009-2012 seed CSV only includes sold players)
- Retained players show as "NA" price in some years — need to distinguish from unsold

## Future Improvements
- Add 2008-2012 data via seed CSV
- Build name-matching override seed CSV for known mismatches
- Add retained player detection (players with NA price who are on team rosters)
- Consider scraping ESPN squad pages to get espn_player_id per team per season,
  then join auction data via team+season+name for higher accuracy
- If bid-by-bid data ever becomes available, the bronze schema can be extended
