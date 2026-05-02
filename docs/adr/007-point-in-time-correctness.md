# ADR-007: Point-in-Time Correctness for Analytical and ML Features

## Status
Accepted

## Date
2026-04-25

## Context

ADR-006 introduces four analytical shapes on top of gold: OBT, Entity Snapshots, Relationship Cubes, and Model Outputs. Three of these shapes (OBT, snapshots, and any ML training table derived from them) carry **as-of-that-match** columns — things like:

- Kohli's rolling 10-innings strike rate *at the moment of this ball*
- Kohli's career runs *before this match*
- Bumrah's spell economy *so far this innings*
- The matchup cube's (batter, bowler) cell *excluding future matches when training a model*

Every one of these columns is a point-in-time calculation. Get it wrong and the system silently leaks future information into historical features. The symptoms are invisible: queries return "correct-looking" numbers, models train with inflated accuracy, predictions look great on backtest and fail in production.

Data leakage is the single highest-risk failure mode in this architecture. It deserves a dedicated ADR that locks down the conventions, because one careless `SUM(runs) OVER (PARTITION BY player)` without a proper frame clause compromises every downstream feature that touches that column.

## Decision

All as-of / rolling / career-to-date / pre-match columns must be computed using **strictly past** data only — never including the current row or any future row. This applies across dbt models, Python feature engineering, and ML training code.

Three mechanisms enforce this:

1. A **naming convention** that makes as-of columns self-describing.
2. A **dbt macro** that wraps window functions with the safe frame clause.
3. **Singular dbt tests** that spot-check point-in-time correctness on real data.

Plus one architectural rule: **snapshots are the single source of truth for point-in-time state.** OBT columns that need rolling / career / as-of values are derived by joining to the relevant snapshot, not by recomputing window functions directly.

## Conventions

### Column naming

Every column that represents state *as of some reference point* has an explicit suffix:

