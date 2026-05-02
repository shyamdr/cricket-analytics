"""Match analytics endpoints — player ratings, team comparison, matchups, phase breakdown."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.api.database import DbQuery  # noqa: TC001 — runtime dep for FastAPI DI
from src.tables import (
    AGG_BATTER_VS_BOWLER,
    AGG_PLAYER_RATINGS,
    AGG_TEAM_HEAD_TO_HEAD,
    DELIVERIES_ENRICHED,
    MATCHES,
)

router = APIRouter(
    prefix="/api/v1/matches/{match_id}/analytics",
    tags=["analytics"],
)


def _get_match_context(db: DbQuery, match_id: str) -> dict:
    """Fetch match metadata needed by all analytics endpoints."""
    rows = db(
        f"SELECT match_id, match_date, team1, team2, venue, season "
        f"FROM {MATCHES} WHERE match_id = $1",
        [match_id],
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Match '{match_id}' not found")
    return rows[0]


@router.get("/player-ratings")
def get_player_ratings(match_id: str, db: DbQuery):
    """Player composite ratings for all players in this match's playing XI.

    Returns one rating per player who participated in the match, with
    sub-dimension scores (experience, age, batting, bowling, form) and
    a weighted composite overall_rating (0-100). All stats are as-of
    BEFORE this match (no future data leakage).
    """
    _get_match_context(db, match_id)  # validate match exists

    return db(
        f"""
        SELECT
            player_name,
            playing_role,
            overall_rating,
            experience_score,
            age_score,
            batting_score,
            bowling_score,
            form_score,
            venue_score,
            pressure_score,
            vs_pace_score,
            vs_spin_score,
            adaptability_score,
            age_at_match,
            confidence,
            career_innings_batted_before,
            career_runs_before,
            career_batting_avg,
            career_batting_sr,
            career_innings_bowled_before,
            career_wickets_before,
            career_bowling_econ,
            career_bowling_sr
        FROM {AGG_PLAYER_RATINGS}
        WHERE as_of_match_id = $1
        ORDER BY overall_rating DESC
        """,
        [match_id],
    )


@router.get("/team-comparison")
def get_team_comparison(match_id: str, db: DbQuery):
    """Side-by-side team strength comparison for the two teams in a match.

    Returns team analytics (recent form, venue record, phase strengths)
    and historical head-to-head record.
    """
    ctx = _get_match_context(db, match_id)
    team1, team2 = ctx["team1"], ctx["team2"]
    venue = ctx["venue"]

    # Head-to-head
    h2h = db(
        f"""
        SELECT team_a, team_b, total_matches, team_a_wins, team_b_wins,
               no_results, ties, team_a_win_pct, last_5_winners
        FROM {AGG_TEAM_HEAD_TO_HEAD}
        WHERE (team_a = $1 AND team_b = $2) OR (team_a = $2 AND team_b = $1)
        """,
        [team1, team2],
    )

    # Recent form per team (last 5 matches before this one)
    def _recent_form(team: str) -> list[dict]:
        return db(
            f"""
            SELECT match_id, match_date, team1, team2, outcome_winner
            FROM {MATCHES}
            WHERE (team1 = $1 OR team2 = $1)
              AND match_date < $2
            ORDER BY match_date DESC
            LIMIT 5
            """,
            [team, ctx["match_date"]],
        )

    # Venue record per team
    def _venue_record(team: str) -> dict:
        rows = db(
            f"""
            SELECT
                count(*) as matches,
                count(*) filter (where outcome_winner = $1) as wins,
                count(*) filter (where outcome_winner is not null and outcome_winner != $1) as losses,
                count(*) filter (where outcome_result = 'no result') as no_results
            FROM {MATCHES}
            WHERE (team1 = $1 OR team2 = $1) AND venue = $2
              AND match_date < $3
            """,
            [team, venue, ctx["match_date"]],
        )
        if rows:
            r = rows[0]
            decided = r["matches"] - r["no_results"]
            r["win_percentage"] = round(r["wins"] * 100.0 / decided, 1) if decided > 0 else None
            return r
        return {"matches": 0, "wins": 0, "losses": 0, "no_results": 0, "win_percentage": None}

    # Phase stats per team (historical averages from OBT)
    def _phase_stats(team: str) -> list[dict]:
        return db(
            f"""
            SELECT
                phase,
                count(distinct match_id) as matches_sample_size,
                round(avg(total_runs) * count(*) / nullif(count(distinct match_id), 0), 1) as avg_runs,
                round(avg(case when is_wicket then 1.0 else 0.0 end) * count(*) / nullif(count(distinct match_id), 0), 1) as avg_wickets,
                round(sum(total_runs) * 6.0 / nullif(sum(case when is_legal_delivery then 1 else 0 end), 0), 2) as avg_run_rate,
                round(sum(case when is_four or is_six then 1 else 0 end) * 100.0 / nullif(sum(case when is_legal_delivery then 1 else 0 end), 0), 1) as boundary_pct,
                round(sum(case when is_dot_ball then 1 else 0 end) * 100.0 / nullif(sum(case when is_legal_delivery then 1 else 0 end), 0), 1) as dot_ball_pct
            FROM {DELIVERIES_ENRICHED}
            WHERE batting_team = $1 AND phase IS NOT NULL
              AND match_date < $2
            GROUP BY phase
            ORDER BY case phase when 'powerplay' then 1 when 'middle' then 2 when 'death' then 3 end
            """,
            [team, ctx["match_date"]],
        )

    return {
        "match_id": match_id,
        "team1": {
            "team_name": team1,
            "recent_form": _recent_form(team1),
            "venue_record": _venue_record(team1),
            "phase_stats": _phase_stats(team1),
        },
        "team2": {
            "team_name": team2,
            "recent_form": _recent_form(team2),
            "venue_record": _venue_record(team2),
            "phase_stats": _phase_stats(team2),
        },
        "head_to_head": h2h[0] if h2h else None,
    }


@router.get("/matchups")
def get_matchups(
    match_id: str,
    db: DbQuery,
    min_balls: int = Query(6, ge=1, le=100, description="Minimum balls faced to include"),
):
    """Key batter vs bowler matchups between the two playing XIs.

    Returns historical stats for cross-team batter-bowler pairs where
    the batter is from one team and the bowler from the other.
    Only includes pairs with at least `min_balls` balls faced.
    """
    _get_match_context(db, match_id)  # validate match exists

    return db(
        f"""
        WITH playing_xi AS (
            SELECT DISTINCT batter as player_name, batting_team as team
            FROM {DELIVERIES_ENRICHED}
            WHERE match_id = $1
            UNION
            SELECT DISTINCT bowler, bowling_team
            FROM {DELIVERIES_ENRICHED}
            WHERE match_id = $1
        )
        SELECT
            m.batter,
            m.bowler,
            m.balls_faced,
            m.runs_scored,
            m.dismissals,
            m.strike_rate,
            m.dot_ball_percentage,
            m.boundary_percentage,
            m.average,
            m.fours,
            m.sixes,
            m.matches,
            m.last_match_date
        FROM {AGG_BATTER_VS_BOWLER} m
        JOIN playing_xi bat ON m.batter = bat.player_name
        JOIN playing_xi bowl ON m.bowler = bowl.player_name
        WHERE bat.team != bowl.team
          AND m.balls_faced >= $2
        ORDER BY m.balls_faced DESC
        """,
        [match_id, min_balls],
    )


@router.get("/phase-comparison")
def get_phase_comparison(match_id: str, db: DbQuery):
    """Phase-wise (powerplay/middle/death) comparison for both teams and venue averages.

    Computes historical phase stats for both teams and the venue, using
    only matches played before this match (time-contextual).
    """
    ctx = _get_match_context(db, match_id)

    def _phase_query(filter_col: str, filter_val: str) -> list[dict]:
        return db(
            f"""
            SELECT
                phase,
                count(distinct match_id) as matches_sample_size,
                round(sum(total_runs) * 1.0 / nullif(count(distinct match_id), 0), 1) as avg_runs_per_match,
                round(sum(case when is_wicket then 1 else 0 end) * 1.0 / nullif(count(distinct match_id), 0), 1) as avg_wickets_per_match,
                round(sum(total_runs) * 6.0 / nullif(sum(case when is_legal_delivery then 1 else 0 end), 0), 2) as run_rate,
                round(sum(case when is_four or is_six then 1 else 0 end) * 100.0 / nullif(sum(case when is_legal_delivery then 1 else 0 end), 0), 1) as boundary_pct,
                round(sum(case when is_dot_ball then 1 else 0 end) * 100.0 / nullif(sum(case when is_legal_delivery then 1 else 0 end), 0), 1) as dot_ball_pct
            FROM {DELIVERIES_ENRICHED}
            WHERE {filter_col} = $1 AND phase IS NOT NULL
              AND match_date < $2
            GROUP BY phase
            ORDER BY case phase when 'powerplay' then 1 when 'middle' then 2 when 'death' then 3 end
            """,
            [filter_val, ctx["match_date"]],
        )

    return {
        "match_id": match_id,
        "team1": {
            "team_name": ctx["team1"],
            "phases": _phase_query("batting_team", ctx["team1"]),
        },
        "team2": {
            "team_name": ctx["team2"],
            "phases": _phase_query("batting_team", ctx["team2"]),
        },
        "venue_averages": {
            "venue": ctx["venue"],
            "phases": _phase_query("venue", ctx["venue"]),
        },
    }
