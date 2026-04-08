"""DuckDB connection manager for the API layer.

Uses a threading lock to prevent concurrent access to the DuckDB
connection. DuckDB's Python binding crashes (SIGTRAP) when multiple
threads call execute() on the same connection simultaneously, even
in read-only mode. The lock serializes queries — safe and fast enough
for our scale (queries take <10ms each).

Dependency injection:
    Routers receive the ``query`` callable via ``Depends(get_query_fn)``.
    Tests can override ``get_query_fn`` with ``app.dependency_overrides``
    to inject a mock without touching the real database.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from src.database import get_read_conn

_conn = None
_lock = threading.Lock()

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
    with _lock:
        if _conn is not None:
            _conn.close()
            _conn = None


def query(sql: str, params: list | None = None) -> list[dict]:
    """Execute a SQL query and return results as a list of dicts.

    Thread-safe: uses a lock to serialize DuckDB access.
    """
    with _lock:
        conn = get_conn()
        result = conn.execute(sql, params or [])
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row, strict=False)) for row in result.fetchall()]


def get_query_fn() -> QueryFn:
    """FastAPI dependency that provides the query callable."""
    return query


DbQuery = Annotated[QueryFn, Depends(get_query_fn)]
