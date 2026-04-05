# Cricket Analytics — Architecture & Decisions

## Project Vision
The most insightful cricket analytics experience on the internet, for free.

Built on ball-by-ball data from Cricsheet (21 datasets: IPL, T20I, BBL, PSL, ODI, Tests, WPL, WBBL, etc.),
enriched with ESPN data (captains, player bios, shot-level spatial data, win probability), weather, and
venue coordinates. The platform goes beyond what Cricbuzz and ESPNcricinfo offer — deeper analysis,
richer visualizations, and (eventually) near-live match analytics with ML-powered insights.

Two audiences:
1. Portfolio showcase — demonstrates senior DE/SWE skills (architecture, patterns, quality, testing, scalability)
2. Cricket nerds — a product people actually open during matches for stats no other free tool provides

## Core Principles
- Zero cost — all tools and tech must be free or open-source
- Portability — clone + `make all` (or `docker compose up`) on any machine rebuilds everything
- Flexibility — the data platform supports any analytics, viz, or ML use case on top
- Professional quality — coding standards, type hints, tests, docs, CI, ADRs, the works
- Idempotent pipelines — raw data downloaded from source, never stored in git
- Format-agnostic — all code, validations, and schema design must work across cricket formats (T20, ODI, Test, The Hundred, etc.) and leagues (IPL, BBL, PSL, CPL, etc.). Never hardcode IPL-specific assumptions like "20 overs", "season is 4 digits", "dates start from 2008", or "max batter_runs = 6". The project is cricket-analytics, not IPL-analytics.

## Tech Stack
| Layer            | Tool                        | Why                                              |
|------------------|-----------------------------|--------------------------------------------------|
| Storage/Compute  | DuckDB                      | Free, local, fast columnar analytics, zero infra |
| Orchestration    | Dagster                     | Modern, asset-based, great local dev, free OSS   |
| Transformation   | dbt-core + dbt-duckdb       | Industry standard, lineage, testing, docs        |
| API              | FastAPI                     | Async, auto OpenAPI docs, lightweight            |
| Frontend (new)   | Next.js + Tailwind          | SSR, Vercel deploy, real-time capable via SSE     |
| UI (legacy)      | Streamlit                   | Kept for internal data exploration, not public    |
| Data Enrichment  | python-espncricinfo, Open-Meteo | ESPN match data via Playwright, free weather API |
| ML (planned)     | scikit-learn, XGBoost       | Win probability, batting quality models           |
| CI/CD            | GitHub Actions              | Free for public repos                            |
| Linting/Format   | ruff                        | Fast, standard — lint + format in one tool        |
| Testing          | pytest, dbt tests           | Unit + integration + data quality                |
| Containerization | Docker + docker-compose     | Environment portability (optional workflow)       |

## Data Architecture (Medallion)
```
Raw (Cricsheet JSON/CSV)
  → Bronze (staged as-is into DuckDB)
    → Silver (cleaned, typed, normalized — dbt)
      → Gold (aggregated, analytics-ready — dbt)
```

### Gold Layer Models
- `dim_players` — player profiles, linked to people.csv identifiers
- `dim_teams` — team info with historical name changes
- `dim_venues` — venues and cities
- `dim_matches` — match-level facts (date, season, toss, outcome, venue, event stage)
- `fact_deliveries` — core grain: one row per legal ball bowled
- `fact_batting_innings` — per-batter-per-match aggregates (runs, balls, SR, 4s, 6s, etc.)
- `fact_bowling_innings` — per-bowler-per-match aggregates (overs, runs, wickets, econ, etc.)
- `fact_match_summary` — team-level match aggregates

## Project Structure (Monorepo)
Single GitHub repo, multiple independently deployable apps. Monorepo chosen because:
- One person/small team owns everything — multi-repo coordination overhead is pure waste
- Shared types between API and frontend (TypeScript types generated from FastAPI OpenAPI spec)
- Atomic commits across frontend + API (change endpoint + update call in same PR)
- One CI pipeline tests everything together
- Microservices is a deployment architecture, not a repo strategy — you can deploy separately from a monorepo

