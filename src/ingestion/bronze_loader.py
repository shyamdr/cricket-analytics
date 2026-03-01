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

import pyarrow as pa
import structlog

from src.config import settings
from src.database import append_to_bronze, get_write_conn

logger = structlog.get_logger(__name__)


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
                    "wicket_fielder1": (fielders[0].get("name") if len(fielders) > 0 else None),
                    "wicket_fielder2": (fielders[1].get("name") if len(fielders) > 1 else None),
                }
                rows.append(row)

    return rows


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
    conn = get_write_conn()
    matches_table_name = f"{settings.bronze_schema}.matches"
    deliveries_table_name = f"{settings.bronze_schema}.deliveries"

    json_files = sorted(matches_dir.glob("*.json"))
    logger.info("scanning_json_files", file_count=len(json_files))

    if full_refresh:
        conn.execute(f"DROP TABLE IF EXISTS {matches_table_name}")
        conn.execute(f"DROP TABLE IF EXISTS {deliveries_table_name}")

    # Parse all JSON files into lists
    all_matches: list[dict[str, Any]] = []
    all_deliveries: list[dict[str, Any]] = []

    for json_file in json_files:
        match_id = json_file.stem
        with open(json_file) as f:
            data = json.load(f)
        all_matches.append(_parse_match_info(match_id, data))
        all_deliveries.extend(_parse_deliveries(match_id, data))

    if not all_matches:
        logger.info("no_json_files_found")
        conn.close()
        return 0

    matches_pa = pa.Table.from_pylist(all_matches)
    deliveries_pa = pa.Table.from_pylist(all_deliveries) if all_deliveries else None

    # Dedup + append via shared utility
    new_matches = append_to_bronze(conn, matches_table_name, matches_pa, "match_id")

    if deliveries_pa is not None and new_matches > 0:
        append_to_bronze(conn, deliveries_table_name, deliveries_pa, "match_id")

    total_matches = conn.execute(f"SELECT COUNT(*) FROM {matches_table_name}").fetchone()[0]
    total_deliveries = conn.execute(f"SELECT COUNT(*) FROM {deliveries_table_name}").fetchone()[0]

    logger.info(
        "bronze_load_complete",
        new_matches=new_matches,
        total_matches=total_matches,
        total_deliveries=total_deliveries,
    )
    conn.close()
    return new_matches


def load_people_to_bronze(people_csv: Path) -> int:
    """Load people.csv into bronze.people (always full refresh — it's a registry)."""
    conn = get_write_conn()
    logger.info("loading_people_to_bronze", path=str(people_csv))

    conn.execute(f"DROP TABLE IF EXISTS {settings.bronze_schema}.people")
    conn.execute(f"""
        CREATE TABLE {settings.bronze_schema}.people AS
        SELECT * FROM read_csv_auto('{people_csv}', header=true)
        """)

    count = conn.execute(f"SELECT COUNT(*) FROM {settings.bronze_schema}.people").fetchone()[0]

    logger.info("people_load_complete", count=count)
    conn.close()
    return count
