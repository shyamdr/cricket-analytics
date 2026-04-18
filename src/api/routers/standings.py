"""Points table / standings endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Query

from src.api.database import DbQuery  # noqa: TC001 — runtime dep for FastAPI DI
from src.tables import MATCH_SUMMARY, MATCHES

router = APIRouter(prefix="/api/v1/standings", tags=["standings"])


@router.get("")
def get_standings(
    db: DbQuery,
    season: str = Query(..., description="Season to get standings for"),
):
    """Get points table for a season.

    Returns team standings with matches played, won, lost, no result,
    points (2 per win, 1 per NR), and net run rate.
    Only returns data if the season has more than 2 teams.
    """
    standings = db(
        f"""
        WITH team_matches AS (
            SELECT team1 as team, match_id, outcome_winner, match_result_type
            FROM {MATCHES} WHERE season = $1
            UNION ALL
            SELECT team2 as team, match_id, outcome_winner, match_result_type
            FROM {MATCHES} WHERE season = $1
        ),
        team_stats AS (
            SELECT team,
                   COUNT(*) as played,
                   SUM(CASE WHEN outcome_winner = team THEN 1 ELSE 0 END) as won,
                   SUM(CASE WHEN outcome_winner IS NOT NULL AND outcome_winner != team THEN 1 ELSE 0 END) as lost,
                   SUM(CASE WHEN match_result_type = 'no_result' THEN 1 ELSE 0 END) as nr
            FROM team_matches
            GROUP BY team
        ),
        team_batting AS (
            SELECT batting_team as team,
                   SUM(total_runs) as runs_for,
                   SUM(overs_played) as overs_faced
            FROM {MATCH_SUMMARY}
            WHERE season = $1
            GROUP BY batting_team
        ),
        team_bowling AS (
            SELECT
                CASE WHEN ms.batting_team = m.team1 THEN m.team2 ELSE m.team1 END as team,
                SUM(ms.total_runs) as runs_against,
                SUM(ms.overs_played) as overs_bowled
            FROM {MATCH_SUMMARY} ms
            JOIN {MATCHES} m ON ms.match_id = m.match_id
            WHERE ms.season = $1
            GROUP BY team
        )
        SELECT ts.team,
               ts.played,
               ts.won,
               ts.lost,
               ts.nr,
               (ts.won * 2 + ts.nr) as points,
               ROUND(
                 (tb.runs_for * 1.0 / NULLIF(tb.overs_faced, 0))
                 - (bo.runs_against * 1.0 / NULLIF(bo.overs_bowled, 0)),
                 3
               ) as nrr
        FROM team_stats ts
        LEFT JOIN team_batting tb ON ts.team = tb.team
        LEFT JOIN team_bowling bo ON ts.team = bo.team
        ORDER BY points DESC, nrr DESC
        """,
        [season],
    )

    # Only return if more than 2 teams (not a bilateral series)
    if len(standings) <= 2:
        return []

    return standings
