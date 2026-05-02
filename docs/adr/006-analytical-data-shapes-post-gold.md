 # ADR-006: Analytical Data Shapes Post-Gold

## Status
Accepted

## Date
2026-04-25

## Context

Gold is clean, analytics-ready, and built on natural keys (ADR-004) and format-agnostic models (ADR-005). It answers a lot of questions: "Kohli's runs in this match," "top scorers this season," "team points table." The 9 gold models (`dim_*`, `fact_*`) are enough for Phase 1 of the product.

Phase 2+ is a different beast. The product vision includes:

1. **Advanced analytics** — "When does Kohli attack across batter-score × team-score × wickets-in-hand × opposition × venue × bowler-type?" That's six dimensions sliced simultaneously on ball-level data with a derived `is_attack` tag.
2. **Matchup and compositional predictions** — "Best bowler to Kohli + ABD at the crease right now?" Needs per-pair stats with small-sample shrinkage, plus optionally an ML model.
3. **Career trajectories with point-in-time state** — "Kohli's rolling 10-innings strike rate at match #347 of his career." ML training features need the same as-of-that-match view.
4. **ML predictions as joinable data** — win probability per ball, player ratings over time, context-adjusted stats.
5. **Natural-language query agent** (planned) — an "ask anything" endpoint that converts English to SQL. Needs a stable, discoverable schema and pre-computed statistical primitives.
6. **Similarity and cluster questions** — "Players similar to Dhoni," "matches comparable to tonight's final." Needs vector representations.

The gold layer alone cannot answer 2, 3, 4, or 6 at all, and it answers 1 and 5 poorly because every ad-hoc slice requires scanning `fact_deliveries` and joining to four dimension tables at query time.

This ADR decides what analytical shapes live **on top of gold** to cover everything we want to build, without over-engineering or locking us out of questions we haven't thought of yet.

## Options Considered

### Option A: Traditional Kimball data marts
Pre-aggregate along known dimensions: `mart_player_phase_performance`, `mart_player_venue_performance`, `mart_player_vs_bowler_type`, etc. Industry-standard BI pattern.

**Rejected.** The 5-dimensional Kohli-attack question explodes: `players × score-buckets × team-score-buckets × wickets-in-hand × oppositions × venues × bowler-types ≈ 10^10 rows`. Pre-aggregating every slice is impossible. You can only pre-aggregate the slices you know about, which locks the product into a fixed question set. Any question outside that set gets "we can't answer that."

### Option B: Semantic / metrics layer (dbt Semantic Layer, Cube)
A translation layer that converts user intent to SQL using metric definitions.

**Rejected.** Adds operational complexity (a new service, a new DSL) that a solo developer can't justify. Most of these tools expect cloud warehouses, not DuckDB. Good for teams with 10+ dashboard consumers needing metric consistency; wrong tool for one developer with one API.

### Option C: Feature store (Feast, Tecton)
ML-first architecture where every fact about an entity at a point in time is a versioned feature.

**Rejected as primary.** Feast needs Redis + Postgres. Tecton is paid. Overkill without 5+ production models in flight. Point-in-time correctness (the useful idea from this approach) can be achieved inside dbt.

### Option D: Lakehouse (Delta, Iceberg)
Parquet on object storage with transactional metadata.

**Rejected.** Wrong scale. Our dataset is megabytes, not petabytes. Adds ops complexity with zero payoff.

### Option E: Switch to ClickHouse or Apache Pinot
Purpose-built columnar analytics engines designed for thousands of QPS.

**Rejected.** Benchmarked mentally against our actual workload:
- Data scale: 278K balls now, projected 20M at full coverage. DuckDB handles 10× that on a laptop.
- Concurrency: ~100 concurrent users during live matches, <50 QPS peak. DuckDB handles 1000+ QPS for analytical queries.
- Writes: one poller writing ~0.13 writes/sec during live matches. DuckDB's single-writer model is fine.
- Migration cost from DuckDB is real (2–4 weeks) but not painful; operational cost of ClickHouse *right now* is real every single day.

ClickHouse becomes the right answer at ~5,000+ concurrent users or continuous streaming ingestion. Pinot becomes relevant only at LinkedIn-scale consumer-facing analytics (millions of simultaneous users). Neither scenario is within two orders of magnitude of InsideEdge's realistic trajectory. DuckDB stays (ADR-001).

