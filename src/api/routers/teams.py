"""Team endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.database import query

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.get("")
def list_teams():
    """List all IPL teams."""
    return query("SELECT * FROM main_gold.dim_teams ORDER BY team_name")


@router.get("/{team_name}")
def get_team(team_name: str):
    """Get a specific team's details."""
    rows = query(
        "SELECT * FROM main_gold.dim_teams WHERE team_name = $1",
        [team_name],
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found")
    return rows[0]


@router.get("/{team_name}/matches")
def get_team_matches(team_name: str, season: str | None = None):
    """Get all matches for a team, optionally filtered by season."""
    if season:
        return query(
            """
            SELECT * FROM main_gold.dim_matches
            WHERE (team1 = $1 OR team2 = $1) AND season = $2
            ORDER BY match_date
            """,
            [team_name, season],
        )
    return query(
        """
        SELECT * FROM main_gold.dim_matches
        WHERE team1 = $1 OR team2 = $1
        ORDER BY match_date
        """,
        [team_name],
    )
