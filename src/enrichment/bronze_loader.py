"""Load ESPN enrichment data into DuckDB bronze layer."""

from __future__ import annotations

from typing import Any

import duckdb
import pyarrow as pa
import structlog

from src.config import settings
from src.database import get_write_conn

logger = structlog.get_logger(__name__)


def _get_existing_match_ids(conn: duckdb.DuckDBPyConnection) -> set[str]:
    """Get match IDs already in bronze.espn_matches (for idempotency)."""
    try:
        rows = conn.execute(
            f"SELECT cricsheet_match_id FROM {settings.bronze_schema}.espn_matches"
        ).fetchall()
        return {r[0] for r in rows}
    except duckdb.CatalogException:
        return set()


def load_espn_to_bronze(records: list[dict[str, Any]]) -> int:
    """Load ESPN enrichment records into bronze.espn_matches.

    Appends new records, skipping any match_ids already present (idempotent).
    Creates the table on first run.

    Returns:
        Number of new records inserted.
    """
    if not records:
        logger.info("no_espn_records_to_load")
        return 0

    conn = get_write_conn()
    existing = _get_existing_match_ids(conn)

    # Filter out already-loaded matches
    new_records = [r for r in records if r["cricsheet_match_id"] not in existing]
    if not new_records:
        logger.info("all_matches_already_loaded", total=len(records))
        conn.close()
        return 0

    table = pa.Table.from_pylist(new_records)

    # Create or append
    table_exists = len(existing) > 0
    if not table_exists:
        try:
            conn.execute(f"SELECT 1 FROM {settings.bronze_schema}.espn_matches LIMIT 1")
            table_exists = True
        except duckdb.CatalogException:
            table_exists = False

    if table_exists:
        conn.register("_tmp_espn", table)
        conn.execute(
            f"INSERT INTO {settings.bronze_schema}.espn_matches SELECT * FROM _tmp_espn"
        )
        conn.unregister("_tmp_espn")
    else:
        conn.register("_tmp_espn", table)
        conn.execute(
            f"CREATE TABLE {settings.bronze_schema}.espn_matches AS SELECT * FROM _tmp_espn"
        )
        conn.unregister("_tmp_espn")

    total = conn.execute(
        f"SELECT COUNT(*) FROM {settings.bronze_schema}.espn_matches"
    ).fetchone()[0]

    logger.info(
        "espn_bronze_load_complete",
        new_records=len(new_records),
        total_records=total,
    )
    conn.close()
    return len(new_records)
