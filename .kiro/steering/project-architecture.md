# Cricket Analytics — Architecture & Decisions

## Project Vision
A portfolio-grade, end-to-end cricket analytics platform built on IPL data from Cricsheet.
Demonstrates senior DE/Software engineering skills: architecture, design patterns, code quality,
testing, scalability, documentation. Everything free/open-source.

## Core Principles
- Zero cost — all tools and tech must be free or open-source
- Portability — clone + `make all` (or `docker compose up`) on any machine rebuilds everything
- Flexibility — the data platform supports any analytics, viz, or ML use case on top
- Professional quality — coding standards, type hints, tests, docs, CI, ADRs, the works
- Idempotent pipelines — raw data downloaded from source, never stored in git

## Tech Stack
| Layer            | Tool                        | Why                                              |
|------------------|-----------------------------|--------------------------------------------------|
| Storage/Compute  | DuckDB                      | Free, local, fast columnar analytics, zero infra |
| Orchestration    | Dagster                     | Modern, asset-based, great local dev, free OSS   |
| Transformation   | dbt-core + dbt-duckdb       | Industry standard, lineage, testing, docs        |
| API              | FastAPI                     | Async, auto OpenAPI docs, lightweight            |
| UI               | Streamlit                   | Free, flexible, good for interactive exploration  |
| Data Enrichment  | python-espncricinfo, Open-Meteo | ESPN match data via Playwright, free weather API |
| ML (future)      | scikit-learn, XGBoost, MLflow | All free, MLflow for experiment tracking        |
| CI/CD            | GitHub Actions              | Free for public repos                            |
| Linting/Format   | ruff, black                 | Fast, standard                                   |
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

## Project Structure
```
cricket-analytics/
├── .github/workflows/          # CI/CD (lint, test, dbt test)
├── .kiro/steering/             # project context (persists across sessions)
├── docs/                       # ADRs, data dictionary, architecture diagrams
├── src/
│   ├── ingestion/              # raw data loaders (download + load into DuckDB bronze)
│   ├── enrichment/             # data enrichment (ESPN scraper, weather, geocoding)
│   ├── dbt/                    # dbt project (bronze → silver → gold)
│   ├── orchestration/          # Dagster definitions (assets, jobs, schedules)
│   ├── api/                    # FastAPI serving layer
│   ├── ui/                     # Streamlit app
│   └── ml/                     # future ML models
├── tests/                      # pytest (unit + integration)
├── data/                       # .gitignored — local DuckDB files + downloaded raw data
├── Makefile                    # dev commands (setup, ingest, transform, test, lint, run)
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml              # single source for deps + tool config
├── .pre-commit-config.yaml
├── .gitignore
└── README.md
```

## Data Portability Strategy
- Raw data is NOT stored in git — downloaded from Cricsheet URLs by the ingestion pipeline
  - Matches: https://cricsheet.org/downloads/ipl_json.zip
  - People: https://cricsheet.org/register/people.csv
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
- Player stat pages (career stats, per-season breakdown, innings list)
- Team analytics (head-to-head, home/away, toss impact)
- Trend analysis (boundaries/innings over years, scoring rate evolution)
- Comparative analysis ("Is AB de Villiers really that good?")
- Weather impact analysis (dew factor, humidity effect on scoring)
- Captain/keeper performance analysis
- Auction value-for-money analysis (runs per crore)
- Custom Elo ratings (team + player, historical time series)
- Future: ML predictions (match outcome simulation, player performance forecasting)
- Future: NL query interface
- Future: live match data pipeline

## Workflow Commands
```bash
make setup          # install deps, create virtualenv
make ingest         # download from cricsheet + load into DuckDB bronze
make transform      # dbt run (bronze → silver → gold)
make test           # pytest + dbt test
make lint           # ruff + black check
make all            # setup + ingest + transform
make api            # start FastAPI server
make ui             # start Streamlit app
```

## Public GitHub Repo
- Repo: https://github.com/shyamdr/cricket-analytics
- Git config (local): user=shyamdr, email=shyamdrangapure@gmail.com
- CI: GitHub Actions (free for public repos)
