"""Load raw Cricsheet data into DuckDB bronze layer.

Supports delta loading — only inserts new matches that don't already
exist in bronze. This means you can re-run ingestion for the same
dataset and it will only pick up new matches.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

import duckdb
import pyarrow as pa
import structlog

from src.config import settings

logger = structlog.get_logger(__name__)


def get_connection() -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection, creating the database file if needed."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(settings.duckdb_path))
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {settings.bronze_schema}")
    return conn


def _get_existing_match_ids(conn: duckdb.DuckDBPyConnection) -> set[str]:
    """Get match_ids already in bronze.matches."""
    try:
        rows = conn.execute(
            f"SELECT match_id FROM {settings.bronze_schema}.matches"
        ).fetchall()
        return {str(r[0]) for r in rows}
    except duckdb.CatalogException:
        return set()


def _parse_match_info(match_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Extract match-level info from a Cricsheet JSON file."""
    info = data["info"]
    meta = data["meta"]
    outcome = info.get("outcome", {})
    event = info.get("event", {})
    toss = info.get("toss", {})

    return {
        "match_id": match_id,
        "data_version": meta.get("data_version"),
        "season": str(info.get("season", "")),
        "date": info.get("dates", [None])[0],
        "city": info.get("city"),
        "venue": info.get("venue"),
        "team1": info["teams"][0] if len(info.get("teams", [])) > 0 else None,
        "team2": info["teams"][1] if len(info.get("teams", [])) > 1 else None,
        "toss_winner": toss.get("winner"),
        "toss_decision": toss.get("decision"),
        "outcome_winner": outcome.get("winner"),
        "outcome_by_runs": outcome.get("by", {}).get("runs"),
        "outcome_by_wickets": outcome.get("by", {}).get("wickets"),
        "outcome_method": outcome.get("method"),
        "outcome_result": outcome.get("result"),
        "outcome_eliminator": outcome.get("eliminator"),
        "player_of_match": info.get("player_of_match", [None])[0],
        "event_name": event.get("name"),
        "event_match_number": event.get("match_number"),
        "event_stage": event.get("stage"),
        "match_type": info.get("match_type"),
        "gender": info.get("gender"),
        "overs": info.get("overs"),
        "balls_per_over": info.get("balls_per_over"),
        "players_team1_json": json.dumps(
            info.get("players", {}).get(info["teams"][0], []) if info.get("teams") else []
        ),
        "players_team2_json": json.dumps(
            info.get("players", {}).get(info["teams"][1], [])
            if len(info.get("teams", [])) > 1
            else []
        ),
        "registry_json": json.dumps(info.get("registry", {}).get("people", {})),
    }


