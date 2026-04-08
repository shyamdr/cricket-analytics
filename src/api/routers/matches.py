"""Match endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.api.database import DbQuery  # noqa: TC001 — runtime dep for FastAPI DI
from src.tables import BATTING_INNINGS, BOWLING_INNINGS, MATCH_SUMMARY, MATCHES, VENUES

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])


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
        SELECT * FROM {MATCHES}
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
        FROM {MATCHES}
        GROUP BY season
        ORDER BY season
        """)


@router.get("/venues")
def list_venues(db: DbQuery):
    """List all venues."""
    return db(f"SELECT * FROM {VENUES} ORDER BY venue")


@router.get("/recent")
def recent_matches_with_scores(
    db: DbQuery,
    limit: int = Query(10, ge=1, le=50),
):
    """Recent matches with inline innings scores for the landing page."""
    matches = db(
        f"""
        SELECT
            m.match_id, m.season, m.match_date, m.city, m.venue,
            m.team1, m.team2, m.outcome_winner, m.match_result_type,
            m.winning_margin, m.event_name, m.event_stage, m.floodlit
        FROM {MATCHES} m
        ORDER BY m.match_date DESC
        LIMIT $1
        """,
        [limit],
    )
    if not matches:
        return []

    match_ids = [m["match_id"] for m in matches]
    placeholders = ", ".join(f"${i + 1}" for i in range(len(match_ids)))

    summaries = db(
        f"""
        SELECT match_id, innings, batting_team, total_runs, total_wickets, overs_played
        FROM {MATCH_SUMMARY}
        WHERE match_id IN ({placeholders})
        ORDER BY match_id, innings
        """,
        match_ids,
    )

    summary_map: dict[str, list] = {}
    for s in summaries:
        summary_map.setdefault(s["match_id"], []).append(s)

    for m in matches:
        m["innings"] = summary_map.get(m["match_id"], [])

    return matches


@router.get("/by-tournament")
def matches_by_tournament(
    db: DbQuery,
    days: int = Query(30, ge=1, le=365),
):
    """Recent matches grouped by tournament. Shows tournaments with activity in the last N days."""
    from datetime import date, timedelta

    cutoff = (date.today() - timedelta(days=days)).isoformat()

    matches = db(
        f"""
        SELECT
            m.match_id, m.season, m.match_date, m.city, m.venue,
            m.team1, m.team2, m.outcome_winner, m.match_result_type,
            m.winning_margin, m.event_name, m.event_stage, m.floodlit
        FROM {MATCHES} m
        WHERE m.match_date >= $1
        ORDER BY m.match_date DESC
        """,
        [cutoff],
    )

    tournaments: dict[str, list] = {}
    for m in matches:
        name = m["event_name"] or "Other"
        tournaments.setdefault(name, []).append(m)

    return [
        {"tournament": name, "matches": ms, "match_count": len(ms)}
        for name, ms in tournaments.items()
    ]


@router.get("/{match_id}")
def get_match(match_id: str, db: DbQuery):
    """Get details for a specific match."""
    rows = db(
        f"SELECT * FROM {MATCHES} WHERE match_id = $1",
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
        SELECT * FROM {MATCH_SUMMARY}
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
        SELECT * FROM {BATTING_INNINGS}
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
        SELECT * FROM {BOWLING_INNINGS}
        WHERE match_id = $1
        ORDER BY innings, wickets DESC
        """,
        [match_id],
    )
