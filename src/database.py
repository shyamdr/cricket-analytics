"""Centralized DuckDB connection factory.

Single source of truth for all database connections in the project.
Provides read-only and read-write connections with consistent
configuration, schema bootstrapping, and lifecycle management.

Usage:
    from src.database import get_read_conn, get_write_conn, query

    # Quick read query
    rows = query("SELECT * FROM main_gold.dim_matches LIMIT 10")

    # Write connection (creates schemas, ensures data dir)
    conn = get_write_conn()
    conn.execute("INSERT INTO ...")
    conn.close()

    # Read-only connection
    conn = get_read_conn()
    result = conn.execute("SELECT 1").fetchone()
    conn.close()
"""

from __future__ import annotations

import duckdb
import structlog

from src.config import settings

logger = structlog.get_logger(__name__)


def get_read_conn() -> duckdb.DuckDBPyConnection:
    """Get a read-only DuckDB connection.

    Use for queries that don't modify data (API, UI, enrichment lookups).
    DuckDB supports concurrent read-only connections.
    """
    return duckdb.connect(str(settings.duckdb_path), read_only=True)


def get_write_conn() -> duckdb.DuckDBPyConnection:
    """Get a read-write DuckDB connection.

    Creates the data directory and bronze schema if they don't exist.
    Use for ingestion, enrichment writes, and any DDL operations.
    """
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(settings.duckdb_path))
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {settings.bronze_schema}")
    return conn


def query(sql: str, params: list | None = None) -> list[dict]:
    """Execute a read-only SQL query and return results as a list of dicts.

    Opens and closes a connection per call. For hot-path usage (API, UI),
    prefer the module-level singleton in src.api.database or the
    Streamlit-cached connection in src.ui.data.
    """
    conn = get_read_conn()
    try:
        result = conn.execute(sql, params or [])
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row, strict=False)) for row in result.fetchall()]
    finally:
        conn.close()
