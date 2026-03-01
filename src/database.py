"""Centralized DuckDB connection factory.

Single source of truth for all database connections in the project.
Provides read-only and read-write connections with consistent
configuration, schema bootstrapping, and lifecycle management.

Usage:
    from src.database import get_read_conn, get_write_conn, query

    # Quick read query
    rows = query("SELECT * FROM main_gold.dim_matches LIMIT 10")  # schema from settings

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

from typing import TYPE_CHECKING

import duckdb
import structlog

if TYPE_CHECKING:
    import pyarrow as pa

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


def append_to_bronze(
    conn: duckdb.DuckDBPyConnection,
    table_name: str,
    data: pa.Table,
    id_column: str,
) -> int:
    """Idempotent append of a PyArrow table into a bronze DuckDB table.

    Uses a SQL anti-join for dedup instead of loading all existing IDs
    into Python memory. Scales to millions of rows without OOM.

    Args:
        conn: An open read-write DuckDB connection.
        table_name: Fully-qualified table name (e.g. ``bronze.matches``).
        data: PyArrow Table to load.
        id_column: Column used for dedup (e.g. ``match_id``).

    Returns:
        Number of new rows inserted.
    """
    if data.num_rows == 0:
        return 0

    tmp_name = "_tmp_bronze_load"
    conn.register(tmp_name, data)

    try:
        # Check if target table exists
        table_exists = False
        try:
            conn.execute(f"SELECT 1 FROM {table_name} LIMIT 0")
            table_exists = True
        except duckdb.CatalogException:
            pass

        if not table_exists:
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM {tmp_name}")
            new_rows = data.num_rows
        else:
            # Count before insert
            (count_before,) = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()

            # Anti-join dedup: only insert rows whose id_column is not already present
            conn.execute(
                f"""INSERT INTO {table_name}
                    SELECT t.* FROM {tmp_name} t
                    WHERE t.{id_column} NOT IN (
                        SELECT DISTINCT {id_column} FROM {table_name}
                    )"""
            )

            (count_after,) = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            new_rows = count_after - count_before
    finally:
        conn.unregister(tmp_name)

    if new_rows > 0:
        logger.info("bronze_append", table=table_name, new_rows=new_rows)
    else:
        logger.info("no_new_rows", table=table_name)

    return new_rows