```
cricket-analytics/
├── .github/workflows/          # CI/CD (lint, test, dbt test, deploy)
├── .kiro/steering/             # project context (persists across sessions)
├── apps/
│   └── web/                    # Next.js frontend (deploys to Vercel)
├── config/                     # datasets.yml — dataset & enrichment configuration
├── docs/                       # ADRs, data dictionary, architecture diagrams
├── src/
│   ├── ingestion/              # raw data loaders (download + load into DuckDB bronze)
│   ├── enrichment/             # data enrichment (ESPN scraper, weather, geocoding)
│   ├── dbt/                    # dbt project (bronze → silver → gold)
│   ├── orchestration/          # Dagster definitions (assets, jobs, schedules)
│   ├── api/                    # FastAPI serving layer (deploys to Railway/Render)
│   ├── ui/                     # Streamlit app (legacy, internal use)
│   └── ml/                     # ML models (win probability, batting quality)
├── tests/                      # pytest (unit + integration)
├── data/                       # .gitignored — local DuckDB files + downloaded raw data
├── Makefile                    # dev commands (setup, ingest, transform, test, lint, run)
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml              # single source for Python deps + tool config
├── .pre-commit-config.yaml
├── .gitignore
└── README.md
```

### Deployment Architecture
| Component      | Deploys to          | Trigger              | Cost  |
|----------------|---------------------|----------------------|-------|
| Next.js frontend | Vercel            | Git push to main     | Free  |
| FastAPI API    | Railway / Render    | Git push to main     | Free tier |
| Data pipeline  | Local / CI          | Manual / scheduled   | Free  |
| Live poller    | Laptop / VPS        | During matches only  | Free / $5/mo |
| DuckDB         | Baked into API deploy | Rebuilt by pipeline | Free  |

## Data Portability Strategy
- Raw data is NOT stored in git — downloaded from Cricsheet URLs by the ingestion pipeline
  - Dataset URLs defined in config/datasets.yml (21 datasets available)
  - People: https://cricsheet.org/register/people.csv
- Dataset selection controlled by config/datasets.yml — single source of truth
  - Named profiles: minimal (IPL), standard (IPL+T20I), t20_all, everything
  - Per-dataset enabled flag + enrichment toggles
- DuckDB file is .gitignored — rebuilt by running the pipeline
- New machine workflow: `git clone` → `make all` → full database in ~2-3 min
- Docker alternative: `docker compose up` → no Python install needed

## Data Enrichment (planned)
See `docs/data-enrichment-strategy.md` for full details.

### Key External Sources
| Source                  | Data                                      | Method                    | Cost |
|-------------------------|-------------------------------------------|---------------------------|------|
| python-espncricinfo     | Captain, keeper, player roles, match time | Playwright + __NEXT_DATA__| Free |
| Open-Meteo              | Historical weather (temp, humidity, wind)  | REST API, no key needed   | Free |
| OpenStreetMap Nominatim | Venue geocoding (lat/lng)                 | REST API, 1 req/sec       | Free |
| Manual seed CSVs        | Auction prices, venue coordinates         | Curated data files        | Free |

### Enrichment Phases
1. Venue coordinates (seed CSV) + weather pipeline (Open-Meteo)
2. ESPN enrichment: captain, keeper, player roles, match time, day/night
3. Elo rating system + auction prices + player DOB
4. Derived analytics: pitch profiles, advanced ball-by-ball metrics

### Not Available (free)
- Hawk-Eye ball tracking (trajectory, spin, swing) — proprietary, BCCI/Star Sports owned
- Pitch reports — no structured source; derive from match data instead
- Live streaming ball-by-ball — future phase, needs running service during matches

## Use Cases (flexible, not exhaustive)

### Historical Analytics (available now via gold layer)
- Player stat pages (career stats, per-season breakdown, innings list)
- Team analytics (head-to-head, home/away, toss impact)
- Trend analysis (boundaries/innings over years, scoring rate evolution)
- Comparative analysis ("Is AB de Villiers really that good?")
- Weather impact analysis (dew factor, humidity effect on scoring)
- Captain/keeper performance analysis
- Auction value-for-money analysis (runs per crore)

### Advanced Analytics (planned — uses ESPN ball-level data)
- Bowling heat maps (pitch_line × pitch_length per bowler)
- Wagon wheel visualizations (wagon_x, wagon_y, wagon_zone)
- Batting quality index (rolling shot_control distribution — middling vs edging)
- Phase-wise breakdown (powerplay/middle/death scoring vs venue average)
- Matchup matrices (batter vs bowler type, with historical depth)
- Pressure index (composite of required rate × wickets lost × dot ball frequency)

