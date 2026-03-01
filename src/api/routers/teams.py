"""Team endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.api.database import DbQuery  # noqa: TC001 — runtime dep for FastAPI DI
from src.config import settings

router = APIRouter(prefix="/api/v1/teams", tags=["teams"])

_gold = settings.gold_schema


@router.get("")
def list_teams(db: DbQuery):
    """List all IPL teams."""
    return db(f"SELECT * FROM {_gold}.dim_teams ORDER BY team_name")


@router.get("/{team_name}")
def get_team(team_name: str, db: DbQuery):
    """Get a specific team's details."""
    rows = db(
        f"SELECT * FROM {_gold}.dim_teams WHERE team_name = $1",
        [team_name],
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found")
    return rows[0]


@router.get("/{team_name}/matches")
def get_team_matches(
    team_name: str,
    db: DbQuery,
    season: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get all matches for a team, optionally filtered by season."""
    if season:
        return db(
            f"""
            SELECT * FROM {_gold}.dim_matches
            WHERE (team1 = $1 OR team2 = $1) AND season = $2
            ORDER BY match_date
            LIMIT $3 OFFSET $4
            """,
            [team_name, season, limit, offset],
        )
    return db(
        f"""
        SELECT * FROM {_gold}.dim_matches
        WHERE team1 = $1 OR team2 = $1
        ORDER BY match_date
        LIMIT $2 OFFSET $3
        """,
        [team_name, limit, offset],
    )
