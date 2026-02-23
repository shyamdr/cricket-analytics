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

## Verified Data (gold layer)
- dim_matches: 1,169 rows
- dim_players: 927 rows
- dim_teams: 19 rows
- dim_venues: 63 rows
- fact_deliveries: 278,034 rows
- fact_batting_innings: 17,638 rows
- fact_bowling_innings: 13,846 rows
- fact_match_summary: 2,333 rows

## Pending
- [ ] Dagster orchestration (wire ingestion + dbt as assets)
- [ ] FastAPI endpoints (query gold layer)
- [ ] Streamlit UI (player pages, team analytics, trend viz)
- [ ] pytest unit/integration tests
- [ ] ML module (future)
- [ ] Delete old data/ folder from parent Projects directory .git issue

## Technical Notes
- Python 3.13.2 on macOS (company laptop, Homebrew Python)
- Must use .venv (system pip blocked by PEP 668)
- DuckDB schemas: bronze.*, main_silver.*, main_gold.* (dbt prefixes with "main_")
- dbt profiles.yml uses relative path ../../data/cricket.duckdb
- Commit convention: conventional commits (feat:, fix:, docs:, refactor:, etc.) with detailed descriptions

## Git Standards
- Clear commit titles with conventional commit prefixes
- Detailed multi-line descriptions explaining what and why
