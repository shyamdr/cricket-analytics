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
            m.winning_margin, m.event_name, m.event_stage, m.floodlit,
            m.toss_winner, m.toss_decision, m.player_of_match,
            m.team1_captain, m.team2_captain
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

    # Top 2 batters and bowlers per innings per match
    top_batters = db(
        f"""
        SELECT match_id, innings, batter, runs_scored, balls_faced
        FROM (
            SELECT match_id, innings, batter, runs_scored, balls_faced,
                   ROW_NUMBER() OVER (PARTITION BY match_id, innings ORDER BY runs_scored DESC, balls_faced ASC) as rn
            FROM {BATTING_INNINGS}
            WHERE match_id IN ({placeholders})
        ) ranked
        WHERE rn <= 2
        ORDER BY match_id, innings, rn
        """,
        match_ids,
    )

    top_bowlers = db(
        f"""
        SELECT match_id, innings, bowler, wickets, runs_conceded, overs_bowled
        FROM (
            SELECT match_id, innings, bowler, wickets, runs_conceded, overs_bowled,
                   ROW_NUMBER() OVER (PARTITION BY match_id, innings ORDER BY wickets DESC, runs_conceded ASC) as rn
            FROM {BOWLING_INNINGS}
            WHERE match_id IN ({placeholders})
        ) ranked
        WHERE rn <= 2
        ORDER BY match_id, innings, rn
        """,
        match_ids,
    )

    batter_map: dict[str, list] = {}
    for b in top_batters:
        batter_map.setdefault(b["match_id"], []).append(b)

    bowler_map: dict[str, list] = {}
    for b in top_bowlers:
        bowler_map.setdefault(b["match_id"], []).append(b)

    for m in matches:
        m["innings"] = summary_map.get(m["match_id"], [])
        m["top_batters"] = batter_map.get(m["match_id"], [])
        m["top_bowlers"] = bowler_map.get(m["match_id"], [])

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


@router.get("/{match_id}/playing-xi")
def get_playing_xi(match_id: str, db: DbQuery):
    """Get full playing XI for both teams with batting + bowling stats and ESPN player IDs.

    Returns players grouped by team, ordered by batting position, with
    both batting and bowling stats for each player in this match.
    """
    from src.tables import DELIVERIES_ENRICHED

    # Get team names
    match = db(f"SELECT team1, team2 FROM {MATCHES} WHERE match_id = $1", [match_id])
    if not match:
        raise HTTPException(status_code=404, detail=f"Match '{match_id}' not found")
    team1, team2 = match[0]["team1"], match[0]["team2"]

    # Get all players who participated, with batting + bowling stats
    rows = db(
        f"""
        WITH batters AS (
            SELECT
                batter as player_name,
                batting_team as team,
                batter_espn_id as espn_player_id,
                batter_batting_position as batting_position,
                batter_playing_roles as playing_role,
                batter_is_captain_this_match as is_captain,
                batter_is_keeper_this_match as is_keeper,
                sum(batter_runs) as runs_scored,
                sum(case when is_legal_delivery then 1 else 0 end) as balls_faced,
                sum(case when is_four then 1 else 0 end) as fours,
                sum(case when is_six then 1 else 0 end) as sixes,
                case when sum(case when is_legal_delivery then 1 else 0 end) > 0
                    then round(sum(batter_runs) * 100.0 / sum(case when is_legal_delivery then 1 else 0 end), 2)
                    else 0 end as strike_rate,
                max(case when is_wicket and wicket_player_out = batter then wicket_kind end) as dismissal_kind,
                max(case when is_wicket and wicket_player_out = batter then bowler end) as dismissed_by,
                max(case when is_wicket and wicket_player_out = batter then true else false end) as is_out
            FROM {DELIVERIES_ENRICHED}
            WHERE match_id = $1
            GROUP BY batter, batting_team, batter_espn_id, batter_batting_position, batter_playing_roles, batter_is_captain_this_match, batter_is_keeper_this_match
        ),
        bowlers AS (
            SELECT
                bowler as player_name,
                bowling_team as team,
                bowler_espn_id as espn_player_id,
                sum(case when is_legal_delivery then 1 else 0 end) as legal_balls,
                floor(sum(case when is_legal_delivery then 1 else 0 end) / 6)
                    + (sum(case when is_legal_delivery then 1 else 0 end) % 6) * 0.1 as overs_bowled,
                sum(batter_runs + extras_wides + extras_noballs) as runs_conceded,
                sum(case when is_wicket and wicket_kind not in ('run out', 'retired hurt', 'retired out', 'obstructing the field') then 1 else 0 end) as wickets,
                case when sum(case when is_legal_delivery then 1 else 0 end) > 0
                    then round(sum(batter_runs + extras_wides + extras_noballs) * 6.0 / sum(case when is_legal_delivery then 1 else 0 end), 2)
                    else 0 end as economy_rate,
                sum(case when is_dot_ball then 1 else 0 end) as dot_balls
            FROM {DELIVERIES_ENRICHED}
            WHERE match_id = $1
            GROUP BY bowler, bowling_team, bowler_espn_id
        )
        SELECT
            coalesce(b.player_name, bw.player_name) as player_name,
            coalesce(b.team, bw.team) as team,
            coalesce(b.espn_player_id, bw.espn_player_id) as espn_player_id,
            b.batting_position,
            b.playing_role,
            b.is_captain,
            b.is_keeper,
            b.runs_scored,
            b.balls_faced,
            b.fours,
            b.sixes,
            b.strike_rate,
            b.dismissal_kind,
            b.dismissed_by,
            b.is_out,
            bw.overs_bowled,
            bw.runs_conceded,
            bw.wickets,
            bw.economy_rate,
            bw.dot_balls
        FROM batters b
        FULL OUTER JOIN bowlers bw
            ON b.player_name = bw.player_name AND b.team = bw.team
        ORDER BY
            coalesce(b.team, bw.team),
            coalesce(b.batting_position, 99),
            coalesce(b.player_name, bw.player_name)
        """,
        [match_id],
    )

    # Split by team
    t1_players = [r for r in rows if r["team"] == team1]
    t2_players = [r for r in rows if r["team"] == team2]

    return {
        "match_id": match_id,
        "team1": {"team_name": team1, "players": t1_players},
        "team2": {"team_name": team2, "players": t2_players},
    }


