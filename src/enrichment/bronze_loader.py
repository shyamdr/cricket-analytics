"""Load ESPN enrichment data into DuckDB bronze layer."""

from __future__ import annotations

from typing import Any

import pyarrow as pa
import structlog

from src.config import settings
from src.database import append_to_bronze, get_write_conn

logger = structlog.get_logger(__name__)


def load_espn_to_bronze(records: list[dict[str, Any]]) -> dict[str, int]:
    """Load ESPN enrichment records into bronze tables.

    Each record is a dict with keys: match, players, innings, balls.
    Appends to bronze.espn_matches, bronze.espn_players,
    bronze.espn_innings, and bronze.espn_ball_data.

    Returns:
        Dict with counts of new rows per table.
    """
    if not records:
        logger.info("no_espn_records_to_load")
        return {"matches": 0, "players": 0, "innings": 0, "balls": 0}

    # Flatten all sub-records from each match
    match_rows = []
    player_rows = []
    innings_rows = []
    ball_rows = []

    for rec in records:
        match_rows.append(rec["match"])
        player_rows.extend(rec.get("players") or [])
        innings_rows.extend(rec.get("innings") or [])
        ball_rows.extend(rec.get("balls") or [])

    conn = get_write_conn()
    counts = {}

    try:
        if match_rows:
            table = pa.Table.from_pylist(match_rows)
            counts["matches"] = append_to_bronze(
                conn, f"{settings.bronze_schema}.espn_matches", table, "cricsheet_match_id"
            )
        else:
            counts["matches"] = 0

        if player_rows:
            # Add composite key for dedup: player appears in multiple matches
            # but bio data is the same — we want one row per player per match
            for row in player_rows:
                row["_player_match_key"] = f"{row['espn_player_id']}_{row['espn_match_id']}"
            table = pa.Table.from_pylist(player_rows)
            counts["players"] = append_to_bronze(
                conn, f"{settings.bronze_schema}.espn_players", table, "_player_match_key"
            )
        else:
            counts["players"] = 0

        if innings_rows:
            table = pa.Table.from_pylist(innings_rows)
            # Composite key: match + inning number — use match_id for dedup
            # (append_to_bronze dedup is on single column, so we use espn_match_id
            # and accept that re-scraping a match appends duplicate innings.
            # In practice, matches are only scraped once due to the already_scraped check.)
            counts["innings"] = append_to_bronze(
                conn, f"{settings.bronze_schema}.espn_innings", table, "espn_match_id"
            )
        else:
            counts["innings"] = 0

        if ball_rows:
            table = pa.Table.from_pylist(ball_rows)
            counts["balls"] = append_to_bronze(
                conn, f"{settings.bronze_schema}.espn_ball_data", table, "espn_ball_id"
            )
        else:
            counts["balls"] = 0
    finally:
        conn.close()

    logger.info(
        "espn_bronze_loaded",
        matches=counts["matches"],
        players=counts["players"],
        innings=counts["innings"],
        balls=counts["balls"],
    )
    return counts
