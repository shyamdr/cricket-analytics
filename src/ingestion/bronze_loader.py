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
from src.database import append_to_bronze, get_write_conn

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Explicit bronze DDL — avoids type-inference issues from NULL-heavy batches
# ---------------------------------------------------------------------------

_MATCHES_DDL = """
CREATE TABLE IF NOT EXISTS {schema}.matches (
    match_id            VARCHAR NOT NULL,
    data_version        VARCHAR,
    meta_created        VARCHAR,
    meta_revision       INTEGER,
    season              VARCHAR,
    date                VARCHAR,
    city                VARCHAR,
    venue               VARCHAR,
    team1               VARCHAR,
    team2               VARCHAR,
    team_type           VARCHAR,
    match_type          VARCHAR,
    match_type_number   INTEGER,
    gender              VARCHAR,
    overs               INTEGER,
    balls_per_over      INTEGER,
    toss_winner         VARCHAR,
    toss_decision       VARCHAR,
    toss_uncontested    BOOLEAN,
    outcome_winner      VARCHAR,
    outcome_by_runs     INTEGER,
    outcome_by_wickets  INTEGER,
    outcome_method      VARCHAR,
    outcome_result      VARCHAR,
    outcome_eliminator  VARCHAR,
    player_of_match     VARCHAR,
    event_name          VARCHAR,
    event_match_number  INTEGER,
    event_stage         VARCHAR,
    event_group         VARCHAR,
    officials_json      VARCHAR,
    supersubs_json      VARCHAR,
    missing_json        VARCHAR,
    players_team1_json  VARCHAR,
    players_team2_json  VARCHAR,
    registry_json       VARCHAR
)
"""

_DELIVERIES_DDL = """
CREATE TABLE IF NOT EXISTS {schema}.deliveries (
    match_id            VARCHAR NOT NULL,
    innings             INTEGER NOT NULL,
    batting_team        VARCHAR,
    is_super_over       BOOLEAN,
    over_num            INTEGER NOT NULL,
    ball_num            INTEGER NOT NULL,
    batter              VARCHAR,
    bowler              VARCHAR,
    non_striker         VARCHAR,
    batter_runs         INTEGER NOT NULL,
    extras_runs         INTEGER NOT NULL,
    total_runs          INTEGER NOT NULL,
    non_boundary        BOOLEAN,
    extras_wides        INTEGER,
    extras_noballs      INTEGER,
    extras_byes         INTEGER,
    extras_legbyes      INTEGER,
    extras_penalty      INTEGER,
    is_wicket           BOOLEAN NOT NULL,
    wicket_player_out   VARCHAR,
    wicket_kind         VARCHAR,
    wicket_fielder1     VARCHAR,
    wicket_fielder2     VARCHAR,
    review_by           VARCHAR,
    review_umpire       VARCHAR,
    review_batter       VARCHAR,
    review_decision     VARCHAR,
    review_type         VARCHAR,
    review_umpires_call BOOLEAN,
    replacements_json   VARCHAR
)
"""


def _ensure_bronze_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """Create bronze.matches and bronze.deliveries with explicit schemas.

    Uses CREATE TABLE IF NOT EXISTS so it's safe to call on every run.
    This avoids DuckDB inferring wrong types from NULL-heavy first batches.
    """
    conn.execute(_MATCHES_DDL.format(schema=settings.bronze_schema))
    conn.execute(_DELIVERIES_DDL.format(schema=settings.bronze_schema))


