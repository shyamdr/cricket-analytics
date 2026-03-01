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
- [ ] pyproject.toml says requires-python >=3.11 but dev is on 3.13 — consider CI matrix for both
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
- [ ] Add dbt tests on fact tables — zero tests on fact_batting_innings, fact_bowling_innings, fact_match_summary; need not_null on grain, unique composite key, range checks
- [ ] Add business rule dbt tests (singular or dbt_expectations) — e.g., every match has ≥1 delivery, no batter faces >120 balls in T20, total_runs = batter_runs + extras
- [ ] Add column-level documentation in schema.yml — most columns lack descriptions; dbt docs generate produces empty data dictionary
- [ ] Consider silver models as views instead of tables — they're just transforms, no need to store twice in DuckDB

### Dagster Orchestration
Items below are from the ETL deep review. See "Dagster Orchestration — Full Redesign" section for the comprehensive job/asset graph analysis.
- [ ] Remove dead CricketAnalyticsConfig resource — defined in resources.py but never registered or used; assets import from src.config directly
- [ ] Add Dagster sensors — blind daily cron is less production-grade than event-driven triggers (watch for new files or poll Cricsheet RSS)

### Cross-Cutting ETL
- [ ] Add audit columns to bronze tables — _loaded_at, _source_file, _run_id for lineage and debugging
- [ ] Add observability beyond structlog — persist row counts per layer per run, track data freshness, consider Dagster AssetObservation/FreshnessPolicy

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
- [ ] Map dbt sources to Dagster asset keys — in @dbt_assets, configure source_asset_key_map or add meta tags in sources.yml so Dagster knows source('bronze', 'matches') = the bronze_matches Python asset. Without this, the DAG is disconnected and dbt can run before ingestion.
  - Option A: In sources.yml, add `meta: { dagster: { asset_key: ["bronze_matches"] } }` to each source table
  - Option B: Use `@dbt_assets(source_asset_key_map=...)` parameter
  - This is the single most important fix — it connects the entire graph

### Step 2: Fix espn_enrichment dependency
- [ ] Change espn_enrichment deps from ["bronze_matches"] to the dbt dim_matches asset key — the enrichment asset queries main_gold.dim_matches to get the match list, so it must run AFTER dbt, not after bronze ingestion. Current dep means Dagster thinks enrichment can run right after bronze, but it'll fail because dim_matches doesn't exist yet.
  - After Step 1, the dbt dim_matches model becomes a proper Dagster asset
  - Change to: `deps=[AssetKey("dim_matches")]` or however dagster-dbt exposes the model key
  - Verify in Dagster UI that the lineage shows: bronze → dbt → enrichment

### Step 3: Fix job definitions

#### full_pipeline_job — AssetSelection.all()
- [ ] Status: KEEP. Works correctly, useful for CLI `make all` equivalent. Redundant with "Materialize All" in UI but harmless.

#### ingestion_job — AssetSelection.groups("bronze")
- [ ] Status: KEEP. Clean, correct, materializes bronze_matches + bronze_people.

#### transformation_job — complex set arithmetic (BROKEN)
- [ ] REWRITE. Current selection `AssetSelection.groups("bronze", "enrichment").downstream() - AssetSelection.groups("bronze", "enrichment")` is fragile and hard to reason about. If you add a new asset group (e.g., "ml") downstream of bronze, it gets accidentally included.
  - Fix: select dbt assets directly. Either `AssetSelection.assets("dbt_analytics_assets")` or tag dbt models with a group and use `AssetSelection.groups("dbt")`.
  - After Step 1, this becomes trivial because the dbt assets are properly connected.

#### enrichment_job — AssetSelection.groups("enrichment") (BROKEN DEPENDENCY)
- [ ] Status: works in isolation but will fail if dbt hasn't run. After Step 2, the dependency is correct and Dagster will refuse to run enrichment without dim_matches being materialized. No code change needed on the job itself — the fix is in the asset dependency.

#### delta_pipeline_job (BROKEN — multiple issues)
- [ ] REWRITE COMPLETELY. Three problems:
  1. Selection `groups("bronze") | groups("enrichment").upstream()` — since espn_enrichment's upstream is only bronze_matches (wrong dep), this resolves to just `groups("bronze")`. dbt is NOT included. So delta ingests new matches but never transforms them to gold. The new matches are invisible to the API/UI.
  2. Config uses legacy `"ops"` key — should use `RunConfig` from the current Dagster API:
     ```python
     from dagster import RunConfig
     config=RunConfig(ops={"bronze_matches": IngestionConfig(datasets=["recent_7"], full_refresh=False)})
     ```
  3. Baking config into the job definition is inflexible — can't change datasets without creating a new job. Better: use a schedule or sensor that provides config at runtime via `RunRequest`.
  - After Steps 1+2, the correct selection is just `AssetSelection.assets("bronze_matches")` — Dagster will automatically include dbt and enrichment as downstream dependencies.

#### daily_delta_schedule (BROKEN — schedules the broken job)
- [ ] REWRITE after fixing delta_pipeline_job. Consider replacing with a sensor that checks Cricsheet for new data before triggering, rather than blind daily cron.

### Step 4: Simplify to 3 jobs (target state)
After fixing the asset graph, you only need:
- [ ] `full_pipeline` — `AssetSelection.all()` — rebuild everything from scratch
- [ ] `daily_refresh` — schedule/sensor that materializes bronze_matches with recent_7 config; Dagster auto-runs dbt + enrichment downstream because the graph is correct
- [ ] `enrichment_backfill` — `AssetSelection.assets("espn_enrichment")` — for manually scraping historical seasons
- [ ] Remove `transformation_job` — unnecessary; just click "Materialize" on dbt assets in UI, or they run automatically as part of full_pipeline/daily_refresh
- [ ] Remove `ingestion_job` — same reasoning; click "Materialize" on bronze assets in UI

### Step 5: Dagster best practices to add
- [ ] Use Dagster's `FreshnessPolicy` on gold assets — e.g., dim_matches should be no more than 24 hours stale; Dagster UI shows freshness status
- [ ] Use `AssetObservation` to record row counts as observable metadata — currently logged via structlog but not visible in Dagster UI
- [ ] Consider `AutoMaterializePolicy` — Dagster can automatically materialize downstream assets when upstream changes, eliminating the need for most jobs entirely

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
- Formatting: ruff format (black-compatible, single tool for lint + format)

## Git Standards
- Clear commit titles with conventional commit prefixes
- Detailed multi-line descriptions explaining what and why
- Do NOT mention .kiro, steering files, or Kiro in commit messages
