"""Match endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.api.database import DbQuery  # noqa: TC001 — runtime dep for FastAPI DI
from src.config import settings

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])

_gold = settings.gold_schema


@router.get("")
def list_matches(
    db: DbQuery,
    season: str | None = Query(None, description="Filter by season"),
    venue: str | None = Query(None, description="Filter by venue"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List matches with optional filters."""
    conditions = []
    params = []
    idx = 1

    if season:
        conditions.append(f"season = ${idx}")
        params.append(season)
        idx += 1
    if venue:
        conditions.append(f"venue ILIKE '%' || ${idx} || '%'")
        params.append(venue)
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.extend([limit, offset])

    return db(
        f"""
        SELECT * FROM {_gold}.dim_matches
        {where}
        ORDER BY match_date DESC
        LIMIT ${idx} OFFSET ${idx + 1}
        """,
        params,
    )


@router.get("/seasons")
def list_seasons(db: DbQuery):
    """List all available seasons with match counts."""
    return db(f"""
        SELECT season, COUNT(*) as matches
        FROM {_gold}.dim_matches
        GROUP BY season
        ORDER BY season
        """)


@router.get("/venues")
def list_venues(db: DbQuery):
    """List all venues."""
    return db(f"SELECT * FROM {_gold}.dim_venues ORDER BY venue")


@router.get("/{match_id}")
def get_match(match_id: str, db: DbQuery):
    """Get details for a specific match."""
    rows = db(
        f"SELECT * FROM {_gold}.dim_matches WHERE match_id = $1",
        [match_id],
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Match '{match_id}' not found")
    return rows[0]


@router.get("/{match_id}/summary")
def get_match_summary(match_id: str, db: DbQuery):
    """Get team-level summary for a match (both innings)."""
    return db(
        f"""
        SELECT * FROM {_gold}.fact_match_summary
        WHERE match_id = $1
        ORDER BY innings
        """,
        [match_id],
    )


@router.get("/{match_id}/batting")
def get_match_batting(match_id: str, db: DbQuery):
    """Get all batting innings for a match."""
    return db(
        f"""
        SELECT * FROM {_gold}.fact_batting_innings
        WHERE match_id = $1
        ORDER BY innings, runs_scored DESC
        """,
        [match_id],
    )


@router.get("/{match_id}/bowling")
def get_match_bowling(match_id: str, db: DbQuery):
    """Get all bowling innings for a match."""
    return db(
        f"""
        SELECT * FROM {_gold}.fact_bowling_innings
        WHERE match_id = $1
        ORDER BY innings, wickets DESC
        """,
        [match_id],
    )
