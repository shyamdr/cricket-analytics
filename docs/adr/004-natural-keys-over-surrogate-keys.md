# ADR-004: Natural Keys Over Surrogate Keys

## Status
Accepted

## Date
2026-04-17

## Context

Traditional data warehouse design favors integer surrogate keys on dimensions, with foreign key columns on facts (`batter_id`, `bowler_id`, `team_id`, `venue_id`). This is the Kimball orthodoxy: stable, compact, and performant joins.

For this project, the natural keys available from source data are:
- `match_id` — Cricsheet file stem (e.g. `335982`), stable across Cricsheet updates
- `player_id` — 8-char hex hash from Cricsheet people registry, stable across datasets
- `player_name` — short name like `'V Kohli'`, used directly in delivery rows
- `team_name` — full name like `'Chennai Super Kings'`, also used directly in delivery rows
- `venue` — full venue name string

All of these are already present in every row of bronze data. Introducing surrogate keys would require:
1. A dim_* lookup step to assign integer IDs
2. FK columns on every fact table
3. Joins back to the dimension to recover human-readable names for any analytics query

## Decision

**Use natural keys. No surrogate keys on dimensions. No FK columns on facts.**

## Rationale

### DuckDB is columnar and already dictionary-encodes strings
At storage level, `batting_team = 'Mumbai Indians'` is stored as a dictionary reference, not a full string copy per row. DuckDB gets most of the surrogate-key storage benefit automatically. The common "integers are smaller than strings" argument doesn't apply.

### DuckDB doesn't enforce foreign keys
Even if we added FK columns, DuckDB wouldn't enforce them at insert time. Integrity checking has to happen elsewhere (dbt tests). Surrogate keys give us none of the enforcement guarantees they provide in PostgreSQL or SQL Server.

### Scale is small
278K deliveries across 1169 IPL matches, 927 players, 63 venues. A string-vs-integer join at this size is a rounding error on query time. Even at full Cricsheet scale (~5M deliveries across all leagues), joins on columnar-compressed strings remain fast.

### This is an analytics platform for humans to explore
The primary consumer after the API is a SQL prompt or Streamlit app. `batter = 'V Kohli'` is readable; `batter_id = 437` is not. Requiring a dim_players join on every ad-hoc query would be painful.

### Referential integrity via dbt tests, not DB constraints
dbt's `relationships` test (`stg_deliveries.match_id → stg_matches.match_id`) catches orphan rows during CI. This is the same enforcement level we'd get from surrogate keys in DuckDB, with zero extra columns.

## Consequences

### Positive
- Ad-hoc SQL queries on gold layer are readable without joins
- No dim_* lookup step needed in silver → gold
- New facts can be added without surrogate-key plumbing
- Streamlit and API code is simpler (no repeated ID→name joins)

### Negative
- If a player's canonical name ever changes in Cricsheet (e.g. case correction), it appears as a new row in `dim_players`. We'd need to dedup via `player_id` or handle it as a data quality event.
- Large-scale batch joins might be 5-10% slower than integer joins at multi-billion-row scale. Acceptable at our scale; re-evaluate if we ever approach that.
- A team rename (e.g. Delhi Daredevils → Delhi Capitals) shows up as two rows in `dim_teams`. Handled by the `team_name_mappings` seed which provides `current_franchise_name` for grouping. See `dim_teams.sql`.

### Tradeoff accepted
We lose the classical "change the name in one place, all facts update" property. In exchange, we get a platform anyone can query directly without memorizing ID mappings. For a cricket analytics product where curiosity-driven queries are the norm, that's the right tradeoff.

## When to reconsider

Revisit this decision if:
- Fact table grows past 100M rows and joins become a measurable bottleneck
- We move off DuckDB to a database that enforces FKs
- Name changes in source data become frequent enough that dedup overhead dominates