### Option F (chosen): Four analytical shapes on top of gold

Not a single "platinum" layer. A small family of complementary shapes, each solving one kind of question that gold alone cannot. Named by what they are, not by color.

## Decision

Four analytical shapes sit on top of gold. Each has a distinct grain and purpose. Together they cover every realistic cricket-analytics question.

**Source-of-truth rule:** silver (`stg_deliveries`, `stg_matches`, `stg_people`, ESPN silver models) is the canonical source for everything downstream. The existing `dim_*` and per-match `fact_*` tables, the new OBT, Entity Snapshots, and Relationship Cubes are all **siblings** fed from silver — none is derived from another. Model Outputs are the exception: they read from OBT and snapshots because ML features need point-in-time state already assembled. This keeps the DAG shallow, rebuilds idempotent, and avoids the anti-pattern of "gold model A reads from gold model B which reads from gold model C."

### Shape 1: OBT (Event Spine) — `fact_deliveries_enriched`
**Grain:** one row per legal ball.
**Purpose:** ad-hoc, multi-dimensional slicing at ball level. The backbone of everything else.
**Materialization:** incremental table in DuckDB (via dbt). Rebuilt for new matches only.
**Principle:** every piece of context that existed at the moment of the ball is attached as a column. No query-time joins to dimension tables required to filter or group.
**Source:** `stg_deliveries` and `stg_matches` (silver) joined to `dim_players`, `dim_teams`, `dim_venues`, and `fact_weather` for denormalized context. OBT is a **sibling** of the existing `dim_*` and per-match `fact_*` tables, not derived from them — they share silver as their common source of truth.

Context columns grow over time but include at least:
- Match context — match_id, season, date, venue, phase, innings, is_super_over
- Score state — batter_score_so_far, team_score_at_ball, wickets_in_hand, balls_faced_by_batter, required_run_rate (2nd innings), par_score_delta
- Batter context — career_matches_before, career_runs_before, rolling_N_innings_sr, rolling_N_innings_boundary_rate
- Bowler context — spell_economy_so_far, career_wickets_before, rolling_N_innings_economy
- Player attributes — batter_handedness, bowler_type (pace/spin/medium), batter_role, bowler_role
- Environmental — is_floodlit, weather_temp, weather_humidity, weather_wind, venue_elevation
- Derived tags — is_attack (rolling SR + boundary-rate threshold), is_pressure_ball (match context), is_boundary_streak, phase

OBT is the primary target for the NL agent and the training source for most ML models. At 20M balls × ~60 columns, DuckDB scans it in under 500ms for filtered aggregations. Point-in-time correctness (ADR-007) is mandatory for every "as-of" column.

### Shape 2: Entity Snapshots — per-entity state over time
**Grain:** one row per (entity, match).
**Purpose:** point-in-time entity state. Career trajectories. ML feature generation without data leakage.
**Materialization:** incremental tables.

