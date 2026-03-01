"""Bowling analytics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from src.api.database import DbQuery  # noqa: TC001 — runtime dep for FastAPI DI
from src.config import settings

router = APIRouter(prefix="/api/bowling", tags=["bowling"])

_gold = settings.gold_schema


@router.get("/top")
def top_wicket_takers(
    db: DbQuery,
    season: str | None = Query(None, description="Filter by season"),
    limit: int = Query(10, ge=1, le=100),
):
    """Get top wicket takers, optionally filtered by season."""
    if season:
        return db(
            f"""
            SELECT bowler, COUNT(*) as innings,
                   SUM(wickets) as total_wickets,
                   ROUND(AVG(economy_rate), 2) as avg_economy,
                   ROUND(SUM(runs_conceded) * 1.0 / NULLIF(SUM(wickets), 0), 2) as bowling_avg
            FROM {_gold}.fact_bowling_innings
            WHERE season = $1
            GROUP BY bowler ORDER BY total_wickets DESC LIMIT $2
            """,
            [season, limit],
        )
    return db(
        f"""
        SELECT bowler, COUNT(*) as innings,
               SUM(wickets) as total_wickets,
               ROUND(AVG(economy_rate), 2) as avg_economy,
               ROUND(SUM(runs_conceded) * 1.0 / NULLIF(SUM(wickets), 0), 2) as bowling_avg
        FROM {_gold}.fact_bowling_innings
        GROUP BY bowler ORDER BY total_wickets DESC LIMIT $1
        """,
        [limit],
    )


@router.get("/stats/{player_name}")
def player_bowling_stats(player_name: str, db: DbQuery):
    """Get aggregated bowling stats for a player across all seasons."""
    return db(
        f"""
        SELECT bowler,
               COUNT(*) as innings,
               SUM(wickets) as total_wickets,
               SUM(runs_conceded) as total_runs_conceded,
               ROUND(AVG(economy_rate), 2) as avg_economy,
               ROUND(SUM(runs_conceded) * 1.0 / NULLIF(SUM(wickets), 0), 2) as bowling_avg,
               MAX(wickets) as best_wickets,
               SUM(dot_balls) as total_dot_balls,
               SUM(wides) as total_wides,
               SUM(noballs) as total_noballs
        FROM {_gold}.fact_bowling_innings
        WHERE bowler = $1
        GROUP BY bowler
        """,
        [player_name],
    )


@router.get("/season-breakdown/{player_name}")
def player_bowling_season_breakdown(player_name: str, db: DbQuery):
    """Get per-season bowling breakdown for a player."""
    return db(
        f"""
        SELECT season, COUNT(*) as innings,
               SUM(wickets) as total_wickets,
               SUM(runs_conceded) as total_runs_conceded,
               ROUND(AVG(economy_rate), 2) as avg_economy,
               MAX(wickets) as best_wickets
        FROM {_gold}.fact_bowling_innings
        WHERE bowler = $1
        GROUP BY season ORDER BY season
        """,
        [player_name],
    )
