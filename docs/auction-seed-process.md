# IPL Auction Seed File — Process & Progress

## Overview
Building a curated seed CSV (`src/dbt/seeds/espn_squads.csv`) with complete squad data for every IPL season. This is the single source of truth for player contracts/salaries.

## Source
- **Player list + names**: ESPN squad pages (`__NEXT_DATA__` JSON) — gives player_name, player_long_name, espn_id, player_role, is_withdrawn
- **Prices + acquisition types**: Wikipedia personnel changes pages + web research
- **Names are NEVER changed from ESPN** — Wikipedia is only used for price/type lookup

## Columns
season, team, player_name, player_long_name, espn_id, player_role, is_withdrawn, nationality, acquisition_type, base_price, sold_price, currency, sold_price_inr, base_price_inr, sold_price_crores, capped_status, replaced_player, price_bucket, is_mega_auction_year

## Acquisition Types
- `sold` — bought at IPL auction (has specific auction price)
- `retained` — continued from previous year's contract (same price)
- `signed` — signed outside the auction (pre/post auction signings, domestic signings)
- `replacement` — mid-season replacement for unavailable player (price = replaced player's price)
- `traded` — transferred between teams (keeps existing price)
- `icon_player` — 2008 icon players (Tendulkar, Ganguly, Dravid, Yuvraj, Sehwag)
- `supplementary` — under-19/draft picks

## Contract Rules
- **2008 auction**: 3-year contracts (2008, 2009, 2010) — same salary each year
- **2008 signed players**: Ranji Trophy players $50K, non-Ranji $20K (USD)
- **2008 icon players**: 15% more than highest paid player on team
- **2009-2010**: Players retained from 2008 keep same price. New auction buys get new price.
- **2011**: Next mega auction — all players re-enter pool
- **Replacements**: Paid at most the same as the player they replaced (IPL rule)
- **All prices 2008-2013 are in USD**. 2014+ in INR.

## Process Per Year (step by step)

### Step 1: Scrape ESPN squad
- Scrape ESPN squad pages for the year
- Get: player_name, player_long_name, espn_id, player_role, is_withdrawn
- Set is_mega_auction_year (Y for 2008/2011/2014/2018/2022/2025, N otherwise)
- Append to seed file with all price/type columns empty

### Step 2: Fill nationality
- Match against ESPN match data (stg_espn_players) by long name or short name
- Remaining unknowns: Indian domestic → "India", known overseas → "Overseas"

### Step 3: Mark retained players
- Match 2009 players against 2008 seed by player_name
- If found with price → mark as "retained", copy all price fields

### Step 4: Apply Wikipedia changes
- Read Wikipedia personnel changes page for the year
- Apply in order:
  1. Auction results → "sold" with prices
  2. Trades → "traded" (override retained if needed)
  3. Pre/post auction signings → "signed" with prices where known
  4. Replacement players → "signed" (or "replacement" if applicable)
  5. Withdrawals → set is_withdrawn = Y (don't change other columns)
  6. Retirements → set is_withdrawn = Y if record exists

### Step 5: Fill remaining
- Any player still without acquisition_type → "signed"
- Research prices for remaining players (web search, AI estimates based on player tier)
- All prices in USD for 2008-2013 seasons

### Step 6: Verify
- 0 null nationality
- 0 null acquisition_type
- 0 null sold_price
- 0 null price_bucket
- 0 null is_mega_auction_year
- Names unchanged from ESPN
- Create backup file after verification

## Completed Seasons

### 2008 (Mega Auction)
- **Total**: 201 players, 8 teams
- **Withdrawn**: 11
- **Types**: icon_player=5, sold=89, signed=86, supplementary=14, replacement=7
- **Backup**: `espn_squads_backup_2008.csv`
- **Notes**:
  - Icon players: Tendulkar (MI), Ganguly (KKR), Dravid (RCB), Yuvraj (KXIP), Sehwag (DD)
  - 7 replacement players with prices derived from replaced player
  - Muralidaran: ESPN="Muthiah Muralidaran", Wiki="Muttiah Muralitharan" — matched via manual mapping, name kept as ESPN
  - Laxmi Shukla: ESPN="Laxmi Shukla", Wiki="Laxmi Ratan Shukla" — matched via manual mapping

### 2009 (Mini Auction — 3-year contract continues)
- **Total**: 232 players, 8 teams
- **Withdrawn**: 23 (many Australian players withdrew for Ashes, Pakistani players suspended)
- **Types**: retained=138, sold=17, signed=70, traded=7
- **Backup**: `espn_squads_backup_2008_2009.csv`
- **Wikipedia page**: https://en.wikipedia.org/wiki/List_of_2009_Indian_Premier_League_personnel_changes
- **Key changes from 2008**:
  - 17 auction buys (Pietersen $1.55M, Flintoff $1.55M highest)
  - 7 trades (Nehra↔Dhawan, Zaheer↔Uthappa, 3-team trade)
  - Pre-auction signings: Warner $250K, Nannes $200K, McDonald $100K, etc.
  - Post-auction signings: Ojha $50K, Kamran Khan $24K, etc.
  - Replacement signings: Mendis $800K, Hodge $600K, Bravo (retained), Jadeja $30K, Kohli $30K
  - 13 withdrawals from Wikipedia + ESPN's own withdrawn flags
- **Name mismatches handled**:
  - JP Duminy: ESPN="Jean-Paul Duminy" — matched manually
  - Rob Quiney: ESPN="Rob Quiney", Wiki="Robert Quiney" — matched manually
  - Sachin Rana, Monish Parmar: not in ESPN 2009 squad — skipped
- **Domestic player prices**: Estimated based on tier (₹6-12L → $20K, ₹12-20L → $35K, ₹20-30L → $55K)

### 2009 — Addendum (missing players from Cricsheet match data)
- 3 players found in 2009 playing XIs but not in ESPN squad page: A Chopra (retained from 2008 KKR), SB Bangar (signed, was 2008 DC), SS Sarkar (signed uncapped ₹8L)

### 2010 — Addendum (missing players from Cricsheet match data)
- 18 players found in 2010 playing XIs but not in ESPN squad page
- Includes SR Watson (RR), DJ Hussey (KKR), DL Vettori (DD) and other retained/signed players
- ESPN squad pages are incomplete — they miss some retained players and mid-season signings

### 2010 (Mini Auction — 3-year contract final year)
- **Total**: 192 players, 8 teams
- **Withdrawn**: 4 (Oram, Martyn, Mascarenhas, Graeme Smith)
- **Types**: retained=130, signed=43, sold=11, replacement=4, traded=3, draft=1
- **Backup**: `espn_squads_backup_2008_2009_2010.csv`
- **Wikipedia page**: https://en.wikipedia.org/wiki/List_of_2010_Indian_Premier_League_personnel_changes
- **Key changes from 2009**:
  - 11 auction buys (Bond $750K, Pollard $750K highest)
  - 3 trades (Henriques → DD, Shah + Tiwary → KKR)
  - 1 under-19 draft pick: Harmeet Singh (DC) at ₹800,000 ($18K). Harshal Patel (MI) not in ESPN squad — skipped.
  - 4 replacements: Bollinger for Oram (CSK), Theron for Jerome Taylor (KXIP), Lumb for Graeme Smith (RR), SPD Smith for Jesse Ryder (RCB)
  - Hussey retained from 2008 at $350K (was in 2008 squad but not 2009)
  - Kaif and Abdulla: retained overridden to sold (new auction prices)
  - Martyn: sold at auction but marked withdrawn
- **New acquisition type**: `draft` — for under-19/draft picks with specific draft price (distinct from `supplementary` which was 2008 only)

### 2011 (Mega Auction — 10 teams, Kochi Tuskers Kerala + Pune Warriors join)
- **Total**: 269 players, 10 teams
- **Withdrawn**: 5 (Broad, Mascarenhas, McKay, Mathews, Collingwood — all injury replacements)
- **Types**: sold=127, signed=120, retained=12, replacement=10
- **Backup**: `espn_squads_backup_2008_2009_2010_2011.csv`
- **Wikipedia page**: https://en.wikipedia.org/wiki/List_of_2011_Indian_Premier_League_personnel_changes
- **Pre-auction retentions (12 players)**:
  - CSK: Dhoni $1.8M, Raina $1.3M, Vijay $900K, Morkel $500K
  - MI: Tendulkar $1.8M, Harbhajan $1.3M, Malinga $900K, Pollard $500K
  - RR: Warne $1.8M, Watson $1.3M
  - DD: Sehwag $1.8M
  - RCB: Kohli $1.8M
  - KKR, KXIP, DC, Kochi, Pune: no retentions
- **Auction**: 127 players sold (Gambhir $2.4M highest)
- **Replacements (10)**: Southee for Hilfenhaus (CSK), Gayle for Nannes (RCB), Oram for Collingwood (RR), McLaren for Broad (KXIP), Miller for Mascarenhas (KXIP), Boucher for Haddin (KKR), Ganguly for Nehra (PW), Faulkner for Mathews (PW), Fernando for McKay (MI), RW Price for Henriques (MI)
- **Signed uncapped**: 120 domestic players with tier-based prices (₹10L/₹20L/₹30L)
- **Retirements (pre-auction)**: Bond, Flintoff, Hayden, Kumble, Bracken — none in ESPN squad
- **Name note**: Cricsheet uses "M Muralitharan" vs ESPN "M Muralidaran" — different spelling, same player (espn_id=49636). Join on espn_id, not player_name.

### 2011 — Addendum (missing players from Cricsheet match data)
- 1 player found in 2011 playing XI but not in ESPN squad page: RW Price (Ray Price, replacement for MC Henriques at MI, $50K)

### Missing Players Policy (established during 2008-2011 review)
- ESPN squad pages are incomplete — they miss some mid-season replacements and signed players
- Cross-reference Cricsheet playing XI data against seed file to find gaps
- For missing players: get ESPN name from espncricinfo.com player profile (or reuse from existing seed if available)
- Always confirm with user before adding records
- Acquisition type and price derived from previous season data or user-provided research

### 2012 (Mini Auction — 9 teams, Kochi Tuskers terminated)
- **Total**: 283 players, 9 teams
- **Withdrawn**: 12 (3 Wikipedia: Bravo/Sharma/Sreesanth + 9 ESPN: replaced players)
- **Types**: retained=196, signed=38, sold=25, replacement=13, traded=11
- **Backup**: `espn_squads_backup_2008_to_2012.csv`
- **Wikipedia page**: https://en.wikipedia.org/wiki/List_of_2012_Indian_Premier_League_personnel_changes
- **Key changes from 2011**:
  - Kochi Tuskers Kerala terminated — their players entered auction pool
  - 25 auction buys (Jadeja $2M highest, Narine $700K)
  - 11 trades (Pietersen→DD, Karthik→MI, Ojha→MI, Taylor→DD, Dinda→PW, etc.)
  - 13 replacements (Clarke for Yuvraj cancer treatment, Ganguly→PW, etc.)
  - Pune Warriors did not participate in auction
  - Retirements: Warne, Symonds, Jayasuriya, Ntini — none in 2012 squad
- **Cricsheet cross-check**: All playing XI players found in seed ✓

### 2013 (Mini Auction — 9 teams, Sunrisers Hyderabad replaces Deccan Chargers)
- **Total**: 260 players, 9 teams
- **Withdrawn**: 11 (Duminy, Aaron, Clarke, Aravind, Pietersen + ESPN flags)
- **Types**: retained=171, signed=49, sold=36, traded=2
- **Backup**: `espn_squads_backup_2008_to_2013.csv`
- **Wikipedia page**: https://en.wikipedia.org/wiki/List_of_2013_Indian_Premier_League_personnel_changes
- **Auction source**: iplt20.com/auction/2013 (first year using iplt20.com for auction data)
- **Key changes from 2012**:
  - Deccan Chargers terminated → Sunrisers Hyderabad new franchise, retained ~20 DC players
  - 37 auction buys (Maxwell $1M highest)
  - 1 trade only: Nehra ↔ Taylor (DD ↔ PW)
  - Many players released from contracts before auction
  - Retirements: Laxman, Ganguly, Collingwood — none in 2013 squad
  - Pre-auction signings: uncapped domestic at ₹10L/₹20L BCCI slabs
- **Cricsheet cross-check**: 2 missing (Ponting sold at auction, Dogra signed) — added

## Status: HALTED INDEFINITELY
Auction seed file work is paused effective April 2026. 2008-2013 complete and verified. Remaining seasons (2014-2026) deferred — effort-to-value ratio too high for manual curation.

## Pending Seasons (HALTED)
- 2012-2013 (Mini Auctions)
- 2014 (Mega Auction)
- 2015-2017 (Mini Auctions, CSK/RR suspended 2016-2017)
- 2018 (Mega Auction)
- 2019-2021 (Mini Auctions)
- 2022 (Mega Auction — 2 new teams GT, LSG)
- 2023-2024 (Mini Auctions)
- 2025 (Mega Auction)
- 2026 (Mini Auction)

## Files
- `src/dbt/seeds/espn_squads.csv` — main seed file (current: 2008+2009+2010+2011)
- `src/dbt/seeds/espn_squads_backup_2008.csv` — verified 2008 only
- `src/dbt/seeds/espn_squads_backup_2008_2009.csv` — verified 2008+2009
- `src/dbt/seeds/espn_squads_backup_2008_2009_2010.csv` — verified 2008+2009+2010
- `src/dbt/seeds/espn_squads_backup_2008_2009_2010_2011.csv` — verified 2008+2009+2010+2011
- `src/dbt/seeds/espn_squads_backup_2008_to_2012.csv` — verified 2008-2012
- `src/dbt/seeds/espn_squads_backup_2008_to_2013.csv` — verified 2008-2013
- `scripts/scrape_espn_squads.py` — ESPN squad scraper (not used for seed, kept for reference)
- `src/enrichment/wikipedia_auction_scraper.py` — Wikipedia scraper (not used for seed, kept for reference)
- `src/enrichment/auction_scraper.py` — iplt20.com scraper (not used for seed, kept for reference)
