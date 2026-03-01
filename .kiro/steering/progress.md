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
- [x] pytest test suite: 79 tests (27 unit, 38 integration, 14 smoke) — all passing, pushed to GitHub
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
- [ ] Fix schema name mismatch in config — settings says gold_schema="gold" but actual DuckDB schema is "main_gold"; API/UI hardcode "main_gold" everywhere instead of using config
- [ ] Move team name mappings to dbt seed CSV — dim_teams.sql has hardcoded CASE statement for franchise renames; every rename requires code change + rebuild
- [ ] Add retry/backoff on HTTP calls — downloader.py and ESPN scraper have no retry logic; single network blip fails entire pipeline
- [ ] Add FastAPI dependency injection — routers import query() directly; no Depends(), no service layer, no way to unit test API logic without real DB
- [ ] Handle SCD properly for dim_teams — franchise renames (RCB→RCBengaluru) need valid_from/valid_to, not a hardcoded CASE

### Lower Priority (cleanup / DevOps)
- [ ] asyncio.run() inside sync wrappers is fragile — will crash if called from existing event loop (Dagster async, Jupyter); restructure async boundary
- [ ] _ensure_tables in bronze_loader infers schema from first batch — NULL columns in first batch → wrong types; define explicit CREATE TABLE schemas
- [ ] Docker compose builds image 3x — pipeline/api/ui all use build:.; should build once + reference with image:
- [ ] Pre-commit has both ruff-format and black — redundant, can conflict; drop black, use ruff format only
- [ ] CI doesn't cache pip dependencies — pip install from scratch every run; add actions/cache
- [ ] No `make enrich` command — inconsistent with otherwise clean Makefile interface
- [ ] Remove dead code download_matches() in downloader.py — backward-compat wrapper, nothing references it
- [ ] pyproject.toml says requires-python >=3.11 but dev is on 3.13 — consider CI matrix for both
- [ ] Integration tests have hardcoded value expectations — "Kohli > 5000 runs" is brittle; test shape/constraints instead

## Pending — ETL Deep Review Backlog
Deep review of ingestion, dbt, Dagster, and DuckDB pipeline. Core DE showcase area.

### Ingestion Layer (Python → Bronze)
- [ ] Add transaction boundaries (BEGIN/COMMIT) around bronze writes — matches + deliveries insert is not atomic; crash between them = orphaned rows
- [ ] Batch processing for large datasets — all JSON files parsed into memory before write; will OOM on Tests/ODI datasets with millions of deliveries
- [ ] Define explicit DDL for bronze tables — _ensure_tables infers schema from first PyArrow batch; NULL columns → wrong types (overlaps with arch review item)
- [ ] Safe people.csv loading — DROP+CREATE is not crash-safe; load into staging table, validate, then swap
- [ ] Per-file error handling in ingestion — one malformed JSON kills the entire batch; parse with try/except, collect failures into dead-letter log
- [ ] Skip unchanged downloads — downloader always re-downloads full zip; use HTTP ETag/If-Modified-Since or local file existence check

### dbt Transformation Layer (Bronze → Silver → Gold)
- [ ] Strengthen silver layer — currently just type casting + computed flags; add data range validation, anomaly flagging, audit columns (_loaded_at, _source_file)
- [ ] Add referential integrity test: stg_deliveries.match_id → stg_matches.match_id (relationships test)
- [ ] Gold facts should read from silver, not other gold — fact_batting/bowling/summary read from fact_deliveries; creates fragile cascade, super_over filter silently inherited
- [ ] dim_matches adds no value over stg_matches — identical SELECT; add surrogate keys, derived columns, or enrichment joins to justify the layer
- [ ] Add incremental materialization to fact_deliveries — demonstrates the most important dbt production pattern; append new matches only
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
- Black version pinned to >=25.1.0,<27 to match CI (currently 26.1.0)

## Git Standards
- Clear commit titles with conventional commit prefixes
- Detailed multi-line descriptions explaining what and why
- Do NOT mention .kiro, steering files, or Kiro in commit messages