@router.get("/{match_id}/highlights")
def get_match_highlights(match_id: str, db: DbQuery):
    """Get match highlights — MVP, POM, key events (dropped catches, big wickets, milestones).

    Returns structured data for building a match narrative summary.
    """
    from src.tables import DELIVERIES_ENRICHED

    match = db(
        f"SELECT team1, team2, player_of_match, outcome_winner, winning_margin FROM {MATCHES} WHERE match_id = $1",
        [match_id],
    )
    if not match:
        raise HTTPException(status_code=404, detail=f"Match '{match_id}' not found")
    m = match[0]

    # MVP data
    mvp = db(
        f"""
        SELECT DISTINCT
            match_mvp_player_name, match_mvp_total_impact,
            match_mvp_batting_impact, match_mvp_bowling_impact,
            match_mvp_smart_runs, match_mvp_smart_wickets
        FROM {DELIVERIES_ENRICHED}
        WHERE match_id = $1 AND match_mvp_player_name IS NOT NULL
        LIMIT 1
        """,
        [match_id],
    )

    # Key wickets (top 5 by impact — early wickets or big-name dismissals)
    key_wickets = db(
        f"""
        SELECT innings, over_num, ball_num, batter, bowler,
               wicket_kind, wicket_player_out, wicket_fielder1,
               commentary_text, espn_dismissal_text_commentary,
               batter_score_at_ball, team_score_at_ball, team_wickets_at_ball
        FROM {DELIVERIES_ENRICHED}
        WHERE match_id = $1 AND is_wicket = true
        ORDER BY innings, over_num, ball_num
        """,
        [match_id],
    )

    # Dropped catches
    dropped = db(
        f"""
        SELECT innings, over_num, ball_num, batter, bowler,
               dropped_catch_fielders, commentary_text,
               batter_score_at_ball, team_score_at_ball
        FROM {DELIVERIES_ENRICHED}
        WHERE match_id = $1 AND had_dropped_catch = true
        ORDER BY innings, over_num, ball_num
        """,
        [match_id],
    )

    # Top scorer per team
    top_scorers = db(
        f"""
        SELECT batting_team as team, batter, batter_espn_id as espn_player_id,
               sum(batter_runs) as runs, sum(case when is_legal_delivery then 1 else 0 end) as balls,
               sum(case when is_four then 1 else 0 end) as fours,
               sum(case when is_six then 1 else 0 end) as sixes
        FROM {DELIVERIES_ENRICHED}
        WHERE match_id = $1
        GROUP BY batting_team, batter, batter_espn_id
        QUALIFY row_number() over (partition by batting_team order by sum(batter_runs) desc) = 1
        """,
        [match_id],
    )

    # Top wicket taker per team
    top_bowlers = db(
        f"""
        SELECT bowling_team as team, bowler, bowler_espn_id as espn_player_id,
               sum(case when is_wicket and wicket_kind not in ('run out','retired hurt','retired out','obstructing the field') then 1 else 0 end) as wickets,
               sum(batter_runs + extras_wides + extras_noballs) as runs_conceded,
               floor(sum(case when is_legal_delivery then 1 else 0 end) / 6)
                   + (sum(case when is_legal_delivery then 1 else 0 end) % 6) * 0.1 as overs
        FROM {DELIVERIES_ENRICHED}
        WHERE match_id = $1
        GROUP BY bowling_team, bowler, bowler_espn_id
        QUALIFY row_number() over (partition by bowling_team order by sum(case when is_wicket and wicket_kind not in ('run out','retired hurt','retired out','obstructing the field') then 1 else 0 end) desc) = 1
        """,
        [match_id],
    )

    # Generate a smart match summary (300-500 chars, proper narrative)
    winner = m["outcome_winner"]
    margin = m["winning_margin"]
    pom = m["player_of_match"]
    loser = m["team2"] if winner == m["team1"] else m["team1"]
    ts = {s["team"]: s for s in top_scorers}
    tb = {s["team"]: s for s in top_bowlers}
    drop_count = len(dropped)

    summary_text = ""
    if winner and margin:
        winner_scorer = ts.get(winner)
        loser_scorer = ts.get(loser)
        winner_bowler = tb.get(winner)
        loser_bowler = tb.get(loser)

        parts = []

        # Opening — result + star performer
        if winner_scorer and winner_scorer["runs"] >= 50:
            sr = round(winner_scorer["runs"] * 100 / max(winner_scorer["balls"], 1))
            parts.append(
                f"{winner_scorer['batter']}'s brilliant {winner_scorer['runs']} off "
                f"{winner_scorer['balls']} balls (SR {sr}) was the highlight of the match "
                f"as {winner} beat {loser} by {margin}."
            )
        elif winner_bowler and winner_bowler["wickets"] >= 3:
            parts.append(
                f"{winner_bowler['bowler']} produced a devastating spell of "
                f"{winner_bowler['wickets']}/{winner_bowler['runs_conceded']} to lead "
                f"{winner} to a {margin} victory over {loser}."
            )
        elif pom:
            parts.append(
                f"{pom} was the star of the show as {winner} registered a comprehensive "
                f"{margin} win over {loser}."
            )
        else:
            parts.append(f"{winner} produced a clinical team effort to beat {loser} by {margin}.")

        # Middle — losing team's effort
        if loser_scorer and loser_scorer["runs"] >= 30:
            parts.append(
                f"{loser_scorer['batter']}'s fighting {loser_scorer['runs']} off "
                f"{loser_scorer['balls']} balls was the lone bright spot for {loser} "
                f"but it wasn't enough to change the outcome."
            )

        # Bowling from the other side
        if loser_bowler and loser_bowler["wickets"] >= 2 and len(" ".join(parts)) < 350:
            parts.append(
                f"{loser_bowler['bowler']} picked up {loser_bowler['wickets']} wickets "
                f"for {loser} but couldn't prevent the defeat."
            )

        # Dropped catches
        if drop_count > 0 and len(" ".join(parts)) < 400:
            parts.append(
                f"The fielding was sloppy with {drop_count} dropped "
                f"catch{'es' if drop_count > 1 else ''} that could have altered "
                f"the course of the game."
            )

        # POM mention if not already the star
        if pom and pom != (winner_scorer or {}).get("batter") and len(" ".join(parts)) < 420:
            parts.append(f"{pom} was named Player of the Match.")

        summary_text = " ".join(parts)
    else:
        summary_text = (
            "The match ended without a result after play was called off. "
            "Neither team could be separated as external factors brought "
            "an early end to the contest."
        )

    # Enforce 300-500 char range
    if len(summary_text) > 500:
        trimmed = summary_text[:500]
        last_period = trimmed.rfind(".")
        summary_text = trimmed[: last_period + 1] if last_period > 250 else trimmed[:497] + "..."

    return {
        "match_id": match_id,
        "summary_text": summary_text,
        "player_of_match": m["player_of_match"],
        "outcome_winner": m["outcome_winner"],
        "winning_margin": m["winning_margin"],
        "mvp": mvp[0] if mvp else None,
        "key_wickets": key_wickets,
        "dropped_catches": dropped,
        "top_scorers": top_scorers,
        "top_bowlers": top_bowlers,
    }