| Suffix | Meaning | Example |
|---|---|---|
| `*_before` | cumulative value using only rows strictly before the reference row | `career_runs_before`, `career_matches_before` |
| `*_at_ball` | in-match running state up to and including the current ball (OK because it's within the same match, no cross-match leakage) | `batter_score_at_ball`, `team_score_at_ball` |
| `rolling_N_*` | rolling window over the last N rows, **not including the current row** | `rolling_10_innings_sr`, `rolling_6_balls_boundary_rate` |
| `season_to_date_*` | cumulative within current season, excluding current row | `season_to_date_wickets` |
| `as_of_*` | explicit as-of a named reference (typically used in snapshots) | `as_of_match_id`, `as_of_date` |

Columns without a suffix represent the current-row value (`runs_scored`, `batter`, `wicket_kind`). No ambiguity.

Columns representing the *current state across the full dataset* (career totals as of today) live only in serving-time views or in the latest row of a snapshot, never in OBT.

### The dbt macro

A macro `{{ point_in_time_window(expression, partition_by, order_by) }}` wraps window functions with the safe frame clause:

```sql
-- usage
{{ point_in_time_window(
    'sum(runs_scored)',
    partition_by='batter',
    order_by='match_date, match_id'
) }} as career_runs_before

-- expands to
sum(runs_scored) over (
    partition by batter
    order by match_date, match_id
    rows between unbounded preceding and 1 preceding
)
```

Every as-of column in dbt models uses this macro. Raw `OVER (PARTITION BY ... ORDER BY ...)` without a frame clause is disallowed for as-of columns. Code review (self-review) enforces this.

The macro also has a `rolling_n_rows` variant for rolling windows:

```sql
{{ rolling_window(
    'avg(strike_rate)',
    partition_by='batter',
    order_by='match_date, match_id',
    rows=10
) }} as rolling_10_innings_sr
-- expands to: rows between 10 preceding and 1 preceding
```

### Snapshots are the source of truth

OBT has a `rolling_10_innings_sr` column. It is **not** computed directly from `fact_deliveries` in the OBT model. It is computed in `snapshot_player_career` (one row per player-match) using the macro, and OBT joins to the snapshot on `(batter, match_id)` to pull the value.

This has three benefits:

1. **Single definition** — there's exactly one place where "rolling 10 innings SR" is defined. Changing the definition changes every downstream consumer.
2. **Easier to test** — point-in-time tests run on the snapshot. If the snapshot is correct, OBT inherits correctness.
3. **ML training alignment** — ML features pull from the same snapshot. Training and inference use the exact same column definitions. No drift.

The rule: any as-of column in OBT that spans more than the current match is derived by join to a snapshot, not by inline window function.

### In-match vs cross-match state

Some OBT columns are *within-match* running state: batter's score this innings, team total at the current ball, wickets lost in this innings so far. These are computed inline in OBT (they don't cross match boundaries, so there's no data-leakage risk) and use the `*_at_ball` naming convention.

In-match state is computed using window functions with `rows between unbounded preceding and current row` (inclusive of current ball, because "batter's score at ball" includes the runs just scored). That's different from the point-in-time macro; an explicit macro `{{ in_match_window(...) }}` exists for this case to avoid confusion.

## Tests

### Unit-level dbt tests

Singular tests in `src/dbt/tests/`:

- `assert_career_runs_before_is_strictly_prior.sql` — pick a known player with known match count. Verify `career_runs_before` at their Nth match equals the sum of `runs_scored` across their first N-1 matches. Zero leakage tolerance.
- `assert_rolling_sr_excludes_current_innings.sql` — for a batter's first innings ever, `rolling_10_innings_sr` must be NULL or 0, not derived from the current innings.
- `assert_snapshot_monotonic.sql` — in `snapshot_player_career`, `career_runs_before` must be non-decreasing as `match_date` ascends per player. Any decrease indicates a window-function bug.

These are SQL, run as part of `make dbt-test`, format-agnostic.

### Schema-level dbt tests

In `schema.yml` for every snapshot and OBT model:

- `not_null` on `as_of_match_id` and `as_of_date` (snapshots must know what they're as-of)
- `unique` composite key on (entity, as_of_match_id) for snapshots
- Relationships tests linking snapshot's `as_of_match_id` back to `dim_matches.match_id`

### ML training tests

Python-side, in `tests/ml/`:

- For any training dataframe assembled from OBT + snapshot features, assert that every feature column with a point-in-time suffix was derived from data with `match_date < target_row.match_date`.
- A fixture with synthetic known data: player X has 5 matches, match dates fixed. Training feature for match 3 must equal aggregates over matches 1 and 2 only.

These tests guard against leakage in feature-engineering code that bypasses the dbt macros.

## Handling Edge Cases

### First match of a player's career
`career_runs_before`, `career_matches_before`, `rolling_10_innings_sr` are all NULL (or 0 where NULL would be awkward for ML). Not "0 matches played so avg = 0 runs" — that's misleading. Prefer NULL and let downstream consumers decide.

### Same-day matches (rare but real)
A player can play two matches on the same day (e.g., warm-up + real match). Ordering must be by `(match_date, match_id)` not just `match_date`, so the ordering is deterministic. Macro uses this ordering by default.

### Backfills and re-computation
When a past match is corrected (e.g., Cricsheet updates a delivery), every downstream snapshot row for that player from that match onward must be recomputed. Mitigation: snapshots are fully rebuildable from silver; full refresh on corrections is acceptable because snapshots are not the bottleneck (~185K rows for players).

### Live matches
During a live match, snapshots are computed excluding the in-progress match (reference point is end-of-last-completed-match). OBT for the live match uses `*_before` values from the snapshot as-of the prior match. In-match `*_at_ball` state is computed live from streaming deliveries. No mixing.

## Consequences

### Positive
- **Zero data leakage by construction.** Every point-in-time column goes through the macro or derives from a snapshot that does. Enforcement is at code review + test time, not at runtime.
- **Single definition of each as-of concept.** Rolling-10 SR lives in `snapshot_player_career`. Period. Any model or visualization gets the same value.
- **ML training and inference use identical feature definitions.** Critical for model generalization.
- **Reviewable.** A PR that adds an as-of column without using the macro or by direct computation in OBT stands out.

### Negative
- **More join cost in OBT** — every OBT rolling column is a join to a snapshot. Benchmarked: 278K ball-level rows joined to 185K snapshot rows on (batter, match_id) is ~200ms in DuckDB. Acceptable.
- **Rigidity** — you can't just write a quick `SUM() OVER ()` in a model. That's the point.
- **Discipline required** — the macro and naming convention only work if they're used. Solo-dev discipline is the bottleneck.

### Non-Goals
This ADR does not:
- Mandate that every query in the API use point-in-time columns. Serving-time "Kohli's career stats" is fine as a cumulative aggregate.
- Address versioning of model outputs (handled in ADR-006 via `model_version` column).
- Cover survivorship bias or selection bias — those are separate statistical concerns.

It only mandates that any column labeled as "as of" or "before" or "rolling" does not include future information.

## References
- ADR-006 (Analytical data shapes post-gold) — depends on these conventions.
- dbt documentation on window functions and incremental models.
- Leakage discussions in the ML feature-store literature (Feast, Tecton), paraphrased for dbt-first workflows.
