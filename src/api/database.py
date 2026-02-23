"""DuckDB connection manager for the API layer."""

from __future__ import annotations

import duckdb

from src.config import settings

# Module-level read-only connection (DuckDB supports concurrent reads)
_conn: duckdb.DuckDBPyConnection | None = None


def get_conn() -> duckdb.DuckDBPyConnection:
    """Get a read-only DuckDB connection, creating one if needed."""
    global _conn
    if _conn is None:
        _conn = duckdb.connect(str(settings.duckdb_path), read_only=True)
    return _conn


def close_conn() -> None:
    """Close the DuckDB connection."""
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None


def query(sql: str, params: list | None = None) -> list[dict]:
    """Execute a SQL query and return results as a list of dicts."""
    conn = get_conn()
    result = conn.execute(sql, params or [])
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row, strict=False)) for row in result.fetchall()]