def _parse_match_info(match_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Extract match-level info from a Cricsheet JSON file."""
    info = data["info"]
    meta = data["meta"]
    outcome = info.get("outcome", {})
    event = info.get("event", {})
    toss = info.get("toss", {})
    teams = info.get("teams", [])

    return {
        "match_id": match_id,
        "data_version": meta.get("data_version"),
        "meta_created": meta.get("created"),
        "meta_revision": meta.get("revision"),
        "season": str(info.get("season", "")),
        "date": info.get("dates", [None])[0],
        "city": info.get("city"),
        "venue": info.get("venue"),
        "team1": teams[0] if len(teams) > 0 else None,
        "team2": teams[1] if len(teams) > 1 else None,
        "team_type": info.get("team_type"),
        "match_type": info.get("match_type"),
        "match_type_number": info.get("match_type_number"),
        "gender": info.get("gender"),
        "overs": info.get("overs"),
        "balls_per_over": info.get("balls_per_over"),
        "toss_winner": toss.get("winner"),
        "toss_decision": toss.get("decision"),
        "toss_uncontested": toss.get("uncontested"),
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
        "event_group": str(event["group"]) if "group" in event else None,
        "officials_json": json.dumps(info["officials"]) if "officials" in info else None,
        "supersubs_json": json.dumps(info["supersubs"]) if "supersubs" in info else None,
        "missing_json": json.dumps(info["missing"]) if "missing" in info else None,
        "players_team1_json": json.dumps(
            info.get("players", {}).get(teams[0], []) if teams else []
        ),
        "players_team2_json": json.dumps(
            info.get("players", {}).get(teams[1], []) if len(teams) > 1 else []
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
                review = delivery.get("review", {})
                replacements = delivery.get("replacements")

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
                    "non_boundary": runs.get("non_boundary"),
                    "extras_wides": extras.get("wides"),
                    "extras_noballs": extras.get("noballs"),
                    "extras_byes": extras.get("byes"),
                    "extras_legbyes": extras.get("legbyes"),
                    "extras_penalty": extras.get("penalty"),
                    "is_wicket": len(wickets) > 0,
                    "wicket_player_out": wicket.get("player_out"),
                    "wicket_kind": wicket.get("kind"),
                    "wicket_fielder1": (fielders[0].get("name") if len(fielders) > 0 else None),
                    "wicket_fielder2": (fielders[1].get("name") if len(fielders) > 1 else None),
                    "review_by": review.get("by") if review else None,
                    "review_umpire": review.get("umpire") if review else None,
                    "review_batter": review.get("batter") if review else None,
                    "review_decision": review.get("decision") if review else None,
                    "review_type": review.get("type") if review else None,
                    "review_umpires_call": review.get("umpires_call") if review else None,
                    "replacements_json": (json.dumps(replacements) if replacements else None),
                }
                rows.append(row)

    return rows


_BATCH_SIZE = 1000  # files per batch — keeps memory bounded for large datasets


def load_matches_to_bronze(matches_dir: Path, full_refresh: bool = False) -> int:
    """Parse match JSONs and load into bronze.matches and bronze.deliveries.

    Processes files in batches of ``_BATCH_SIZE`` to bound memory usage.
    Each batch is written atomically (BEGIN/COMMIT). Delta-aware: only
    inserts matches not already in bronze. Use full_refresh=True to drop
    and rebuild.

    Args:
        matches_dir: Directory containing Cricsheet JSON files.
        full_refresh: If True, drops and recreates tables.

    Returns:
        Number of new matches loaded.
    """
    conn = get_write_conn()
    matches_table_name = f"{settings.bronze_schema}.matches"
    deliveries_table_name = f"{settings.bronze_schema}.deliveries"

    json_files = sorted(matches_dir.glob("*.json"))
    logger.info("scanning_json_files", file_count=len(json_files))

    if full_refresh:
        conn.execute(f"DROP TABLE IF EXISTS {matches_table_name}")
        conn.execute(f"DROP TABLE IF EXISTS {deliveries_table_name}")

    # Ensure tables exist with correct schema (idempotent)
    _ensure_bronze_tables(conn)

    if not json_files:
        logger.info("no_json_files_found")
        conn.close()
        return 0

    total_new = 0
    num_batches = (len(json_files) + _BATCH_SIZE - 1) // _BATCH_SIZE

    for batch_idx in range(num_batches):
        start = batch_idx * _BATCH_SIZE
        batch_files = json_files[start : start + _BATCH_SIZE]

        batch_matches: list[dict[str, Any]] = []
        batch_deliveries: list[dict[str, Any]] = []

        for json_file in batch_files:
            match_id = json_file.stem
            with open(json_file) as f:
                data = json.load(f)
            batch_matches.append(_parse_match_info(match_id, data))
            batch_deliveries.extend(_parse_deliveries(match_id, data))

        if not batch_matches:
            continue

        matches_pa = pa.Table.from_pylist(batch_matches)
        deliveries_pa = pa.Table.from_pylist(batch_deliveries) if batch_deliveries else None

        # Atomic write: both matches + deliveries succeed or neither does
        conn.execute("BEGIN TRANSACTION")
        try:
            new_matches = append_to_bronze(conn, matches_table_name, matches_pa, "match_id")

            if deliveries_pa is not None and new_matches > 0:
                append_to_bronze(conn, deliveries_table_name, deliveries_pa, "match_id")

            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            conn.close()
            raise

        total_new += new_matches
        if num_batches > 1:
            logger.info(
                "batch_complete",
                batch=batch_idx + 1,
                of=num_batches,
                new_matches=new_matches,
            )

    total_matches = conn.execute(f"SELECT COUNT(*) FROM {matches_table_name}").fetchone()[0]
    total_deliveries = conn.execute(f"SELECT COUNT(*) FROM {deliveries_table_name}").fetchone()[0]

    logger.info(
        "bronze_load_complete",
        new_matches=total_new,
        total_matches=total_matches,
        total_deliveries=total_deliveries,
    )
    conn.close()
    return total_new


def load_people_to_bronze(people_csv: Path) -> int:
    """Load people.csv into bronze.people (always full refresh — it's a registry)."""
    conn = get_write_conn()
    logger.info("loading_people_to_bronze", path=str(people_csv))

    # Atomic swap: drop + recreate in a single transaction
    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute(f"DROP TABLE IF EXISTS {settings.bronze_schema}.people")
        conn.execute(f"""
            CREATE TABLE {settings.bronze_schema}.people AS
            SELECT * FROM read_csv_auto('{people_csv}', header=true)
            """)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        conn.close()
        raise

    count = conn.execute(f"SELECT COUNT(*) FROM {settings.bronze_schema}.people").fetchone()[0]

    logger.info("people_load_complete", count=count)
    conn.close()
    return count
