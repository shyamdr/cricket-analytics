"""Batting analytics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from src.api.database import DbQuery  # noqa: TC001 — runtime dep for FastAPI DI
from src.tables import BATTING_INNINGS, PLAYERS

router = APIRouter(prefix="/api/v1/batting", tags=["batting"])


@router.get("/top")
def top_run_scorers(
    db: DbQuery,
    season: str | None = Query(None, description="Filter by season"),
    limit: int = Query(10, ge=1, le=100),
):
    """Get top run scorers, optionally filtered by season."""
    if season:
        return db(
            f"""
            SELECT b.batter,
                   (ARRAY_AGG(b.batting_team ORDER BY b.match_date DESC))[1] as team,
                   p.espn_player_id,
                   COUNT(*) as innings,
                   SUM(b.runs_scored) as total_runs,
                   ROUND(AVG(b.strike_rate), 2) as avg_strike_rate,
                   SUM(b.fours) as total_fours, SUM(b.sixes) as total_sixes
            FROM {BATTING_INNINGS} b
            LEFT JOIN {PLAYERS} p ON b.batter = p.player_name
            WHERE b.season = $1
            GROUP BY b.batter, p.espn_player_id ORDER BY total_runs DESC LIMIT $2
            """,
            [season, limit],
        )
    return db(
        f"""
        SELECT b.batter,
               (ARRAY_AGG(b.batting_team ORDER BY b.match_date DESC))[1] as team,
               p.espn_player_id,
               COUNT(*) as innings,
               SUM(b.runs_scored) as total_runs,
               ROUND(AVG(b.strike_rate), 2) as avg_strike_rate,
               SUM(b.fours) as total_fours, SUM(b.sixes) as total_sixes
        FROM {BATTING_INNINGS} b
        LEFT JOIN {PLAYERS} p ON b.batter = p.player_name
        GROUP BY b.batter, p.espn_player_id ORDER BY total_runs DESC LIMIT $1
        """,
        [limit],
    )


@router.get("/stats/{player_name}")
def player_batting_stats(player_name: str, db: DbQuery):
    """Get aggregated batting stats for a player across all seasons."""
    return db(
        f"""
        SELECT batter,
               COUNT(*) as innings,
               SUM(runs_scored) as total_runs,
               MAX(runs_scored) as highest_score,
               ROUND(AVG(runs_scored), 2) as avg_runs,
               ROUND(AVG(strike_rate), 2) as avg_strike_rate,
               SUM(fours) as total_fours,
               SUM(sixes) as total_sixes,
               SUM(dot_balls) as total_dot_balls,
               SUM(CASE WHEN runs_scored >= 50 AND runs_scored < 100 THEN 1 ELSE 0 END) as fifties,
               SUM(CASE WHEN runs_scored >= 100 THEN 1 ELSE 0 END) as centuries
        FROM {BATTING_INNINGS}
        WHERE batter = $1
        GROUP BY batter
        """,
        [player_name],
    )


@router.get("/season-breakdown/{player_name}")
def player_season_breakdown(player_name: str, db: DbQuery):
    """Get per-season batting breakdown for a player."""
    return db(
        f"""
        SELECT season, COUNT(*) as innings,
               SUM(runs_scored) as total_runs,
               MAX(runs_scored) as highest_score,
               ROUND(AVG(strike_rate), 2) as avg_strike_rate,
               SUM(fours) as fours, SUM(sixes) as sixes
        FROM {BATTING_INNINGS}
        WHERE batter = $1
        GROUP BY season ORDER BY season
        """,
        [player_name],
    )
