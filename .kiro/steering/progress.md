# Cricket Analytics — Progress Tracker

## Completed
- [x] Git repo setup (local + GitHub remote via HTTPS)
- [x] Local git config: user=shyamdr, email=shyamdrangapure@gmail.com
- [x] Project scaffolding: full directory structure, pyproject.toml, Makefile, Dockerfile, docker-compose, CI, pre-commit
- [x] Ingestion pipeline: downloads from Cricsheet, parses JSON/CSV, loads into DuckDB bronze via PyArrow
- [x] dbt project: 3 silver models (stg_matches, stg_deliveries, stg_people), 8 gold models (4 dims + 4 facts)
- [x] 20 dbt data quality tests — all passing
- [x] End-to-end verified: 1169 matches, 278K deliveries, 927 players, 19 teams, 63 venues
- [x] ADR-001: DuckDB as storage engine
- [x] README with architecture, quick start, commands
- [x] Steering files for cross-session context
- [x] Pushed to GitHub: https://github.com/shyamdr/cricket-analytics
- [x] Dagster orchestration (wire ingestion + dbt as assets)
- [x] FastAPI endpoints (5 routers: players, teams, matches, batting, bowling)
- [x] Streamlit UI (home, player stats, team analytics, match explorer, trends)
- [x] Fix: season normalization bug — '2020/21' was merging with '2021' (120 matches → correctly split into 60+60)

## Verified Data (gold layer, post-season-fix)
- dim_matches: 1,169 rows (18 seasons: 2008–2025, including 2020 COVID UAE bubble)
- dim_players: 927 rows
- dim_teams: 19 rows
- dim_venues: 63 rows
- fact_deliveries: 278,034 rows
- fact_batting_innings: 17,638 rows
- fact_bowling_innings: 13,846 rows
- fact_match_summary: 2,333 rows

## In Progress
- [ ] Data enrichment strategy — brainstormed and documented (see docs/data-enrichment-strategy.md)
- [ ] Streamlit UI improvements — functional but needs polish

## Recently Completed
- [x] pytest test suite: 79 tests (27 unit, 38 integration, 14 smoke) — all passing
  - Unit: ingestion JSON parsing (match info + deliveries), config validation
  - Integration: gold layer data quality (row counts, constraints, referential integrity, season regression), all API endpoints
  - Smoke: DB connectivity, schema existence, API startup, imports
  - Regression test for 2020/2021 season merge bug

## Pending — Next Up
- [ ] Data enrichment Phase 1: venue coordinates + weather (Open-Meteo)
- [ ] Data enrichment Phase 2: ESPN enrichment (captain, keeper, player roles, match time)
- [ ] Data enrichment Phase 3: Elo ratings + auction prices + player DOB
- [ ] Data enrichment Phase 4: derived analytics (pitch profiles, advanced metrics)

## Pending — Future
- [ ] ML module (match outcome prediction, player performance forecasting)
- [ ] Live data pipeline (CricAPI/Cricbuzz polling during matches)
- [ ] Delete old data/ folder from parent Projects directory .git issue

## Technical Notes
- Python 3.13.2 on macOS (company laptop, Homebrew Python)
- Must use .venv (system pip blocked by PEP 668)
- DuckDB schemas: bronze.*, main_silver.*, main_gold.* (dbt prefixes with "main_")
- dbt profiles.yml uses relative path ../../data/cricket.duckdb
- Commit convention: conventional commits (feat:, fix:, docs:, refactor:, etc.) with detailed descriptions
- Season normalization: '2007/08'→'2008', '2009/10'→'2010', '2020/21'→'2020' (special case — COVID)
- Black version pinned to >=25.1.0,<27 to match CI (currently 26.1.0)

## Git Standards
- Clear commit titles with conventional commit prefixes
- Detailed multi-line descriptions explaining what and why
- Do NOT mention .kiro, steering files, or Kiro in commit messages
