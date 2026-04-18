# Cricket Analytics — Progress Tracker

## Branding
- Current name: **InsideEdge** — "The detail that changes everything."
- Alternative considered: **SixthStump** — "Beyond what you see on the field." (revisit if rebranding)
- Both are strong. InsideEdge = polished, analytical. SixthStump = bold, memorable, distinctive.

## Current State Snapshot (April 2026)
Everything below is actually built, tested, and running. Use this as ground truth for what exists.

### Frontend (Next.js — deployed)
- Stack: Next.js 16, React 19, TypeScript 5, Tailwind CSS 4, shadcn/ui, Base UI, Lucide icons
- Pages: home, about, matches list + detail, players list + profile, teams list + detail, venues list, 404
- Deploy: Vercel at https://insideedge.vercel.app (auto from main)
- Env var: `NEXT_PUBLIC_API_URL` points to Render API
- Note: `apps/web/` has nested `.git` folder

### Backend (FastAPI — deployed on Render)
- 9 routers (all under `/api/v1`):
  - `players.py` — list/get player, batting/bowling stats
  - `teams.py` — list/get team, team matches
  - `matches.py` — list/get match, seasons, venues, recent matches with scores, by-tournament, summary, batting, bowling
  - `batting.py` — top run scorers, career batting stats, season breakdown
  - `bowling.py` — top wicket takers, career bowling stats, season breakdown
  - `standings.py` — points table by season
  - `images.py` — serves cached player/team/ground/venue images from `data/images/`
  - `news.py` — proxies ESPN Cricinfo RSS feed
- DI: `get_query_fn()` via `Depends()` in `src/api/database.py`; tests override via `app.dependency_overrides`
- Table name constants live in `src/tables.py` — routers import from there, not from `settings.gold_schema` f-strings
- Deploy: Render at https://insideedge-api.onrender.com (spins down after 15 min idle; first request ~30s)

### Data Platform
- DuckDB: `data/cricket.duckdb` (~427 MB) — IPL + T20I bronze data loaded
- Schemas: `bronze.*`, `main_silver.*`, `main_gold.*`
- Bronze tables: matches (39 cols with audit: _loaded_at, _source_file, _run_id), deliveries (33 cols with audit), people, espn_matches, espn_players, espn_innings, espn_ball_data, espn_teams, espn_grounds, weather, venue_coordinates
- dbt: 21 models total
  - Silver (12): stg_matches, stg_deliveries, stg_people, stg_espn_matches, stg_espn_players, stg_espn_innings, stg_espn_ball_data, stg_espn_teams, stg_espn_grounds, stg_weather_hourly, stg_weather_daily, stg_venue_coordinates
  - Gold (9): dim_matches, dim_players, dim_teams, dim_venues, fact_deliveries (incremental), fact_batting_innings, fact_bowling_innings, fact_match_summary, fact_weather
- dbt tests: 59 (53 generic in schema.yml + 6 singular SQL in tests/)
- dbt seeds (5): espn_squads.csv, espn_squads_backup_2008_to_2013.csv, team_brand_colors.csv, team_name_mappings.csv, venue_name_mappings.csv
- dbt macros: source_exists.sql (fallback for optional ESPN sources), weather_description.sql (extracted CASE macro)

### Dagster Orchestration
- Assets (5 enrichment + ingestion + dbt):
  - `bronze_matches`, `bronze_people` (ingestion)
  - dbt assets (21 models, wired via source meta asset_key mapping)
  - `espn_match_enrichment`, `espn_ball_enrichment`, `geocode_venue_coordinates`, `espn_image_enrichment`, `weather_enrichment`
- Jobs (3): `full_pipeline`, `daily_refresh`, `enrichment_backfill`
- Schedule (1): `daily_refresh_schedule` at 06:00 UTC
- FreshnessPolicy on gold assets (1-week warn, 30-day fail)

### Test Suite (117 pytest tests + 59 dbt tests)
- Unit (61): test_config.py (6), test_database.py (8), test_ingestion.py (26), test_enrichment.py (21)
- Integration (44): test_api.py (25), test_data_quality.py (19)
- Smoke (12): test_smoke.py
- Markers registered in pyproject.toml: unit, integration, smoke

### Deployment Files
- `Dockerfile` — generic image for CI/local pipeline
- `Dockerfile.api` — Render-specific; runs ingest + dbt seed + dbt run during build, then uvicorn
- `render.yaml` — Render Blueprint (Python 3.11, `--profile minimal`)
- `docker-compose.yml` — local dev (pipeline + api + ui services)
- `.github/workflows/ci.yml` — lint (3.11) + unit-tests (3.11 + 3.13) + integration-tests (3.11 + 3.13)

### Enrichment Modules (src/enrichment/)
- `match_scraper.py`, `run_match_scraper.py` — ESPN match metadata (captain, keeper, roles, timing)
- `ball_scraper.py`, `run_ball_scraper.py` — ESPN ball-by-ball commentary (wagon wheel, shot type)
- `series_resolver.py` — maps Cricsheet match_id → ESPN series_id
- `weather_fetcher.py` — Open-Meteo historical weather
- `geocoder.py` — OpenStreetMap Nominatim venue lat/lng
- `image_downloader.py` — ESPN player/team/ground images (sync httpx, not async)
- `bronze_loader.py` — shared PyArrow→DuckDB loader
- `queries.py` — shared query functions (get_matches_for_season, get_all_matches, get_matches_by_ids)

### Images (served by API, cached on disk)
- `data/images/grounds/` — venue/ground images
- `data/images/players/`, `data/images/teams/`, `data/images/logo/`, `data/images/venues/`
- `/api/v1/images/{type}/{id}` serves them

### Docs (docs/)
- ADRs: 001-duckdb-as-storage, 002-image-serving-strategy, 003-monorepo-with-nested-frontend-git, 004-natural-keys-over-surrogate-keys, 005-format-agnostic-schema-design
- `architecture.md` — Mermaid diagrams (system, medallion, Dagster, request path, deployment topology)
- Other: data-enrichment-strategy, espn-ball-data-scraping, espn-json-field-reference, image-strategy, open-meteo-weather-api-reference, auction-data-research, auction-seed-process, ui-design-notes
- Root: `CONTRIBUTING.md` (setup, workflow, code style, where-to-add-things, git conventions, CI)

