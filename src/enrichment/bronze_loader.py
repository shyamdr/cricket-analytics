"""Load ESPN enrichment data into DuckDB bronze layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import duckdb

import pyarrow as pa
import structlog

from src.config import settings
from src.database import append_to_bronze, write_conn

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Explicit ESPN bronze DDL — avoids type-inference issues from NULL-heavy
# first batches (e.g. replacement_players_json inferred as INTEGER when
# first N matches have no replacements, then fails on actual JSON strings).
# ---------------------------------------------------------------------------

_ESPN_MATCHES_DDL = """
CREATE TABLE IF NOT EXISTS {schema}.espn_matches (
    espn_match_id               BIGINT,
    espn_series_id              BIGINT,
    floodlit                    VARCHAR,
    start_date                  VARCHAR,
    start_time                  VARCHAR,
    end_time                    VARCHAR,
    hours_info                  VARCHAR,
    season                      VARCHAR,
    title                       VARCHAR,
    slug                        VARCHAR,
    status_text                 VARCHAR,
    international_class_id      INTEGER,
    sub_class_id                INTEGER,
    espn_ground_id              BIGINT,
    ground_capacity             VARCHAR,
    venue_timezone              VARCHAR,
    team1_name                  VARCHAR,
    team1_long_name             VARCHAR,
    team1_espn_id               BIGINT,
    team1_captain               VARCHAR,
    team1_keeper                VARCHAR,
    team1_is_home               BOOLEAN,
    team1_points                BIGINT,
    team1_primary_color         VARCHAR,
    team2_name                  VARCHAR,
    team2_long_name             VARCHAR,
    team2_espn_id               BIGINT,
    team2_captain               VARCHAR,
    team2_keeper                VARCHAR,
    team2_is_home               BOOLEAN,
    team2_points                BIGINT,
    team2_primary_color         VARCHAR,
    team1_logo_url              VARCHAR,
    team2_logo_url              VARCHAR,
    venue_image_url             VARCHAR,
    replacement_players_json    VARCHAR,
    debut_players_json          VARCHAR,
    teams_enrichment_json       VARCHAR,
    cricsheet_match_id          VARCHAR
)
"""

_ESPN_PLAYERS_DDL = """
CREATE TABLE IF NOT EXISTS {schema}.espn_players (
    date_of_birth_year          BIGINT,
    date_of_birth_month         BIGINT,
    date_of_birth_day           BIGINT,
    batting_styles              VARCHAR,
    bowling_styles              VARCHAR,
    long_batting_styles         VARCHAR,
    long_bowling_styles         VARCHAR,
    country_team_id             BIGINT,
    playing_roles               VARCHAR,
    espn_player_id              BIGINT,
    player_name                 VARCHAR,
    player_long_name            VARCHAR,
    is_overseas                 BOOLEAN,
    match_role_code             VARCHAR,
    team_name                   VARCHAR,
    espn_match_id               BIGINT,
    image_url                   VARCHAR,
    headshot_image_url          VARCHAR,
    _player_match_key           VARCHAR
)
"""

_ESPN_INNINGS_DDL = """
CREATE TABLE IF NOT EXISTS {schema}.espn_innings (
    espn_match_id               BIGINT,
    inning_number               BIGINT,
    batting_team                VARCHAR,
    runs_saved                  INTEGER,
    catches_dropped             INTEGER,
    batsmen_details_json        VARCHAR,
    partnerships_json           VARCHAR,
    drs_reviews_json            VARCHAR,
    over_groups_json            VARCHAR
)
"""

_ESPN_BALL_DATA_DDL = """
CREATE TABLE IF NOT EXISTS {schema}.espn_ball_data (
    cricsheet_match_id          VARCHAR,
    espn_match_id               BIGINT,
    espn_ball_id                BIGINT,
    inning_number               BIGINT,
    over_number                 BIGINT,
    ball_number                 BIGINT,
    overs_actual                DOUBLE,
    overs_unique                DOUBLE,
    batsman_player_id           BIGINT,
    bowler_player_id            BIGINT,
    non_striker_player_id       BIGINT,
    batsman_runs                BIGINT,
    total_runs                  BIGINT,
    total_inning_runs           BIGINT,
    total_inning_wickets        BIGINT,
    is_four                     BOOLEAN,
    is_six                      BOOLEAN,
    is_wicket                   BOOLEAN,
    dismissal_type              BIGINT,
    out_player_id               BIGINT,
    wides                       BIGINT,
    noballs                     BIGINT,
    byes                        BIGINT,
    legbyes                     BIGINT,
    penalties                   BIGINT,
    wagon_x                     BIGINT,
    wagon_y                     BIGINT,
    wagon_zone                  BIGINT,
    pitch_line                  VARCHAR,
    pitch_length                VARCHAR,
    shot_type                   VARCHAR,
    shot_control                BIGINT,
    timestamp                   VARCHAR,
    predicted_score             BIGINT,
    win_probability             DOUBLE
)
"""


_VENUE_COORDINATES_DDL = """
CREATE TABLE IF NOT EXISTS {schema}.venue_coordinates (
    venue               VARCHAR NOT NULL,
    city                VARCHAR,
    latitude            DOUBLE,
    longitude           DOUBLE,
    formatted_address   VARCHAR,
    place_id            VARCHAR,
    geocode_status      VARCHAR
)
"""

_WEATHER_DDL = """
CREATE TABLE IF NOT EXISTS {schema}.weather (
    match_id            VARCHAR NOT NULL,
    match_date          VARCHAR,
    latitude            DOUBLE,
    longitude           DOUBLE,
    elevation           DOUBLE,
    timezone            VARCHAR,
    utc_offset_seconds  INTEGER,
    hourly_json         VARCHAR,
    daily_json          VARCHAR,
    _loaded_at          VARCHAR,
    _run_id             VARCHAR
)
"""


def _ensure_espn_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """Create all ESPN + geocoding bronze tables with explicit schemas.

    Uses CREATE TABLE IF NOT EXISTS so it's safe to call on every run.
    This avoids DuckDB inferring wrong types from NULL-heavy first batches
    (e.g. replacement_players_json as INTEGER, timestamp as INTEGER).
    """
    schema = settings.bronze_schema
    conn.execute(_ESPN_MATCHES_DDL.format(schema=schema))
    conn.execute(_ESPN_PLAYERS_DDL.format(schema=schema))
    conn.execute(_ESPN_INNINGS_DDL.format(schema=schema))
    conn.execute(_ESPN_BALL_DATA_DDL.format(schema=schema))
    conn.execute(_VENUE_COORDINATES_DDL.format(schema=schema))
    conn.execute(_WEATHER_DDL.format(schema=schema))

    # Image enrichment table (standalone scraper)
    from src.enrichment.image_scraper import _ensure_images_table

    _ensure_images_table(conn)

    # Migrate existing tables: add new image columns if they don't exist yet.
    # Safe to run repeatedly — ALTER TABLE ADD COLUMN IF NOT EXISTS is idempotent.
    _migrate_image_columns(conn, schema)


def _migrate_image_columns(conn: duckdb.DuckDBPyConnection, schema: str) -> None:
    """Add image URL columns to existing ESPN tables (backward-compatible migration)."""
    import contextlib

    migrations = [
        (f"{schema}.espn_players", "image_url", "VARCHAR"),
        (f"{schema}.espn_players", "headshot_image_url", "VARCHAR"),
        (f"{schema}.espn_matches", "team1_logo_url", "VARCHAR"),
        (f"{schema}.espn_matches", "team2_logo_url", "VARCHAR"),
        (f"{schema}.espn_matches", "venue_image_url", "VARCHAR"),
        (f"{schema}.espn_matches", "team1_long_name", "VARCHAR"),
        (f"{schema}.espn_matches", "team2_long_name", "VARCHAR"),
    ]
    for table, column, dtype in migrations:
        with contextlib.suppress(Exception):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {dtype}")

    # Backfill team long names from teams_enrichment_json for existing rows
    # that were scraped before the long_name columns were added.
    with contextlib.suppress(Exception):
        conn.execute(f"""
            UPDATE {schema}.espn_matches
            SET team1_long_name = json_extract_string(teams_enrichment_json::json, '$[0].team_long_name'),
                team2_long_name = json_extract_string(teams_enrichment_json::json, '$[1].team_long_name')
            WHERE team1_long_name IS NULL
              AND teams_enrichment_json IS NOT NULL
        """)


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

    counts: dict[str, int] = {}

    with write_conn() as conn:
        # Ensure tables exist with correct types before any data is inserted
        _ensure_espn_tables(conn)

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
            # Composite key for dedup: one row per match per innings
            for row in innings_rows:
                row["_innings_key"] = f"{row['espn_match_id']}_{row['inning_number']}"
            table = pa.Table.from_pylist(innings_rows)
            counts["innings"] = append_to_bronze(
                conn, f"{settings.bronze_schema}.espn_innings", table, "_innings_key"
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

    logger.info(
        "espn_bronze_loaded",
        matches=counts["matches"],
        players=counts["players"],
        innings=counts["innings"],
        balls=counts["balls"],
    )
    return counts
