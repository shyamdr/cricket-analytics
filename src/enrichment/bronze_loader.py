"""Load ESPN enrichment data into DuckDB bronze layer."""

from __future__ import annotations

from typing import Any

import duckdb
import pyarrow as pa
import structlog

from src.config import settings
from src.database import append_to_bronze, upsert_to_bronze, write_conn

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
    cricsheet_match_id          VARCHAR,
    mvp_player_id               BIGINT,
    mvp_player_name             VARCHAR,
    mvp_team_id                 BIGINT,
    mvp_team_name               VARCHAR,
    mvp_batted_type             VARCHAR,
    mvp_runs                    BIGINT,
    mvp_balls_faced             BIGINT,
    mvp_smart_runs              DOUBLE,
    mvp_bowled_type             VARCHAR,
    mvp_wickets                 BIGINT,
    mvp_conceded                BIGINT,
    mvp_smart_wickets           DOUBLE,
    mvp_fielded_type            VARCHAR,
    mvp_batting_impact          DOUBLE,
    mvp_bowling_impact          DOUBLE,
    mvp_total_impact            DOUBLE,
    player_of_match_json        VARCHAR,
    ground_name                 VARCHAR,
    ground_long_name            VARCHAR,
    ground_country_name         VARCHAR,
    ground_country_abbreviation VARCHAR,
    ground_image_url            VARCHAR,
    team1_abbreviation          VARCHAR,
    team2_abbreviation          VARCHAR
)
"""

_ESPN_PLAYERS_DDL = """
CREATE TABLE IF NOT EXISTS {schema}.espn_players (
    espn_player_id              BIGINT,
    player_name                 VARCHAR,
    player_long_name            VARCHAR,
    mobile_name                 VARCHAR,
    index_name                  VARCHAR,
    batting_name                VARCHAR,
    fielding_name               VARCHAR,
    slug                        VARCHAR,
    gender                      VARCHAR,
    date_of_birth_year          BIGINT,
    date_of_birth_month         BIGINT,
    date_of_birth_day           BIGINT,
    date_of_death_year          BIGINT,
    date_of_death_month         BIGINT,
    date_of_death_day           BIGINT,
    batting_styles              VARCHAR,
    bowling_styles              VARCHAR,
    long_batting_styles         VARCHAR,
    long_bowling_styles         VARCHAR,
    country_team_id             BIGINT,
    playing_roles               VARCHAR,
    player_role_type_ids        VARCHAR,
    is_overseas                 BOOLEAN,
    image_url                   VARCHAR,
    headshot_image_url          VARCHAR,
    downloaded_at               TIMESTAMP
)
"""

_ESPN_TEAMS_DDL = """
CREATE TABLE IF NOT EXISTS {schema}.espn_teams (
    espn_team_id                BIGINT,
    team_name                   VARCHAR,
    team_long_name              VARCHAR,
    team_abbreviation           VARCHAR,
    team_unofficial_name        VARCHAR,
    team_slug                   VARCHAR,
    is_country                  BOOLEAN,
    primary_color               VARCHAR,
    image_url                   VARCHAR,
    country_name                VARCHAR,
    country_abbreviation        VARCHAR,
    downloaded_at               TIMESTAMP
)
"""

_ESPN_GROUNDS_DDL = """
CREATE TABLE IF NOT EXISTS {schema}.espn_grounds (
    espn_ground_id              BIGINT,
    ground_name                 VARCHAR,
    ground_long_name            VARCHAR,
    ground_small_name           VARCHAR,
    ground_slug                 VARCHAR,
    town_name                   VARCHAR,
    town_area                   VARCHAR,
    timezone                    VARCHAR,
    country_name                VARCHAR,
    country_abbreviation        VARCHAR,
    capacity                    VARCHAR,
    image_url                   VARCHAR,
    downloaded_at               TIMESTAMP
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

_ESPN_BALL_COMMENTARY_DDL = """
CREATE TABLE IF NOT EXISTS {schema}.espn_ball_commentary (
    espn_ball_id                BIGINT,
    cricsheet_match_id          VARCHAR,
    espn_match_id               BIGINT,
    inning_number               BIGINT,
    over_number                 BIGINT,
    ball_number                 BIGINT,
    title                       VARCHAR,
    commentary_text             VARCHAR,
    pre_text                    VARCHAR,
    post_text                   VARCHAR,
    smart_stats                 VARCHAR,
    batsman_stat_text           VARCHAR,
    bowler_stat_text            VARCHAR,
    dismissal_text              VARCHAR,
    events                      VARCHAR,
    comment_images              VARCHAR,
    over_summary                VARCHAR
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
    conn.execute(_ESPN_TEAMS_DDL.format(schema=schema))
    conn.execute(_ESPN_GROUNDS_DDL.format(schema=schema))
    conn.execute(_ESPN_INNINGS_DDL.format(schema=schema))
    conn.execute(_ESPN_BALL_DATA_DDL.format(schema=schema))
    conn.execute(_ESPN_BALL_COMMENTARY_DDL.format(schema=schema))
    conn.execute(_VENUE_COORDINATES_DDL.format(schema=schema))
    conn.execute(_WEATHER_DDL.format(schema=schema))

    # Migrate existing tables: add new image columns if they don't exist yet.
    # Safe to run repeatedly — ALTER TABLE ADD COLUMN IF NOT EXISTS is idempotent.
    _migrate_image_columns(conn, schema)


def _migrate_image_columns(conn: duckdb.DuckDBPyConnection, schema: str) -> None:
    """Add image URL columns to existing ESPN tables (backward-compatible migration)."""
    migrations = [
        (f"{schema}.espn_players", "image_url", "VARCHAR"),
        (f"{schema}.espn_players", "headshot_image_url", "VARCHAR"),
        (f"{schema}.espn_matches", "team1_logo_url", "VARCHAR"),
        (f"{schema}.espn_matches", "team2_logo_url", "VARCHAR"),
        (f"{schema}.espn_matches", "venue_image_url", "VARCHAR"),
        (f"{schema}.espn_matches", "team1_long_name", "VARCHAR"),
        (f"{schema}.espn_matches", "team2_long_name", "VARCHAR"),
        (f"{schema}.espn_ball_commentary", "comment_images", "VARCHAR"),
        (f"{schema}.espn_ball_commentary", "over_summary", "VARCHAR"),
        # MVP (ESPN's "Most Valued Player of the Match" smart metrics)
        (f"{schema}.espn_matches", "mvp_player_id", "BIGINT"),
        (f"{schema}.espn_matches", "mvp_player_name", "VARCHAR"),
        (f"{schema}.espn_matches", "mvp_team_id", "BIGINT"),
        (f"{schema}.espn_matches", "mvp_team_name", "VARCHAR"),
        (f"{schema}.espn_matches", "mvp_batted_type", "VARCHAR"),
        (f"{schema}.espn_matches", "mvp_runs", "BIGINT"),
        (f"{schema}.espn_matches", "mvp_balls_faced", "BIGINT"),
        (f"{schema}.espn_matches", "mvp_smart_runs", "DOUBLE"),
        (f"{schema}.espn_matches", "mvp_bowled_type", "VARCHAR"),
        (f"{schema}.espn_matches", "mvp_wickets", "BIGINT"),
        (f"{schema}.espn_matches", "mvp_conceded", "BIGINT"),
        (f"{schema}.espn_matches", "mvp_smart_wickets", "DOUBLE"),
        (f"{schema}.espn_matches", "mvp_fielded_type", "VARCHAR"),
        (f"{schema}.espn_matches", "mvp_batting_impact", "DOUBLE"),
        (f"{schema}.espn_matches", "mvp_bowling_impact", "DOUBLE"),
        (f"{schema}.espn_matches", "mvp_total_impact", "DOUBLE"),
        # Player(s) of the Match with per-innings stats
        (f"{schema}.espn_matches", "player_of_match_json", "VARCHAR"),
        # Ground details + team abbreviations (added for OBT expansion)
        (f"{schema}.espn_matches", "ground_name", "VARCHAR"),
        (f"{schema}.espn_matches", "ground_long_name", "VARCHAR"),
        (f"{schema}.espn_matches", "ground_country_name", "VARCHAR"),
        (f"{schema}.espn_matches", "ground_country_abbreviation", "VARCHAR"),
        (f"{schema}.espn_matches", "ground_image_url", "VARCHAR"),
        (f"{schema}.espn_matches", "team1_abbreviation", "VARCHAR"),
        (f"{schema}.espn_matches", "team2_abbreviation", "VARCHAR"),
    ]
    for table, column, dtype in migrations:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {dtype}")
        except duckdb.CatalogException:
            pass  # Table doesn't exist yet — will be created by DDL above
        except Exception:
            logger.warning("migration_failed", table=table, column=column)

    # Backfill team long names from teams_enrichment_json for existing rows
    # that were scraped before the long_name columns were added.
    try:
        conn.execute(f"""
            UPDATE {schema}.espn_matches
            SET team1_long_name = json_extract_string(teams_enrichment_json::json, '$[0].team_long_name'),
                team2_long_name = json_extract_string(teams_enrichment_json::json, '$[1].team_long_name')
            WHERE team1_long_name IS NULL
              AND teams_enrichment_json IS NOT NULL
        """)
    except duckdb.CatalogException:
        pass  # Table doesn't exist yet
    except Exception:
        logger.warning("backfill_team_long_names_failed")


def load_espn_to_bronze(records: list[dict[str, Any]], refresh: bool = False) -> dict[str, int]:
    """Load ESPN enrichment records into bronze tables.

    Each record is a dict with keys: match, players, innings, balls.
    Appends to bronze.espn_matches, bronze.espn_players,
    bronze.espn_innings, and bronze.espn_ball_data.

    Args:
        records: List of enrichment dicts from match_scraper.
        refresh: If True, delete existing rows for these matches before
            inserting (use to backfill new columns on already-scraped
            matches). Default False — skip matches already in bronze.

    Returns:
        Dict with counts of new rows per table.
    """
    if not records:
        logger.info("no_espn_records_to_load")
        return {"matches": 0, "players": 0, "teams": 0, "grounds": 0, "innings": 0, "balls": 0}

    # Flatten all sub-records from each match
    match_rows = []
    player_rows = []
    team_rows = []
    ground_rows = []
    innings_rows = []
    ball_rows = []

    seen_team_ids: set[int] = set()
    seen_ground_ids: set[int] = set()
    seen_player_ids: set[int] = set()

    for rec in records:
        match_rows.append(rec["match"])
        innings_rows.extend(rec.get("innings") or [])
        ball_rows.extend(rec.get("balls") or [])

        # Dedup players across matches within this batch
        for p in rec.get("players") or []:
            pid = p.get("espn_player_id")
            if pid and pid not in seen_player_ids:
                seen_player_ids.add(pid)
                player_rows.append(p)

        # Dedup teams across matches within this batch
        for t in rec.get("teams") or []:
            tid = t.get("espn_team_id")
            if tid and tid not in seen_team_ids:
                seen_team_ids.add(tid)
                team_rows.append(t)

        # Dedup grounds across matches within this batch
        g = rec.get("ground")
        if g:
            gid = g.get("espn_ground_id")
            if gid and gid not in seen_ground_ids:
                seen_ground_ids.add(gid)
                ground_rows.append(g)

    counts: dict[str, int] = {}

    with write_conn() as conn:
        # Ensure tables exist with correct types before any data is inserted
        _ensure_espn_tables(conn)

        # Refresh mode: delete existing rows for these matches so the
        # re-scrape replaces them (instead of being skipped by dedup).
        if refresh and match_rows:
            match_ids = [
                r.get("cricsheet_match_id") for r in match_rows if r.get("cricsheet_match_id")
            ]
            espn_match_ids = [r.get("espn_match_id") for r in match_rows if r.get("espn_match_id")]
            if match_ids:
                conn.execute(
                    f"DELETE FROM {settings.bronze_schema}.espn_matches "
                    f"WHERE cricsheet_match_id IN ({','.join(['?'] * len(match_ids))})",
                    match_ids,
                )
            if espn_match_ids:
                conn.execute(
                    f"DELETE FROM {settings.bronze_schema}.espn_innings "
                    f"WHERE espn_match_id IN ({','.join(['?'] * len(espn_match_ids))})",
                    espn_match_ids,
                )
            logger.info(
                "refresh_deleted_rows",
                matches=len(match_ids),
                innings_matches=len(espn_match_ids),
            )

        if match_rows:
            table = pa.Table.from_pylist(match_rows)
            counts["matches"] = append_to_bronze(
                conn, f"{settings.bronze_schema}.espn_matches", table, "cricsheet_match_id"
            )
        else:
            counts["matches"] = 0

        if player_rows:
            # Upsert by espn_player_id — latest data wins (dimension table)
            table = pa.Table.from_pylist(player_rows)
            counts["players"] = upsert_to_bronze(
                conn, f"{settings.bronze_schema}.espn_players", table, "espn_player_id"
            )
        else:
            counts["players"] = 0

        if team_rows:
            table = pa.Table.from_pylist(team_rows)
            counts["teams"] = upsert_to_bronze(
                conn, f"{settings.bronze_schema}.espn_teams", table, "espn_team_id"
            )
        else:
            counts["teams"] = 0

        if ground_rows:
            table = pa.Table.from_pylist(ground_rows)
            counts["grounds"] = upsert_to_bronze(
                conn, f"{settings.bronze_schema}.espn_grounds", table, "espn_ground_id"
            )
        else:
            counts["grounds"] = 0

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
