"""DuckDB connection manager for the API layer.

Wraps the centralized connection factory with a module-level singleton
for the API's hot path. DuckDB supports concurrent reads, so a single
long-lived read-only connection is safe and avoids per-request overhead.

Dependency injection:
    Routers receive the ``query`` callable via ``Depends(get_query_fn)``.
    Tests can override ``get_query_fn`` with ``app.dependency_overrides``
    to inject a mock without touching the real database.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from src.database import get_read_conn

# Module-level read-only connection (DuckDB supports concurrent reads)
_conn = None

# Type alias for the query callable signature
QueryFn = Callable[[str, list | None], list[dict]]


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


def get_query_fn() -> QueryFn:
    """FastAPI dependency that provides the query callable.

    Override in tests via ``app.dependency_overrides[get_query_fn]``.
    """
    return query


# Annotated dependency — use this in router signatures to avoid B008
DbQuery = Annotated[QueryFn, Depends(get_query_fn)]