def _parse_deliveries(match_id: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract ball-by-ball delivery records from a Cricsheet JSON file."""
    rows: list[dict[str, Any]] = []

    for innings_idx, innings in enumerate(data.get("innings", [])):
        team = innings.get("team")
        is_super_over = innings.get("super_over", False)

        for over_obj in innings.get("overs", []):
            over_num = over_obj["over"]

            for ball_idx, delivery in enumerate(over_obj.get("deliveries", [])):
                extras = delivery.get("extras", {})
                runs = delivery.get("runs", {})
                wickets = delivery.get("wickets", [])

                wicket = wickets[0] if wickets else {}
                fielders = wicket.get("fielders", [])

                row = {
                    "match_id": match_id,
                    "innings": innings_idx + 1,
                    "batting_team": team,
                    "is_super_over": is_super_over,
                    "over_num": over_num,
                    "ball_num": ball_idx + 1,
                    "batter": delivery.get("batter"),
                    "bowler": delivery.get("bowler"),
                    "non_striker": delivery.get("non_striker"),
                    "batter_runs": runs.get("batter", 0),
                    "extras_runs": runs.get("extras", 0),
                    "total_runs": runs.get("total", 0),
                    "extras_wides": extras.get("wides"),
                    "extras_noballs": extras.get("noballs"),
                    "extras_byes": extras.get("byes"),
                    "extras_legbyes": extras.get("legbyes"),
                    "extras_penalty": extras.get("penalty"),
                    "is_wicket": len(wickets) > 0,
                    "wicket_player_out": wicket.get("player_out"),
                    "wicket_kind": wicket.get("kind"),
                    "wicket_fielder1": (
                        fielders[0].get("name") if len(fielders) > 0 else None
                    ),
                    "wicket_fielder2": (
                        fielders[1].get("name") if len(fielders) > 1 else None
                    ),
                }
                rows.append(row)

    return rows


def _ensure_tables(conn: duckdb.DuckDBPyConnection, matches_table: pa.Table, deliveries_table: pa.Table) -> bool:
    """Ensure bronze.matches and bronze.deliveries exist. Returns True if they already existed."""
    try:
        conn.execute(f"SELECT 1 FROM {settings.bronze_schema}.matches LIMIT 1")
        return True
    except duckdb.CatalogException:
        # Create from first batch — this defines the schema
        conn.register("_tmp_m", matches_table)
        conn.execute(
            f"CREATE TABLE {settings.bronze_schema}.matches AS SELECT * FROM _tmp_m WHERE 1=0"
        )
        conn.unregister("_tmp_m")

        conn.register("_tmp_d", deliveries_table)
        conn.execute(
            f"CREATE TABLE {settings.bronze_schema}.deliveries AS SELECT * FROM _tmp_d WHERE 1=0"
        )
        conn.unregister("_tmp_d")
        return False


def load_matches_to_bronze(matches_dir: Path, full_refresh: bool = False) -> int:
    """Parse match JSONs and load into bronze.matches and bronze.deliveries.

    Delta-aware: only inserts matches not already in bronze. Use
    full_refresh=True to drop and rebuild (backward compat).

    Args:
        matches_dir: Directory containing Cricsheet JSON files.
        full_refresh: If True, drops and recreates tables.

    Returns:
        Number of new matches loaded.
    """
    conn = get_connection()
    json_files = sorted(matches_dir.glob("*.json"))
    logger.info("scanning_json_files", file_count=len(json_files))

    if full_refresh:
        conn.execute(f"DROP TABLE IF EXISTS {settings.bronze_schema}.matches")
        conn.execute(f"DROP TABLE IF EXISTS {settings.bronze_schema}.deliveries")
        existing_ids: set[str] = set()
    else:
        existing_ids = _get_existing_match_ids(conn)

    if existing_ids:
        logger.info("existing_matches_in_bronze", count=len(existing_ids))

    # Parse only new matches
    new_matches: list[dict[str, Any]] = []
    new_deliveries: list[dict[str, Any]] = []
    skipped = 0

    for json_file in json_files:
        match_id = json_file.stem
        if match_id in existing_ids:
            skipped += 1
            continue

        with open(json_file) as f:
            data = json.load(f)

        new_matches.append(_parse_match_info(match_id, data))
        new_deliveries.extend(_parse_deliveries(match_id, data))

    if not new_matches:
        logger.info("no_new_matches", skipped=skipped)
        conn.close()
        return 0

    logger.info(
        "loading_new_matches",
        new=len(new_matches),
        skipped=skipped,
        deliveries=len(new_deliveries),
    )

    matches_table = pa.Table.from_pylist(new_matches)
    deliveries_table = pa.Table.from_pylist(new_deliveries) if new_deliveries else None

    _ensure_tables(conn, matches_table, deliveries_table or matches_table)

    # Append new data
    conn.register("_tmp_matches", matches_table)
    conn.execute(
        f"INSERT INTO {settings.bronze_schema}.matches SELECT * FROM _tmp_matches"
    )
    conn.unregister("_tmp_matches")

    if deliveries_table is not None:
        conn.register("_tmp_deliveries", deliveries_table)
        conn.execute(
            f"INSERT INTO {settings.bronze_schema}.deliveries SELECT * FROM _tmp_deliveries"
        )
        conn.unregister("_tmp_deliveries")

    total_matches = conn.execute(
        f"SELECT COUNT(*) FROM {settings.bronze_schema}.matches"
    ).fetchone()[0]
    total_deliveries = conn.execute(
        f"SELECT COUNT(*) FROM {settings.bronze_schema}.deliveries"
    ).fetchone()[0]

    logger.info(
        "bronze_load_complete",
        new_matches=len(new_matches),
        total_matches=total_matches,
        total_deliveries=total_deliveries,
    )
    conn.close()
    return len(new_matches)


def load_people_to_bronze(people_csv: Path) -> int:
    """Load people.csv into bronze.people (always full refresh — it's a registry)."""
    conn = get_connection()
    logger.info("loading_people_to_bronze", path=str(people_csv))

    conn.execute(f"DROP TABLE IF EXISTS {settings.bronze_schema}.people")
    conn.execute(f"""
        CREATE TABLE {settings.bronze_schema}.people AS
        SELECT * FROM read_csv_auto('{people_csv}', header=true)
        """)

    count = conn.execute(
        f"SELECT COUNT(*) FROM {settings.bronze_schema}.people"
    ).fetchone()[0]

    logger.info("people_load_complete", count=count)
    conn.close()
    return count