### Live Match Analytics (planned — Phase 2)
- Near-live scoring (1-2 min lag via ESPN commentary API interception)
- Live win probability (own ML model, updated ball-by-ball)
- Live bowling heat map building in real-time
- Live wagon wheel building ball-by-ball
- Historical context overlays ("Kohli averages 12 at this venue in death overs vs left-arm pace")
- Phase comparison ("Team X scored 45/1 in powerplay, venue average is 52/2")

### ML Models (planned — Phase 3)
- Win probability model (XGBoost on historical features: runs needed, balls remaining, wickets, venue, phase)
- Custom Elo ratings (team + player, historical time series)
- Player performance forecasting

### Not Available (free data)
- Hawk-Eye ball tracking (trajectory, spin, swing) — proprietary, BCCI/Star Sports owned
- Pitch reports — no structured source; derive from match data instead
- Sub-30-second live latency — free data sources are 1-3 min behind broadcast

## Workflow Commands
```bash
make setup          # install deps, create virtualenv
make ingest         # ingest datasets (default profile from config/datasets.yml)
make ingest PROFILE=minimal   # IPL only
make ingest PROFILE=t20_all   # all T20 leagues
make transform      # dbt run (bronze → silver → gold)
make test           # pytest + dbt test
make lint           # ruff check + ruff format check
make enrich         # ESPN enrichment (optional: make enrich SEASON=2024)
make all            # setup + ingest + transform
make api            # start FastAPI server
make ui             # start Streamlit app
```

## Public GitHub Repo
- Repo: https://github.com/shyamdr/cricket-analytics
- Git config (local): user=shyamdr, email=shyamdrangapure@gmail.com
- CI: GitHub Actions (free for public repos)
- Repo is public — serves as portfolio showcase + open-source project

## Product Roadmap

### Phase 1: Public Website with Historical Data (current focus)
- Next.js frontend in `apps/web/` with Tailwind CSS
- Pages: home (recent matches), match detail (scorecard + stats), player profile, team page
- Served by existing FastAPI API (may need new/adjusted endpoints for frontend needs)
- Deploy: Vercel (frontend) + Railway/Render (API with baked-in DuckDB)
- Goal: get a URL live on the internet that anyone can visit

### Phase 2: Live Match Data
- ESPN Playwright poller — intercept `hs-consumer-api` commentary responses during live matches
  (same pattern as existing ball_scraper.py, but keeping the page open instead of scrolling history)
- SSE (Server-Sent Events) endpoint on FastAPI to push new balls to connected frontends
- Live scorecard page that updates without refresh
- Runs on laptop during matches initially, cheap VPS ($5/mo) later
- Latency: 1-2 minutes behind broadcast (ESPN's own lag)

### Phase 3: ML Models + Advanced Analytics
- Win probability model (XGBoost, trained on 278K+ historical deliveries)
- Batting quality index (shot_control rolling window)
- Bowling heat maps, wagon wheels, pitch maps from ESPN spatial data
- Each model/visualization is a standalone feature shipped independently

### Phase 4: Polish + Growth
- More leagues (BBL, PSL, T20 World Cup) — data platform already supports them
- Mobile-responsive design (web-first, responsive handles mobile)
- Ads if traffic justifies it (much later, not a priority)

## Live Data Architecture (Phase 2)
```
During a live match:
  Playwright opens ESPN ball-by-ball commentary page
    → Intercepts hs-consumer-api responses (new balls arrive as page auto-refreshes)
    → Writes to bronze.live_deliveries
    → Enriches with historical context from gold layer (venue averages, matchup stats)
    → ML model runs inference (<1ms per ball)
    → FastAPI SSE endpoint pushes enriched ball data to connected frontends

Between matches:
  Normal batch pipeline runs (Cricsheet → bronze → silver → gold)
  ML model retrains on new historical data
```

### Live Data Source Decision
ESPN Cricinfo is the primary live data source because:
- Already have working Playwright infrastructure (ball_scraper.py, match_scraper.py)
- ESPN's `hs-consumer-api` serves live commentary during matches — same API as historical
- No API key needed, no rate limit (one persistent page connection)
- ~200MB RAM for headless WebKit — fine for laptop or small VPS
- Cricbuzz mobile API as fallback (undocumented but free, less reliable)
- CricAPI paid tier ($15/mo) as backup if ESPN scraping breaks

### Data Licensing Notes
- Cricsheet data: CC BY 4.0 — free for any use with attribution
- ESPN scraped data: NOT licensed for redistribution or commercial use
- Own derived analytics (ML models, computed metrics): fully owned, can monetize
- If revenue ever becomes a goal: use only Cricsheet + own models, or get commercial data license
