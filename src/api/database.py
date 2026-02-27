"""DuckDB connection manager for the API layer.

Wraps the centralized connection factory with a module-level singleton
for the API's hot path. DuckDB supports concurrent reads, so a single
long-lived read-only connection is safe and avoids per-request overhead.
"""

from __future__ import annotations

from src.database import get_read_conn

# Module-level read-only connection (DuckDB supports concurrent reads)
_conn = None


def get_conn():
    """Get a read-only DuckDB connection, creating one if needed."""
    global _conn
    if _conn is None:
        _conn = get_read_conn()
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
