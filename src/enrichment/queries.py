"""Shared query functions for enrichment CLI modules.

Reads match lists from bronze (not gold) to avoid circular dependencies
in the Dagster DAG. Used by both run_match_scraper.py and run_ball_scraper.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.config import settings
from src.database import get_read_conn

if TYPE_CHECKING:
    import duckdb


def get_matches_for_season(
    season: str, conn: duckdb.DuckDBPyConnection | None = None
) -> list[dict[str, str]]:
    """Get all matches for a season from bronze.

    Derives calendar year from match date for consistent season matching.
    Includes no-result matches (rain-abandoned) since they may still have
    partial data on ESPN.
    """
    close_after = conn is None
    if conn is None:
        conn = get_read_conn()
    rows = conn.execute(
        f"""SELECT match_id,
                   CAST(date AS DATE) as match_date,
                   CAST(EXTRACT(YEAR FROM CAST(date AS DATE)) AS VARCHAR) as season
           FROM {settings.bronze_schema}.matches
           WHERE CAST(EXTRACT(YEAR FROM CAST(date AS DATE)) AS VARCHAR) = ?
           ORDER BY date""",
        [season],
    ).fetchall()
    if close_after:
        conn.close()
    return [{"match_id": r[0], "match_date": str(r[1]), "season": r[2]} for r in rows]


def get_all_matches(
    conn: duckdb.DuckDBPyConnection | None = None,
) -> list[dict[str, str]]:
    """Get all matches across all seasons from bronze."""
    close_after = conn is None
    if conn is None:
        conn = get_read_conn()
    rows = conn.execute(
        f"""SELECT match_id,
                   CAST(date AS DATE) as match_date,
                   CAST(EXTRACT(YEAR FROM CAST(date AS DATE)) AS VARCHAR) as season
           FROM {settings.bronze_schema}.matches
           ORDER BY date""",
    ).fetchall()
    if close_after:
        conn.close()
    return [{"match_id": r[0], "match_date": str(r[1]), "season": r[2]} for r in rows]


def get_matches_by_ids(
    match_ids: list[str], conn: duckdb.DuckDBPyConnection | None = None
) -> list[dict[str, str]]:
    """Get specific matches by their Cricsheet match IDs from bronze."""
    close_after = conn is None
    if conn is None:
        conn = get_read_conn()
    placeholders = ",".join(["?"] * len(match_ids))
    rows = conn.execute(
        f"""SELECT match_id,
                   CAST(date AS DATE) as match_date,
                   CAST(EXTRACT(YEAR FROM CAST(date AS DATE)) AS VARCHAR) as season
           FROM {settings.bronze_schema}.matches
           WHERE match_id IN ({placeholders})
           ORDER BY date""",
        match_ids,
    ).fetchall()
    if close_after:
        conn.close()
    return [{"match_id": r[0], "match_date": str(r[1]), "season": r[2]} for r in rows]
