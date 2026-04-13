"""Centralized DuckDB connection factory.

Single source of truth for all database connections in the project.
Provides read-only and read-write connections with consistent
configuration, schema bootstrapping, and lifecycle management.

Usage:
    from src.database import get_read_conn, write_conn

    # Write connection — context manager guarantees cleanup
    with write_conn() as conn:
        conn.execute("INSERT INTO ...")

    # Read-only connection
    conn = get_read_conn()
    result = conn.execute("SELECT 1").fetchone()
    conn.close()
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from typing import TYPE_CHECKING

import duckdb
import structlog

if TYPE_CHECKING:
    from collections.abc import Generator

    import pyarrow as pa

from src.config import settings

logger = structlog.get_logger(__name__)

# Safe SQL identifier pattern — same as schema validation in config.py
_SAFE_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_identifier(name: str, label: str = "identifier") -> None:
    """Reject identifiers that aren't safe for SQL interpolation.

    Raises ValueError if the name contains characters outside
    ``[a-zA-Z0-9_]`` or doesn't start with a letter/underscore.
    """
    if not _SAFE_IDENTIFIER_RE.match(name):
        raise ValueError(f"Unsafe SQL {label}: {name!r}")


def _q(name: str) -> str:
    """Double-quote a SQL identifier to handle reserved words and special chars."""
    return f'"{name}"'


def get_read_conn() -> duckdb.DuckDBPyConnection:
    """Get a read-only DuckDB connection.

    Use for queries that don't modify data (API, UI, enrichment lookups).
    DuckDB supports concurrent read-only connections.
    """
    return duckdb.connect(str(settings.duckdb_path), read_only=True)


def get_write_conn() -> duckdb.DuckDBPyConnection:
    """Get a read-write DuckDB connection.

    Creates the data directory, bronze schema, and all bronze tables
    (Cricsheet + ESPN) if they don't exist. Safe to call repeatedly.
    Use for ingestion, enrichment writes, and any DDL operations.

    PREFER ``write_conn()`` context manager over this function —
    it guarantees the connection is closed even on exceptions.
    """
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(settings.duckdb_path))
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {settings.bronze_schema}")
    _bootstrap_bronze_tables(conn)
    return conn


@contextmanager
def write_conn() -> Generator[duckdb.DuckDBPyConnection]:
    """Context manager for a read-write DuckDB connection.

    Guarantees the connection is closed when the block exits,
    even if an exception is raised. Use this instead of
    ``get_write_conn()`` to prevent connection leaks.

    Usage::

        with write_conn() as conn:
            conn.execute("INSERT INTO ...")
    """
    conn = get_write_conn()
    try:
        yield conn
    finally:
        conn.close()


def _bootstrap_bronze_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """Create all bronze tables with explicit DDL if they don't exist.

    Imported lazily to avoid circular imports (ingestion/enrichment
    bronze_loaders both import from database.py).
    """
    # Cricsheet tables
    from src.ingestion.bronze_loader import _ensure_bronze_tables

    _ensure_bronze_tables(conn)

    # ESPN enrichment tables
    from src.enrichment.bronze_loader import _ensure_espn_tables

    _ensure_espn_tables(conn)


def append_to_bronze(
    conn: duckdb.DuckDBPyConnection,
    table_name: str,
    data: pa.Table,
    id_column: str,
) -> int:
    """Idempotent append of a PyArrow table into a bronze DuckDB table.

    Uses a SQL anti-join for dedup instead of loading all existing IDs
    into Python memory. Scales to millions of rows without OOM.

    Handles schema evolution: if the incoming data has columns not yet in
    the target table, they are added via ALTER TABLE. Column matching is
    done by name, not position, so column order doesn't matter.

    All column names are double-quoted in generated SQL to prevent
    injection and handle reserved words or special characters safely.

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

    _validate_identifier(id_column, "id_column")

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
            # Schema evolution: add any new columns from incoming data
            existing_cols = {
                row[0]
                for row in conn.execute(
                    f"SELECT column_name FROM information_schema.columns "
                    f"WHERE table_name = '{table_name.split('.')[-1]}' "
                    f"AND table_schema = '{table_name.split('.')[0]}'"
                ).fetchall()
            }
            incoming_cols = data.column_names
            for col in incoming_cols:
                if col not in existing_cols:
                    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {_q(col)} VARCHAR")

            # Use explicit column list so order doesn't matter
            col_list = ", ".join(_q(c) for c in incoming_cols)
            # Prefixed column list for SELECT from the tmp table (avoids ambiguity in JOIN)
            t_col_list = ", ".join(f"t.{_q(c)}" for c in incoming_cols)
            qid = _q(id_column)

            # Count before insert
            (count_before,) = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()

            # Anti-join dedup: only insert rows not already present in target.
            # Uses LEFT JOIN (NULL-safe) instead of NOT IN (breaks if any ID is NULL).
            conn.execute(
                f"""INSERT INTO {table_name} ({col_list})
                    SELECT {t_col_list} FROM {tmp_name} t
                    LEFT JOIN {table_name} existing ON t.{qid} = existing.{qid}
                    WHERE existing.{qid} IS NULL"""
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


def upsert_to_bronze(
    conn: duckdb.DuckDBPyConnection,
    table_name: str,
    data: pa.Table,
    id_column: str,
) -> int:
    """Upsert a PyArrow table into a bronze DuckDB dimension table.

    For dimension tables (espn_players, espn_teams, espn_grounds) where
    we want the latest data to always win. Deletes existing rows that
    match on id_column, then inserts all incoming rows.

    Handles schema evolution same as append_to_bronze.
    All column names are double-quoted in generated SQL.

    Args:
        conn: An open read-write DuckDB connection.
        table_name: Fully-qualified table name (e.g. ``bronze.espn_players``).
        data: PyArrow Table to load.
        id_column: Primary key column for matching (e.g. ``espn_player_id``).

    Returns:
        Number of rows upserted (inserted or updated).
    """
    if data.num_rows == 0:
        return 0

    _validate_identifier(id_column, "id_column")

    tmp_name = "_tmp_bronze_upsert"
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
            upserted = data.num_rows
        else:
            # Schema evolution: add any new columns from incoming data
            existing_cols = {
                row[0]
                for row in conn.execute(
                    f"SELECT column_name FROM information_schema.columns "
                    f"WHERE table_name = '{table_name.split('.')[-1]}' "
                    f"AND table_schema = '{table_name.split('.')[0]}'"
                ).fetchall()
            }
            incoming_cols = data.column_names
            for col in incoming_cols:
                if col not in existing_cols:
                    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {_q(col)} VARCHAR")

            qid = _q(id_column)

            # Delete existing rows that will be replaced
            conn.execute(f"DELETE FROM {table_name} WHERE {qid} IN (SELECT {qid} FROM {tmp_name})")

            # Insert all incoming rows
            col_list = ", ".join(_q(c) for c in incoming_cols)
            src_col_list = ", ".join(_q(c) for c in incoming_cols)
            conn.execute(
                f"INSERT INTO {table_name} ({col_list}) SELECT {src_col_list} FROM {tmp_name}"
            )
            upserted = data.num_rows
    finally:
        conn.unregister(tmp_name)

    if upserted > 0:
        logger.info("bronze_upsert", table=table_name, upserted=upserted)

    return upserted
