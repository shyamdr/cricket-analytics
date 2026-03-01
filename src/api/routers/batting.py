"""Batting analytics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from src.api.database import query
from src.config import settings

router = APIRouter(prefix="/api/batting", tags=["batting"])

_gold = settings.gold_schema


@router.get("/top")
def top_run_scorers(
    season: str | None = Query(None, description="Filter by season"),
    limit: int = Query(10, ge=1, le=100),
):
    """Get top run scorers, optionally filtered by season."""
    if season:
        return query(
            f"""
            SELECT batter, COUNT(*) as innings,
                   SUM(runs_scored) as total_runs,
                   ROUND(AVG(strike_rate), 2) as avg_strike_rate,
                   SUM(fours) as total_fours, SUM(sixes) as total_sixes
            FROM {_gold}.fact_batting_innings
            WHERE season = $1
            GROUP BY batter ORDER BY total_runs DESC LIMIT $2
            """,
            [season, limit],
        )
    return query(
        f"""
        SELECT batter, COUNT(*) as innings,
               SUM(runs_scored) as total_runs,
               ROUND(AVG(strike_rate), 2) as avg_strike_rate,
               SUM(fours) as total_fours, SUM(sixes) as total_sixes
        FROM {_gold}.fact_batting_innings
        GROUP BY batter ORDER BY total_runs DESC LIMIT $1
        """,
        [limit],
    )


@router.get("/stats/{player_name}")
def player_batting_stats(player_name: str):
    """Get aggregated batting stats for a player across all seasons."""
    return query(
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
        FROM {_gold}.fact_batting_innings
        WHERE batter = $1
        GROUP BY batter
        """,
        [player_name],
    )


@router.get("/season-breakdown/{player_name}")
def player_season_breakdown(player_name: str):
    """Get per-season batting breakdown for a player."""
    return query(
        f"""
        SELECT season, COUNT(*) as innings,
               SUM(runs_scored) as total_runs,
               MAX(runs_scored) as highest_score,
               ROUND(AVG(strike_rate), 2) as avg_strike_rate,
               SUM(fours) as fours, SUM(sixes) as sixes
        FROM {_gold}.fact_batting_innings
        WHERE batter = $1
        GROUP BY season ORDER BY season
        """,
        [player_name],
    )
