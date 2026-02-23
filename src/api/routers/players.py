"""Player endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.api.database import query

router = APIRouter(prefix="/api/players", tags=["players"])


@router.get("")
def list_players(
    search: str | None = Query(None, description="Search player name (case-insensitive)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List players with optional name search."""
    if search:
        return query(
            """
            SELECT * FROM main_gold.dim_players
            WHERE player_name ILIKE '%' || $1 || '%'
            ORDER BY player_name
            LIMIT $2 OFFSET $3
            """,
            [search, limit, offset],
        )
    return query(
        "SELECT * FROM main_gold.dim_players ORDER BY player_name LIMIT $1 OFFSET $2",
        [limit, offset],
    )


@router.get("/{player_name}")
def get_player(player_name: str):
    """Get a specific player's profile."""
    rows = query(
        "SELECT * FROM main_gold.dim_players WHERE player_name = $1",
        [player_name],
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Player '{player_name}' not found")
    return rows[0]


@router.get("/{player_name}/batting")
def get_player_batting(
    player_name: str,
    season: str | None = Query(None, description="Filter by season"),
):
    """Get a player's batting innings history."""
    if season:
        return query(
            """
            SELECT * FROM main_gold.fact_batting_innings
            WHERE batter = $1 AND season = $2
            ORDER BY match_date
            """,
            [player_name, season],
        )
    return query(
        """
        SELECT * FROM main_gold.fact_batting_innings
        WHERE batter = $1
        ORDER BY match_date
        """,
        [player_name],
    )


@router.get("/{player_name}/bowling")
def get_player_bowling(
    player_name: str,
    season: str | None = Query(None, description="Filter by season"),
):
    """Get a player's bowling innings history."""
    if season:
        return query(
            """
            SELECT * FROM main_gold.fact_bowling_innings
            WHERE bowler = $1 AND season = $2
            ORDER BY match_date
            """,
            [player_name, season],
        )
    return query(
        """
        SELECT * FROM main_gold.fact_bowling_innings
        WHERE bowler = $1
        ORDER BY match_date
        """,
        [player_name],
    )