Snapshot tables, one per entity kind:
- `snapshot_player_career` — after every match a player played, cumulative career stats + rolling-window stats + rating/Elo. ~927 players × ~200 matches ≈ 185K rows. Enables career trajectory charts (Kohli's SR over 200 matches) as a single sorted scan.
- `snapshot_team_state` — after every match, team cumulative stats + Elo + recent form.
- `snapshot_venue_state` — rolling venue characteristics (avg first-innings score, chase success rate, boundary density) over time.
- `snapshot_match_state` — per-ball in-match state (win probability timeline, pressure timeline). One row per ball per match, but as a separate table from OBT because it's driven by model outputs and refreshed on different cadence.

Snapshots are the **single correct source** for point-in-time joins. OBT's `rolling_N_innings_sr` columns are computed *from* snapshots, not directly from `fact_deliveries`, to keep the point-in-time logic in one place.

### Shape 3: Relationship Cubes — entity-to-entity aggregates with shrinkage
**Grain:** one row per (entity-A, entity-B, optional context dim).
**Purpose:** compositional and matchup questions. Pre-computed statistical products (not just sums).
**Materialization:** full-refresh tables, rebuilt nightly.

Starting cube set:
- `cube_matchup_batter_bowler` — (batter, bowler) and (batter, bowler, phase). Columns: `raw_runs`, `raw_balls`, `raw_dismissals`, `shrunken_avg_runs`, `shrunken_dismissal_rate`, `confidence_score`, `sample_size`. Shrinkage uses Empirical Bayes toward a (batter-type × bowler-type) prior.
- `cube_team_head_to_head` — (team_a, team_b, venue_optional). Rolling W/L, margins, venue-specific breakdowns.
- `cube_player_at_venue` — (player, venue). Historical stats at each venue.
- `cube_player_vs_bowler_type` — (player, bowler_type) and (bowler, batter_type).

**Why materialized, not views:** shrinkage is a statistical product involving joins to prior-distribution tables and similarity tables. Computing it on a view at every page load is wasted work, and it makes the NL agent's job harder (the LLM would need to reason about shrinkage SQL; the materialized cube lets it just `SELECT shrunken_avg_runs`). Refresh cost is trivial at our scale.

Cubes are deliberately few (5–8, not 25). Every cube must justify its existence with concrete product features that use it.

### Shape 4: Model Outputs — predictions as queryable tables
**Grain:** depends on the model.
**Purpose:** ML/statistical output stored as regular tables, joinable to everything else, versioned.
**Materialization:** full-refresh or incremental per model.

Starting model-output tables:
- `model_win_probability_timeline` — per (match_id, innings, over_num, ball_num), predicted WP + confidence interval + `model_version`.
- `model_ball_outcome_predictions` — per ball, expected runs and dismissal probability.
- `model_player_ratings_timeline` — per (player, match), Elo and custom rating + `model_version`.
- `model_matchup_projections` — per (batter, bowler, phase, venue, context), predicted runs/dismissal for unseen or low-sample situations.

Every output table carries `model_version` and `trained_at` columns. Re-training writes a new version; old versions stay for reproducibility. The API reads the latest version; analytics queries can pin to a specific version for reproducibility.

### Shape 5 (deferred): Embeddings / vector space
Player-profile vectors for similarity search. Commentary text embeddings for NL-agent retrieval. Deferred until the NL agent is actually in scope; they're not foundational, and DuckDB's vector support is still maturing. When built, they live either as `FLOAT[]` columns in DuckDB or in a sibling file-based index (LanceDB, sqlite-vss).

## What Stays From the Current Architecture

The existing gold layer is **not deprecated.** It serves distinct purposes:

- **`dim_players`, `dim_teams`, `dim_venues`, `dim_matches`** — small lookup / serving tables. Human-readable columns. Used by every API endpoint today. They stay. They will be referenced as dimension sources when building OBT context columns.
- **`fact_batting_innings`, `fact_bowling_innings`, `fact_match_summary`** — per-match aggregates. Already used by API routers for fast per-match queries. They stay. At 17K/13K/2.3K rows, they're trivially cheap and answer "give me the scorecard for this match" in 2ms without touching OBT.
- **`fact_deliveries`** — the existing ball-level table. Same grain as the planned OBT. It continues to serve existing API endpoints during transition; once `fact_deliveries_enriched` is in place and API consumers have migrated, `fact_deliveries` can be retired or kept as a thin view. **OBT is not built from `fact_deliveries`** — both are derived from `stg_deliveries`.
- **`fact_weather`** — per-match weather. Used by OBT as a source for environmental context columns.

The right mental model is not "medallion layer 4." It is: **gold has dimensions and per-match facts; on top of gold sit four application-specific shapes for ball-level analytics.**

## Schema Organization

DuckDB schemas:
- `main_silver.*` — existing
- `main_gold.*` — existing (dims + kimball facts + `fact_deliveries_enriched` lives here too; see note below)
- `main_gold.*` — OBT + snapshots + cubes + model outputs all live here, named by prefix (`fact_*`, `snapshot_*`, `cube_*`, `model_*`)

Rationale for keeping everything in `main_gold` rather than introducing `main_platinum` or `main_analytics`:
- One schema = simpler for the NL agent's schema prompt
- Prefixes (`fact_`, `snapshot_`, `cube_`, `model_`) are self-documenting
- `dbt-duckdb` and `src/tables.py` already handle this well

dbt folder organization follows suit:
```
src/dbt/models/
├── silver/
└── gold/
    ├── dim/          dim_*.sql
    ├── fact/         fact_*.sql (including fact_deliveries_enriched)
    ├── snapshot/     snapshot_*.sql
    ├── cube/         cube_*.sql
    └── model/        model_*.sql (outputs of ML models, written by Python back into the warehouse)
```

Model outputs are written by Python/ML code into DuckDB tables; dbt then has `source()`-style refs to them so downstream dbt models can use them.

## Build Order

Not all at once. The four shapes get built incrementally, each delivering features as it lands:

1. **OBT foundation** — build `fact_deliveries_enriched` with the initial set of ~30 context columns (match + score-state + phase + venue + basic rolling stats). Unlocks ad-hoc slicing and ~15 of the 40 planned match-analytics features.
2. **Player snapshot** — `snapshot_player_career` with rolling-window stats and basic Elo. Unlocks career trajectory charts and is a prerequisite for OBT's point-in-time rolling columns (re-plumb OBT to derive them from the snapshot).
3. **Matchup cube** — `cube_matchup_batter_bowler` with shrinkage. Unlocks matchup matrix, best-bowler-to-pair, and gives the NL agent proper statistical primitives.
4. **Team and venue snapshots** — as analytics features call for them.
5. **Win probability model output** — `model_win_probability_timeline`. Phase 3 work.
6. **Additional cubes and model outputs** — only when a concrete product feature justifies each one.

## Non-Goals

- We are not building a platinum layer named `main_platinum`. That was an intermediate proposal; the final decision is a single `main_gold` schema with prefixed table names.
- We are not deprecating `dim_*` or kimball `fact_*` tables. They continue to serve the API and UI.
- We are not pre-aggregating 25 narrow marts by player × venue × phase × bowler-type. OBT + cubes with shrinkage cover the same space without the cardinality explosion.
- We are not switching engines. DuckDB stays (ADR-001). Nightly Parquet mirror is a cheap insurance policy documented separately.

## Consequences

### Positive
- **No question gets "we can't answer that" as an architectural answer.** Every cricket-analytics question maps to one of: event slicing (OBT), entity state (snapshots), relationship (cubes), prediction (model outputs), or similarity (embeddings, when added).
- **NL agent has a stable, small schema target.** ~20 total analytical tables, all prefixed, all documented in a metadata file it can use as context.
- **ML features are free from data leakage by construction** because snapshots are the single source of point-in-time truth.
- **Gold layer stays small and stable** — it's the core contract. OBT, snapshots, cubes, model outputs can evolve independently.
- **Incremental delivery** — each shape ships on its own, unlocking features without blocking the others.

### Negative
- **OBT will be wide (60+ columns)** and grow. Needs discipline to keep column semantics clear. Mitigation: strict naming convention (`*_before`, `*_at_ball`, `rolling_N_*`) + documented column descriptions in schema.yml.
- **Nightly rebuild time will grow.** OBT + snapshots + cubes for 20M balls projected at ~5 minutes on a laptop. Acceptable.
- **More tables to test.** Each shape needs its own dbt tests + point-in-time correctness tests (ADR-007).
- **Schema churn during Phase 2** — OBT and snapshot column sets will evolve. Mitigate by versioning the NL agent's schema metadata alongside the tables.

### Risks and Mitigations
- **Risk: context columns in OBT drift from their canonical source** (e.g., rolling SR computed from OBT directly instead of from snapshot).
  **Mitigation:** enforce that rolling / career / as-of columns in OBT are computed by joining to the relevant snapshot table, not recomputed inline.
- **Risk: cube cardinality creep** — each new context dim multiplies cube size.
  **Mitigation:** no cube is added without a concrete feature justifying it. Cubes stay small (<1M rows each) and periodically audited.
- **Risk: model outputs go stale** silently when dbt runs but Python retraining doesn't.
  **Mitigation:** `model_version` + `trained_at` columns + freshness policies in Dagster.

## Open Questions for Later

- Exact shrinkage priors for matchup cube (Empirical Bayes vs hierarchical Bayes).
- Whether match-state snapshots (`snapshot_match_state`) merge into OBT as additional columns or stay separate.
- Vector store choice when embeddings land (DuckDB native vs LanceDB vs sqlite-vss).
- Whether to expose the NL agent as a public endpoint or gate it (cost + abuse considerations).

These do not block OBT + player snapshot + matchup cube, which is the Phase 2 starting point.
