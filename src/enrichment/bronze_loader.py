"""Load ESPN enrichment data into DuckDB bronze layer."""

from __future__ import annotations

from typing import Any

import pyarrow as pa
import structlog

from src.config import settings
from src.database import append_to_bronze, get_write_conn

logger = structlog.get_logger(__name__)


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
    table = pa.Table.from_pylist(records)
    new_count = append_to_bronze(
        conn, f"{settings.bronze_schema}.espn_matches", table, "cricsheet_match_id"
    )

    if new_count == 0:
        logger.info("all_espn_matches_already_loaded", total=len(records))

    conn.close()
    return new_count
