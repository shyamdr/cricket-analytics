# ADR-001: DuckDB as the Storage and Compute Engine

## Status
Accepted

## Context
We need an analytical database for an IPL cricket analytics platform.
The project must be zero-cost, portable (runs on any laptop), and
capable of handling ~1200 match files with ball-by-ball granularity.

## Options Considered
1. PostgreSQL — mature, but requires a running server process
2. SQLite — embedded, but poor analytical query performance
3. DuckDB — embedded, columnar, optimized for analytics
4. Cloud warehouse (BigQuery/Snowflake) — not free

## Decision
Use DuckDB as the single storage and compute layer.

## Rationale
- Zero infrastructure: single file, no server process
- Columnar storage: fast aggregations on delivery-level data
- Native JSON/CSV ingestion: reads Cricsheet data directly
- dbt-duckdb adapter: integrates with our transformation layer
- Dagster integration: dagster-duckdb resource available
- Portable: the .duckdb file can be rebuilt from pipeline on any machine

## Consequences
- No concurrent write access (single-writer model) — acceptable for this use case
- Limited to local machine memory — sufficient for IPL dataset (~300K deliveries)
- No built-in replication — mitigated by reproducible pipeline