### Scripts (scripts/)
- `player_photo_viewer.html` — manual HTML viewer for ESPN player image IDs
- `scrape_espn_squads.py` — auction pipeline (halted at 2013)
- Note: `scripts/audit_espn_ball_response.py` has been referenced as an active editor file but isn't currently on disk — likely an unsaved buffer or work-in-progress audit tool

### Workspace Root
- `cricsheet-website-data-format.txt` — Cricsheet field reference, gitignored, not tracked
- `.env` — gitignored, not tracked

### Steering Files (`.kiro/steering/`)
- `project-architecture.md` — vision, tech stack, medallion layers, project structure, roadmap
- `progress.md` — this file; current state snapshot + completed/pending/decisions log
- `cricsheet-data-reference.md` — Cricsheet JSON/CSV data format cheat sheet (static reference)
- `api-endpoints-reference.md` — all 9 API routers with endpoint tables and conventions
- `dbt-models-reference.md` — all 21 dbt models with grains, columns, and rationale

## Completed
- [x] Git repo setup (local + GitHub remote via HTTPS)
- [x] Local git config: user=shyamdr, email=shyamdrangapure@gmail.com
- [x] Project scaffolding: full directory structure, pyproject.toml, Makefile, Dockerfile, docker-compose, CI, pre-commit
- [x] Ingestion pipeline: downloads from Cricsheet, parses JSON/CSV, loads into DuckDB bronze via PyArrow
- [x] dbt project: 12 silver models + 9 gold models (expanded from 3+8)
- [x] 59 dbt tests (53 generic + 6 singular) — all passing
- [x] End-to-end verified: 1169 IPL matches, 278K deliveries, 927 players, 19 teams, 63 venues
- [x] ADR-001: DuckDB as storage engine
- [x] ADR-002: Image serving strategy (API serves cached images from data/images/)
- [x] ADR-003: Monorepo with nested frontend git repo
- [x] ADR-004: Natural keys over surrogate keys
- [x] ADR-005: Format-agnostic schema design
- [x] CONTRIBUTING.md (setup, code style, where to add things, git/CI conventions)
- [x] Architecture diagrams (docs/architecture.md — Mermaid for system, medallion, Dagster, request path, deployment)
- [x] README with architecture, quick start, commands
- [x] Steering files for cross-session context
- [x] Pushed to GitHub: https://github.com/shyamdr/cricket-analytics
- [x] Dagster orchestration — bronze + dbt + 5 enrichment assets, 3 jobs, 1 schedule
- [x] FastAPI endpoints — 9 routers: players, teams, matches, batting, bowling, standings, images, news
- [x] Streamlit UI (legacy) — home, player stats, team analytics, match explorer, trends
- [x] Next.js frontend — full Phase 1 deployed to Vercel (https://insideedge.vercel.app)
- [x] FastAPI deployed to Render (https://insideedge-api.onrender.com) with baked-in DuckDB
- [x] Fix: season normalization bug — '2020/21' was merging with '2021' (120 matches → correctly split into 60+60)
- [x] Format-agnostic season derivation — replaced hardcoded CASE/split_part logic with `EXTRACT(YEAR FROM match_date)`. Eliminates IPL-specific '2020/21' special case. Works correctly for BBL (split-year seasons span Dec-Feb) and all other leagues. Original Cricsheet season preserved as `season_raw` in silver layer.
- [x] ESPN match enrichment pipeline (captain, keeper, player roles, toss time, day/night)
- [x] ESPN ball-by-ball enrichment pipeline (wagon wheel, shot type, shot control)
- [x] Weather enrichment pipeline (Open-Meteo, hourly + daily) — fact_weather gold model
- [x] Venue geocoding pipeline (OpenStreetMap Nominatim)
- [x] ESPN image scraping pipeline — player, team, ground images cached on disk, served via `/api/v1/images/`
- [x] News feed endpoint — proxies ESPN Cricinfo RSS
- [x] Standings endpoint — points table by season
- [x] Table name constants centralized in `src/tables.py` — routers and UI import from there

## Verified Data (gold layer, IPL only — pre-T20I gold aggregation)
- dim_matches: 1,169 rows (18 seasons: 2008–2025, including 2020 COVID UAE bubble)
- dim_players: 927 rows
- dim_teams: 19 rows
- dim_venues: 63 rows
- fact_deliveries: 278,034 rows
- fact_batting_innings: 17,638 rows
- fact_bowling_innings: 13,846 rows
- fact_match_summary: 2,333 rows
- Note: T20I bronze data has been ingested, but the default render.yaml + CI pipelines currently build with `--profile minimal` (IPL only). Gold row counts above are IPL-only.
- DuckDB file size: ~427 MB (after IPL + T20I ingestion and enrichment)

## In Progress
- [x] Phase 1: Next.js Frontend — COMPLETE and deployed to https://insideedge.vercel.app
  - Built in `apps/web/` with Next.js 16, React 19, TypeScript, Tailwind CSS 4, shadcn/ui, Base UI, Lucide icons
  - Pages built: home (`/`), about (`/about`), matches list (`/matches`), match detail (`/matches/[matchId]`), players list (`/players`), player profile (`/players/[playerName]`), teams list (`/teams`), team detail (`/teams/[teamName]`), venues list (`/venues`), 404
  - Home components: MatchSpotlight, MatchTicker, LatestResults, TopPerformers, PointsTable, NewsFeed, SeasonSummary, ExploreCards
  - Shared components: Navbar, ThemeProvider, ThemeToggle (dark/light mode), Loading
  - `src/lib/`: `api.ts` (API client), `landing-utils.ts`, `team-logos.ts`, `types.ts`, `utils.ts`
  - Configured via `NEXT_PUBLIC_API_URL` env var (points to Render API)
  - Deploy: Vercel auto-deploys from main
  - The `apps/web/` directory has its own `.git` folder (nested git repo) — keep in mind when doing git operations
- [~] Auction data pipeline — HALTED at 2013. Manual curation too tedious. See "Pending — Next Up" for details.
- [x] Streamlit UI — LEGACY, no further investment. 4 pages still present (Player Stats, Team Analytics, Match Explorer, Trends) for internal exploration.

## Recently Completed
- [x] Config-driven dataset management — created config/datasets.yml as single source of truth for all dataset and enrichment configuration. 21 Cricsheet datasets (IPL, T20I, BBL, PSL, CPL, SA20, LPL, ILT20, BPL, NPL, MLC, MSL, SSM, NTB, ODI, Test, T20I Women, ODI Women, Test Women, WBBL, WPL) with per-dataset enrichment toggles (espn_match, espn_ball, weather, geocoding). Named profiles (minimal, standard, t20_all, everything). CLI supports --profile, --enabled, --dataset, --list. All consumers (CLI, Makefile, Dagster, Docker) read from YAML. Added pyyaml to core dependencies. URLs verified via HTTP HEAD against cricsheet.org.
- [x] Multi-dataset ingestion: T20 Internationals — default ingestion now pulls both IPL + T20I. Updated Makefile, CLI defaults, Dagster IngestionConfig, docker-compose, README, and steering files. No schema changes needed — format-agnostic code handles T20I out of the box. Requires `make ingest --full-refresh` to rebuild bronze with both datasets.
- [x] Explicit bronze DDL + full Cricsheet field expansion — 36-column matches table, 30-column deliveries table with CREATE TABLE IF NOT EXISTS. Parser now captures: meta.created, meta.revision, team_type, match_type_number, officials (JSON), supersubs (JSON), missing (JSON), event_group, toss_uncontested, non_boundary, review (6 fields: by/umpire/batter/decision/type/umpires_call), replacements (JSON). 9 new unit tests (107 total). Requires full_refresh rebuild of DuckDB.
- [x] pytest test suite: 107 tests (36 unit, 38 integration, 14 smoke) — all passing, pushed to GitHub
  - Unit: ingestion JSON parsing (match info + deliveries), config validation
  - Integration: gold layer data quality (row counts, constraints, referential integrity, season regression), all API endpoints
  - Smoke: DB connectivity, schema existence, API startup, imports
  - Regression test for 2020/2021 season merge bug
- [x] CI updated: split into lint → unit-tests (no DB) → integration-tests (builds DB, runs integration + smoke + dbt tests)
  - Pytest markers registered in pyproject.toml (unit, integration, smoke)
- [x] Centralized DuckDB connection management — all duckdb.connect() calls now in src/database.py
  - get_read_conn() for read-only, get_write_conn() for writes + schema bootstrap
  - 6 consumers updated: ingestion, enrichment (loader, run, series_resolver), API, UI, tests

## Pending — Architecture Review Backlog
Priority order from senior architecture review. Tackle one at a time.

### High Priority (structural / portfolio impact)
- [~] Add Pydantic response models to FastAPI — DEFERRED until gold schema stabilizes post-enrichment; schema will change as enrichment phases add columns, no point maintaining models through churn
- [x] Surrogate keys on dimensions + FK references in facts — WON'T DO. DuckDB is columnar and dictionary-encodes strings internally (effectively auto-surrogate keys at storage level). No FK constraint enforcement in DuckDB anyway. At 278K deliveries / 927 players, string vs integer join performance is negligible. Human-readable columns (batter='V Kohli' vs batter_id=437) are critical for an analytics platform where users explore data directly via Streamlit/SQL. Referential integrity will be enforced via dbt `relationships` tests instead (see dbt backlog items). Natural keys (match_id, player_id, player_name, team_name) are already stable and unique.
- [x] Unit tests for enrichment module — 19 tests covering ESPN __NEXT_DATA__ extraction (match metadata, captain/keeper/roles, CWK dual-role, empty teamPlayers edge case), ROLE_MAP validation, SeriesResolver cache logic (season/match lookups, cache size), and series info JSON path extraction (including missing season/series edge cases). All pure unit tests with mocked DB — no browser or network needed.
- [x] Consolidate two bronze_loader.py files — extracted shared `append_to_bronze()` into `src/database.py`. Both `src/ingestion/bronze_loader.py` and `src/enrichment/bronze_loader.py` now delegate to this utility for idempotent PyArrow→DuckDB append with dedup.

### Medium Priority (correctness / maintainability)
- [x] Fix schema name mismatch in config — updated config defaults to `gold_schema="main_gold"`, `silver_schema="main_silver"` to match actual DuckDB schemas. Replaced all hardcoded `main_gold` across 16 files (API routers, UI pages, enrichment, tests) with `settings.gold_schema`.
- [x] Move team name mappings to dbt seed CSV — franchise rename CASE statement in dim_teams.sql replaced with LEFT JOIN against `team_name_mappings` seed CSV. New renames only require adding a CSV row, no SQL changes. Makefile and CI updated to run `dbt seed` before `dbt run`.
- [x] Add retry/backoff on HTTP calls — created `src/utils.py` with `retry()` (sync) and `async_retry()` (async) decorators implementing exponential backoff. Applied to `download_file()` in downloader.py, `_fetch_next_data()` in espn_client.py, and `_discover_series_from_match()` in series_resolver.py. Configurable max_attempts, base_delay, backoff_factor, and exception types.
- [x] Add FastAPI dependency injection — introduced `get_query_fn()` dependency and `DbQuery` Annotated type in `src/api/database.py`. All 5 routers now receive the query callable via `Depends()` instead of importing directly. Tests can override via `app.dependency_overrides[get_query_fn]` to inject a mock DB.
- [x] Handle SCD properly for dim_teams — WON'T DO. The current design already tracks temporal validity via first_match_date/last_match_date derived from actual match data, plus current_franchise_name from the seed CSV. This effectively gives SCD Type 2 semantics: "Delhi Daredevils" shows 2008–2018, "Delhi Capitals" shows 2019–2025. Adding explicit valid_from/valid_to columns would be redundant since the dates are derived from real matches. The only gap (a rename before any matches are played) doesn't apply — Cricsheet only has names that appear in actual match data.

### Lower Priority (cleanup / DevOps)
- [x] asyncio.run() inside sync wrappers is fragile — replaced with `run_async()` utility in `src/utils.py` that detects whether an event loop is already running. If no loop: uses `asyncio.run()`. If loop exists (Dagster async, Jupyter, uvicorn): offloads to a background thread. Applied to `scrape_matches()` in espn_client.py and `SeriesResolver.resolve()` in series_resolver.py.
- [x] _ensure_tables in bronze_loader infers schema from first batch — replaced with explicit `_MATCHES_DDL` (36 columns) and `_DELIVERIES_DDL` (30 columns) CREATE TABLE IF NOT EXISTS statements. Tables are created before any data is parsed, so NULL-heavy first batches no longer cause wrong types.
- [x] Docker compose builds image 3x — pipeline now builds + tags `cricket-analytics:latest`, api and ui reuse via `image:`. Also added missing `dbt seed` to pipeline command.
- [x] Pre-commit has both ruff-format and black — removed black entirely; ruff handles both linting and formatting
- [x] CI doesn't cache pip dependencies — added `cache: 'pip'` to all 3 setup-python steps; keyed on pyproject.toml hash
- [x] No `make enrich` command — added `make enrich` target (supports optional `SEASON=2024` arg)
- [x] Remove dead code download_matches() in downloader.py — removed, nothing referenced it
- [x] pyproject.toml says requires-python >=3.11 but dev is on 3.13 — added CI matrix for Python 3.11 + 3.13 on unit-tests and integration-tests jobs. Lint stays on 3.11 only (ruff output is version-independent).
- [x] Integration tests have hardcoded value expectations — replaced with shape/constraint assertions (positive values, sorted order, non-empty results)

## Pending — ETL Deep Review Backlog
Deep review of ingestion, dbt, Dagster, and DuckDB pipeline. Core DE showcase area.

### Ingestion Layer (Python → Bronze)
- [x] Add transaction boundaries (BEGIN/COMMIT) around bronze writes — both load_matches_to_bronze (matches + deliveries atomic) and load_people_to_bronze (drop + create atomic) now wrapped in BEGIN/COMMIT with ROLLBACK on failure
- [x] Batch processing for large datasets — files processed in batches of 1000 with per-batch transactions; IPL (1169 files) runs in 2 batches, scales to multi-league datasets without OOM
- [x] Define explicit DDL for bronze tables — explicit CREATE TABLE DDL for matches (36 cols) and deliveries (30 cols). Also expanded parser to capture ALL Cricsheet fields: meta (created, revision), team_type, match_type_number, officials (JSON), supersubs (JSON), missing (JSON), event_group, toss_uncontested, non_boundary, review (6 fields), replacements (JSON). 9 new unit tests, 107 total passing.
- [x] Safe people.csv loading — load into _people_staging table, validate (row count > 0, identifier column exists), then atomic swap (drop old + rename). Malformed CSV no longer destroys existing people table.
- [x] Per-file error handling in ingestion — malformed JSON files are caught, logged via structlog, and collected into a failed_files summary. Rest of the batch still loads.
- [x] Skip unchanged downloads — HTTP HEAD + Last-Modified check before downloading. If remote file hasn't changed since local zip was saved, download is skipped entirely. Falls through to download if server doesn't provide Last-Modified or local file doesn't exist.

### dbt Transformation Layer (Bronze → Silver → Gold)
- [x] Strengthen silver layer — added `_loaded_at` audit timestamp to all 3 silver models, plus `_is_valid_extras` (extras components sum check) and `_is_valid_total` (total_runs = batter_runs + extras_runs) validation flags on stg_deliveries. All format-agnostic, no IPL-specific assumptions.
- [x] Add referential integrity test: stg_deliveries.match_id → stg_matches.match_id — dbt relationships test, 21 total dbt tests passing
- [x] Gold facts should read from silver, not other gold — fact_batting_innings, fact_bowling_innings, and fact_match_summary now read from stg_deliveries + stg_matches (silver) instead of fact_deliveries (gold). Each has its own explicit `WHERE is_super_over = false` filter. Eliminates fragile cascade dependency and silent filter inheritance.
- [x] dim_matches adds no value over stg_matches — added 3 derived columns to justify the gold layer: `match_result_type` (enum: normal_win/dls_win/tie_super_over/no_result), `winning_margin` (human-readable text like '5 runs', '3 wickets', 'X won via super over'), `is_home_team` (NULL placeholder for future venue-team enrichment). Raw outcome columns kept alongside for filtering flexibility.
- [x] Add incremental materialization to fact_deliveries — uses `materialized='incremental'` with composite unique_key and `match_id NOT IN` filter. Full refresh builds complete table; subsequent runs only append deliveries from new matches. Verified: full refresh 0.32s, incremental no-op 0.07s, row count stable at 278,034.
- [x] Add dbt tests on fact tables — 25 new tests: unique composite key on each fact table (match_id+innings+batter/bowler/batting_team), not_null on all grain and measure columns, plus 3 singular SQL tests for range checks (no negative stats, wickets ≤ 10). Total dbt tests: 46.
- [x] Add business rule dbt tests (singular) — 3 new singular SQL tests: every completed match has ≥1 delivery, every completed match has exactly 2 batting teams in summary, total_runs = batter_runs + extras_runs on every delivery. All format-agnostic. Total dbt tests: 49.
- [x] Add column-level documentation in schema.yml — comprehensive descriptions on every column across all 11 models (3 silver, 8 gold). Descriptions sourced from Cricsheet data format spec. `dbt docs generate` now produces a complete data dictionary.
- [x] Consider silver models as views instead of tables — WON'T DO at current scale. Benchmarked: stg_deliveries transform takes ~300ms at 278K rows. At full Cricsheet scale (~5M deliveries across all leagues/formats), it would take ~5.3s per reference × 4 gold models = ~21s overhead per dbt run. Tables keep gold builds fast with negligible storage cost (DuckDB compresses well). May revisit if storage becomes a concern.

### Dagster Orchestration
Items below are from the ETL deep review. See "Dagster Orchestration — Full Redesign" section for the comprehensive job/asset graph analysis.
- [x] Remove dead CricketAnalyticsConfig resource — class was defined in resources.py but never registered or imported anywhere; assets use src.config.settings directly. Removed the class, kept the module file.
- [ ] Add Dagster sensors — deferred until deployment strategy is decided. Requires Dagster running continuously (server/VM). See Step 5 in Dagster Orchestration Full Redesign section.

### Cross-Cutting ETL
- [x] Add audit columns to bronze tables — `_loaded_at` (TIMESTAMP), `_source_file` (VARCHAR), `_run_id` (VARCHAR) added to both matches (39 cols) and deliveries (33 cols) DDLs. Generated once per `load_matches_to_bronze` call (UUID run_id + UTC timestamp). Parse functions accept audit kwargs with defaults for backward compatibility. Requires full_refresh rebuild of DuckDB.
- [x] Add observability beyond structlog — FreshnessPolicy on gold assets (1-week warn, 30-day fail), MaterializeResult metadata on Python assets (row counts visible in Dagster UI), dagster-dbt captures dbt output metrics automatically.

## Pending — Dagster Orchestration Full Redesign
Comprehensive review of the Dagster asset graph, job definitions, and scheduling.
This is the most critical orchestration work — the current setup has broken dependencies and incorrect job selections.

### Root Cause: Disconnected Asset Graph
The fundamental problem is that Dagster doesn't see the full dependency chain.
Your dbt assets read from `source('bronze', 'matches')` but Dagster doesn't know that
the DuckDB table `bronze.matches` is produced by the `bronze_matches` Python asset.
Similarly, `espn_enrichment` depends on `bronze_matches` but actually queries `main_gold.dim_matches`.

Current (broken) graph:
```
bronze_matches ──┐
                 ├── (NO EDGE to dbt — Dagster doesn't see the connection)
bronze_people ───┘

dbt_analytics_assets (11 models, floating — no upstream dependency in Dagster)

espn_enrichment ─── deps=["bronze_matches"] (but queries main_gold.dim_matches — wrong dep)
```

Target (correct) graph:
```
bronze_matches ──→ stg_matches ──→ dim_matches ──→ espn_enrichment
                               ──→ fact_deliveries ──→ fact_batting_innings
                                                   ──→ fact_bowling_innings
                                                   ──→ fact_match_summary
bronze_people ───→ stg_people ──→ dim_players
                               ──→ dim_teams
                               ──→ dim_venues
```

### Step 1: Wire dbt source assets to Python bronze assets
- [x] Map dbt sources to Dagster asset keys — added `meta: { dagster: { asset_key: ["bronze_matches"] } }` to matches and deliveries sources, `asset_key: ["bronze_people"]` to people source in sources.yml. Enabled `DagsterDbtTranslatorSettings(enable_duplicate_source_asset_keys=True)` in dbt.py since matches+deliveries share the same bronze_matches asset. DAG is now fully connected: bronze → silver → gold → enrichment.

### Step 2: Fix espn_enrichment dependency
- [x] Changed espn_enrichment deps from `["bronze_matches"]` to `[AssetKey(["gold", "dim_matches"])]` — enrichment now correctly depends on the dbt gold layer, not bronze. Dagster will refuse to run enrichment without dim_matches being materialized first.

### Step 3+4: Simplify jobs (3 jobs + 1 schedule)
- [x] Rewrote jobs.py — simplified from 6 jobs + 1 schedule to 3 jobs + 1 schedule:
  - `full_pipeline` — `AssetSelection.all()` (kept as-is)
  - `daily_refresh` — `AssetSelection.all()` with `RunConfig(ops={"bronze_matches": IngestionConfig(datasets=["recent_7"], full_refresh=False)})`. Fixed legacy `"ops"` dict config to use proper `RunConfig`.
  - `enrichment_backfill` — `AssetSelection.groups("enrichment")` for manual historical scraping
  - `daily_refresh` schedule at 06:00 UTC pointing to daily_refresh_job
- [x] Removed: `ingestion_job`, `transformation_job`, `enrichment_job`, `delta_pipeline_job`, `daily_delta_schedule`
- [x] Updated `__init__.py` to register new jobs/schedule

### Step 5: Dagster best practices to add
- [x] FreshnessPolicy on gold assets — 1-week warn, 30-day fail window applied to all 8 gold layer assets via `map_asset_specs` in `__init__.py`. Dagster UI shows freshness health status.
- [x] AssetObservation for row counts — already implemented. Python assets (ingestion, enrichment) emit `MaterializeResult(metadata={...})` with row counts. dagster-dbt automatically captures dbt output metrics. All visible in Dagster UI asset detail pages.
- [x] AutoMaterializePolicy — WON'T DO. Adds implicit complexity without benefit given we already have clean explicit jobs. Makes debugging harder.
- [ ] Add Dagster sensor to replace blind daily cron — poll Cricsheet (HTTP HEAD / Last-Modified) and only trigger daily_refresh when new data is available. Requires Dagster to be running continuously (local laptop or server). Deferred until deployment strategy is decided.

## Pending — Next Up
- [ ] Fix series resolver for T20I — current resolver groups by season (one series per season), breaks for T20I which has ~588 unique (season, event_name) combos. Need to group by (season, event_name) instead. Also add event_name to match query dicts in run_match_scraper.py and run_ball_scraper.py. ON HOLD — not adding more datasets for now.
- [x] Data enrichment Phase 1: venue coordinates (Google Geocoding API) + weather (Open-Meteo) — COMPLETE.
- [~] Data enrichment Phase 3: Auction prices + Elo ratings — HALTED
  - [~] IPL auction/contract seed file — 2008-2013 complete and verified (6 seasons, 1456 player-season records). 2014-2026 halted indefinitely — manual curation effort too high relative to value. Backup: `espn_squads_backup_2008_to_2013.csv`.
  - [ ] Elo ratings — not started
- [ ] Data enrichment Phase 2: T20I ESPN enrichment (after series resolver fix) — ON HOLD
- [ ] Data enrichment Phase 4: derived analytics (pitch profiles, advanced metrics)

## Pending — Pipeline Deep Review (April 2026)
Thorough review of dbt models, Dagster assets, medallion architecture, and enrichment flows.

### DAG Restructuring — Eliminate Circular Dependencies (HIGH PRIORITY)
Current problem: enrichment reads from gold (dim_matches) to know what to enrich, then writes to bronze, which flows back up to gold. This is a circular dependency that Dagster masks but is architecturally wrong.

Target state: enrichment reads from bronze (not gold), runs in parallel with dbt silver, and gold is the single join point.

Current (messy):
```
bronze → silver → gold → enrichment → bronze → silver → gold (circular)
```

Target (clean):
```
bronze.matches ──→ dbt silver ──→ dbt gold (joins silver + enrichment bronze)
       │                              ↑
       └──→ enrichment ──→ bronze.espn_* / bronze.weather ──┘
```

Changes needed:
- [x] `espn_match_enrichment` — changed dep from `AssetKey(["gold", "dim_matches"])` to `AssetKey("bronze_matches")`. Updated `run_match_scraper.py` to query `bronze.matches` (match_id, date, season) instead of `main_gold.dim_matches`.
- [x] `espn_ball_enrichment` — changed dep from `AssetKey(["gold", "dim_matches"])` to `AssetKey("bronze_matches")` + `AssetKey("espn_match_enrichment")`.
- [ ] `weather_enrichment` — remove ESPN timezone lookup from the query. Let gold handle that join. Already correctly depends on bronze.
- [ ] `geocode_venue_coordinates` — already correct (depends on bronze_matches).
- [ ] Gold models — already correct (LEFT JOIN silver + bronze enrichment). No changes needed.
- [ ] Verify the full Dagster DAG has no cycles after restructuring.

### dbt Model Fixes
- [x] Remove `batter` from `fact_deliveries` unique_key — grain is (match_id, innings, over_num, ball_num), not batter. Including batter means Cricsheet name corrections create duplicates instead of updates.
- [x] Remove `extras_penalty` from bowling `runs_conceded` in `fact_bowling_innings` — penalty runs are NOT charged to the bowler (ball tampering, slow over rate). Current formula inflates economy rates.
- [x] Fix `stg_weather_hourly` cross join — generates 24 NULL rows for matches with empty/malformed weather JSON. Add WHERE clause to filter out all-NULL rows.
- [x] Add dbt referential integrity test: `stg_espn_matches.match_id → stg_matches.match_id` — catch silent enrichment drops from ID mismatches.
- [ ] Fix venue coordinate join order in `dim_venues` — geocoded coordinates stored under original venue name, but canonical name mapping happens in the same query. Join should happen before or independently of the canonical mapping.
- [ ] Consider extracting ESPN silver `WHERE false` fallback blocks into a shared macro — 6 models each have ~30 lines of typed NULL columns that must stay in sync with the real query.

### Dagster Asset Fixes
- [x] Remove `bronze_people` dependency on `bronze_matches` — people.csv is independent of match data. Current dep prevents refreshing people registry without re-ingesting matches.
- [x] Add `espn_match_enrichment` as dependency for `weather_enrichment` — weather query uses `bronze.espn_matches` for venue timezone. Without this dep, timezone defaults to Asia/Kolkata for all non-Indian venues.
- [ ] Consider splitting `dbt build` into `dbt run` for daily_refresh_job and `dbt build` (with tests) for full_pipeline_job — daily refresh doesn't need to run all 49 tests every time.

### Ingestion Fixes
- [x] Fix `full_refresh` flag — RESOLVED by removing full_refresh entirely. For a full rebuild, delete `data/cricket.duckdb` and re-run. Tables are created automatically on first write.

### API Fixes
- [x] Fix `by-tournament` endpoint SQL INTERVAL parameter — `INTERVAL '$1 days'` doesn't work with DuckDB parameterized queries. Compute date in Python and pass as date parameter.

## Pending — Code Quality Fixes (Defensive Coding / Robustness)
Quick wins that improve robustness.

### P0 — Fix Now
- [x] Context manager for `get_write_conn()` — added `write_conn()` context manager to `src/database.py`. Migrated all enrichment callers (series_resolver, run_ball_scraper, weather_fetcher, image_scraper, bronze_loader) from manual try/finally to `with write_conn() as conn:`. Eliminates connection leak risk.
- [x] Anti-join pattern in `append_to_bronze()` — replaced `NOT IN (SELECT DISTINCT ...)` with `LEFT JOIN ... WHERE IS NULL`. NULL-safe, better performance at scale.
- [x] Fix innings dedup in enrichment bronze_loader — added composite `_innings_key` (`espn_match_id_inning_number`) for proper per-innings dedup, matching the `_player_match_key` pattern.

### P1 — Quick Wins
- [x] Weather code CASE macro in dbt — extracted duplicated 30-line CASE statement into `macros/weather_description.sql`. `fact_weather.sql` now calls `{{ weather_description('column') }}` for both hourly and daily.
- [x] Remove dead `_get_already_fetched()` in weather_fetcher.py — defined but never called. `_get_pending_matches()` handles delta logic via LEFT JOIN.
- [x] Add `make check` target — single command: `lint + test -m unit + format check`. Developers should run same checks as CI before pushing.
- [x] Centralize table references — created `src/tables.py` with all fully-qualified table names (gold + bronze). Updated all 5 API routers and 4 Streamlit pages to import from `src/tables` instead of building f-strings with `settings.gold_schema`. Enrichment files left as-is (will change during DAG restructuring).

### P2 — API Hardening
- [ ] API response models with `extra="allow"` — compromise between "no models" (current) and "strict models" (deferred). Define Pydantic models for guaranteed fields, allow extra fields to pass through. Gives useful OpenAPI docs without breaking on schema changes.
- [x] Consolidate 3 `query()` functions — removed the slow per-call-connection `query()` from `src/database.py`. Only the API singleton (`src/api/database.query`) and Streamlit cached (`src/ui/data.query`) versions remain. Updated unit test.

### P3 — Docker / DevOps
- [ ] Docker compose doesn't pin image tag — `image: cricket-analytics:latest` is fragile. If `docker compose up api` runs without `pipeline`, gets stale `:latest`. Consider build hash or document dependency.

## Pending — System Design Improvements (Abstraction / Architecture / Team-Readiness)
Gaps between "it works" and "a team can operate and evolve it."

### Abstraction & Boundaries
- [ ] Repository/service layer (the biggest gap) — every consumer (API, UI, enrichment, tests) knows exact schema names, table names, column names, SQL dialect. Rename a column = grep 20+ files. Fix: `src/queries/` module with functions like `get_career_stats(player_name)`. API router calls it, Streamlit calls it, tests mock it. Nobody outside knows SQL. This is the Repository Pattern — minimum abstraction for evolvability.
- [ ] Domain types — everything is `dict[str, Any]`. No function signature tells you what shape of data flows through. Fix: lightweight TypedDicts for core domain objects (`BattingInnings`, `MatchSummary`, etc.). Not Pydantic for everything — just enough that `list[BattingInnings]` communicates intent vs `list[dict[str, Any]]`.
- [ ] Schema contract between ingestion and dbt — bronze DDL lives in Python (`_MATCHES_DDL`), dbt reads from `source('bronze', 'matches')`. No shared definition. Add column to Python DDL → dbt doesn't know. Remove one → dbt fails at runtime. Fix: shared schema definition (YAML/JSON) that both consume, or at minimum dbt source tests that validate expected columns exist.
- [ ] Config separation — `config/datasets.yml` conflates reference data (URLs, metadata) with operational config (profiles, enrichment toggles). Registry changes when Cricsheet adds a league. Profiles change per environment. Fix: separate files or at least separate sections with env-var overrides for operational settings.

### Failure Mode Thinking
- [ ] Enrichment atomicity — if scraper crashes mid-batch after `on_batch` persists match records, next run skips those matches (in `espn_matches`) even if player/innings data was partial. Fix: write all four tables (matches, players, innings, balls) for a single match inside one transaction. Use `cricsheet_match_id` as dedup key for all.
- [ ] Circuit breaker on external APIs — retry with backoff exists, but no circuit breaker. ESPN returning 429s/503s = 3 retries × 1169 matches = 3507 wasted requests over hours. Fix: after N consecutive failures (e.g., 5), promote to `NoRetryError` and stop the batch. Counter-based circuit breaker.
- [ ] `run_async()` thread safety — ThreadPoolExecutor fallback spawns threads for async code in Dagster. If two assets run enrichment concurrently, concurrent DuckDB writes from different threads. DuckDB is single-writer. Latent bug — hasn't hit yet because Dagster runs sequentially by default.

### Testing Gaps
- [ ] End-to-end transformation test (golden file) — no test loads known fixture into bronze, runs dbt, asserts specific gold values. If `stg_deliveries.sql` introduces bug in `is_legal_delivery`, unit tests pass (no dbt), integration tests pass (check ranges not values). Fix: load `SAMPLE_MATCH_JSON` into bronze, run dbt, assert exact gold output.
- [ ] Data quality metrics as first-class output — `_is_valid_extras` and `_is_valid_total` are passive columns. No way to answer "how many invalid deliveries last Tuesday?" Fix: `_data_quality` table in DuckDB, dbt models append row per run with invalid counts, null rates, row count deltas.

### Team-Readiness / Documentation
- [x] CONTRIBUTING.md — setup, test commands, code style, where-to-add-things, git conventions, CI, deployment. Points to steering files and ADRs for deeper context.
- [x] Architecture diagram — `docs/architecture.md` with Mermaid diagrams (system overview, medallion flow, Dagster asset graph, request path, deployment topology)
- [ ] No runbook — "how do I add a new league?" "how do I backfill enrichment for season X?" "what do I do when ESPN scraping breaks?" 5-6 common workflows documented.
- [ ] Naming inconsistencies across source systems — `over_num`/`ball_num` (Cricsheet) vs `over_number`/`ball_number` (ESPN), `match_date` (gold) vs `date` (bronze), `innings` vs `inning_number`. Silver layer should normalize ESPN names to match Cricsheet convention.

## Pending — Future (Phased Roadmap)

### Phase 2: Live Match Data
- [ ] ESPN Playwright live poller — intercept hs-consumer-api commentary during live matches
- [ ] SSE endpoint on FastAPI for real-time push to frontend
- [ ] Live scorecard page in Next.js (updates without refresh)
- [ ] Deploy poller on laptop during matches, VPS later

### Phase 3: ML Models + Advanced Analytics
- [ ] Win probability model (XGBoost on historical features)
- [ ] Batting quality index (shot_control rolling window)
- [ ] Bowling heat maps, wagon wheels from ESPN spatial data
- [ ] Elo rating system (team + player)

### Phase 4: Polish + Growth
- [ ] More leagues (BBL, PSL, T20 World Cup)
- [ ] Mobile-responsive polish
- [ ] Ads / monetization (much later, not a priority)

### Parked
- [ ] Delete old data/ folder from parent Projects directory .git issue
- [ ] NL query interface

## Pending — Senior Code Review (April 2026, Week 2)
Full line-by-line review of every file in the project. Findings organized by severity.
Scope: IPL-only for now. Streamlit is legacy (will be replaced by React web app). Next.js frontend review deferred to next session.

### CRITICAL — Fix These First

- [x] Connection leak in `load_matches_to_bronze` — `src/ingestion/bronze_loader.py` uses `conn = get_write_conn()` with manual `conn.close()` at the end. If an exception occurs between the batch loop and `conn.close()` (e.g., in the final COUNT queries), the connection leaks. The `write_conn()` context manager was built specifically for this but isn't used here. Same issue in `load_people_to_bronze`. Fix: replace `conn = get_write_conn()` + manual `conn.close()` with `with write_conn() as conn:` in both functions.

- [x] SQL injection surface in `append_to_bronze` and `upsert_to_bronze` — `src/database.py`: `table_name`, `id_column`, and column names from incoming PyArrow data are interpolated directly into SQL via f-strings. Column names originate from parsed Cricsheet JSON → `pa.Table.from_pylist` → `append_to_bronze` → raw SQL. A malicious or malformed key in a Cricsheet JSON file could inject SQL. Fix: quote all identifiers with double quotes (e.g., `f'"{col}"'`). Also validate `id_column` against a safe identifier regex before use.

- [x] `full_refresh` flag only applies to first dataset (STILL UNFIXED) — RESOLVED by removing full_refresh entirely. For a full rebuild, delete `data/cricket.duckdb` and re-run the pipeline. Tables are created automatically on first write. Removed from: `load_matches_to_bronze`, `run_ingestion`, `IngestionConfig`, `--full-refresh` CLI flag, and `daily_refresh_job` config.

### HIGH — Architectural Issues

- [ ] `append_to_bronze` dedup for deliveries uses `match_id` only — if a match row was inserted but deliveries were only partially loaded (crash mid-batch before COMMIT), the next run sees the match_id in bronze.matches and skips all its deliveries. The atomic transaction mitigates this, but the dedup key for deliveries should ideally be a composite `(match_id, innings, over_num, ball_num)`. Currently `append_to_bronze` only supports a single `id_column` parameter. Fix: either extend `append_to_bronze` to accept composite keys, or add a separate dedup mechanism for deliveries.

- [x] `_ensure_bronze_tables` called on every `get_write_conn()` — added `_bronze_bootstrapped` module-level guard flag. First call runs full bootstrap (~12 DDL statements). Subsequent calls skip it. Eliminates redundant DDL overhead on every write connection open.

- [x] Inconsistent logging: `structlog` vs stdlib `logging` — replaced `logging.getLogger` with `structlog.get_logger` in `ball_scraper.py` and `run_ball_scraper.py`. Converted all printf-style messages to structlog keyword style. Removed global structlog reconfiguration in `run_ball_scraper.main()`.

- [ ] `src/orchestration/assets/__init__.py` is stale — exports `espn_match_enrichment` and `espn_image_enrichment` but not `espn_ball_enrichment`, `geocode_venue_coordinates`, or `weather_enrichment`. The parent `__init__.py` imports directly from the module so nothing breaks, but the stale `__init__.py` is misleading. Fix: update exports or remove the selective `__all__` and let the parent handle imports.

### MEDIUM — Code Quality

- [x] Type annotations use `callable` (lowercase) instead of `Callable` — replaced with `Callable` from `collections.abc` (in TYPE_CHECKING block) in match_scraper.py and ball_scraper.py.

- [x] Duplicated query patterns in `run_match_scraper.py` and `run_ball_scraper.py` — extracted `get_matches_for_season`, `get_all_matches`, `get_matches_by_ids` into `src/enrichment/queries.py`. Both CLI modules and Dagster enrichment asset now import from the shared module.

- [x] `weather_fetcher.py` has manual retry loop instead of using `@retry` decorator — replaced manual for-loop with `@retry(max_attempts=4, base_delay=1.0, exceptions=(httpx.TimeoutException, httpx.ConnectError, OSError))`.

- [x] `weather_fetcher.py` module-level `httpx.Client` never closed — replaced with lazy-initialized `_get_http_client()` getter. Client created on first use, not at import time.

- [x] `image_downloader.py` uses async without concurrency — replaced `httpx.AsyncClient` + `run_async()` with synchronous `httpx.Client`. The async code had no concurrency (sequential await in a loop), so async was pure overhead.

- [ ] `geocode_venue_coordinates` Dagster asset is a 150-line monolith — the asset function in `enrichment.py` does geocoding, alias detection, CSV writing, and DB writes all inline. Fix: move the geocoding orchestration logic into `src/enrichment/geocoder.py` (which already has the core functions). The Dagster asset should just call a high-level function and report metadata. DEFERRED — not a correctness issue, tackle when touching geocoder code next.

- [x] `_migrate_image_columns` silently swallows all exceptions — replaced `contextlib.suppress(Exception)` with specific `duckdb.CatalogException` catches + `logger.warning` for unexpected errors.

- [x] CORS regex too permissive — tightened from `https://.*\.vercel\.app` to `https://insideedge(-[a-z0-9]+)?\.vercel\.app`.

### LOW — Polish & Repo Hygiene

- [x] `.env` file in repo root — verified: already in `.gitignore` and not tracked by git. Safe.

- [x] `player_photo_viewer.html` in repo root — moved to `scripts/player_photo_viewer.html`.

- [x] `cricsheet-website-data-format.txt` in repo root — already in `.gitignore` and not tracked. No action needed.

- [x] `scripts/scrape_espn_squads.py` — already has a proper docstring. No action needed.

- [x] `data/espn_raw_sample.json` — already gitignored (data/ is in `.gitignore`). Not tracked. No action needed.

- [x] `src/dbt/target/` has 17+ Dagster run artifact directories — verified: not tracked by git. `.gitignore` covers it.

- [ ] No `__all__` exports in core modules — `src/database.py`, `src/config.py`, `src/tables.py` don't define `__all__`. For a portfolio project, explicit exports signal intentional API design. Low priority but good practice.

- [x] `Dockerfile` installs `[all]` including playwright, streamlit, dagster — changed to `pip install ".[dbt]"`. Pipeline only needs dbt deps.

- [x] `espn_squads.csv` and `espn_squads_backup_2008_to_2013.csv` dbt seeds not referenced by any model — harmless. They get loaded by `dbt seed` but no model references them. Not worth removing — they're backup data from the auction pipeline work.

### dbt-Specific

- [ ] Silver `_loaded_at` uses `current_timestamp` — every dbt run updates `_loaded_at` for ALL rows (full table rebuild). This is correct for table materialization but breaks audit trail if silver ever moves to incremental. Document this as a known limitation or use a conditional `_loaded_at` pattern.

- [ ] `source_exists` macro fallback schemas will drift — 6 ESPN silver models each have ~30 lines of typed NULL columns in the `WHERE false` fallback block. These must stay in sync with the real query above. Any column added to the real query but not the fallback (or vice versa) causes silent schema mismatches. Fix (future): extract column definitions into a shared macro or YAML config that generates both the real SELECT and the fallback.

### Decisions / Clarifications Recorded
- Auction data pipeline: HALTED at 2013. Manual curation effort too high. `espn_squads_backup_2008_to_2013.csv` is the backup. Not worth pursuing further unless a reliable automated source is found.
- Streamlit UI: LEGACY, now superseded by the deployed Next.js frontend. Kept for internal data exploration, not public use. No further investment.
- Default profile: `minimal` (IPL only) is intentional for current scope. T20I bronze is loaded but gold models are still IPL-only in production. Will expand to other leagues later.
- `render.yaml` uses `--profile minimal` — correct for now since only IPL is in gold. Update when expanding to more leagues.
- `apps/web/` has its own nested `.git` folder (separate git repo inside the monorepo). Be aware when doing git operations from repo root — changes inside apps/web/ don't show up in `git status` at the root.

## Technical Notes
- Python 3.13.2 on macOS (company laptop, Homebrew Python)
- pyproject.toml requires-python >=3.11; CI matrix tests 3.11 and 3.13
- Must use .venv (system pip blocked by PEP 668)
- DuckDB schemas: bronze.*, main_silver.*, main_gold.* (dbt prefixes with "main_")
- dbt profiles.yml uses relative path ../../data/cricket.duckdb
- Commit convention: conventional commits (feat:, fix:, docs:, refactor:, etc.) with detailed descriptions
- Season derivation: `EXTRACT(YEAR FROM match_date)` — format-agnostic, no hardcoded special cases. `season_raw` preserved in silver for reference.
- Formatting: ruff format (black-compatible, single tool for lint + format)
- No `full_refresh` flag in ingestion: for a full rebuild, delete `data/cricket.duckdb` and re-run. Tables auto-create on first write.

## Git Standards
- Clear commit titles with conventional commit prefixes
- Detailed multi-line descriptions explaining what and why
- Do NOT mention .kiro, steering files, or Kiro in commit messages
