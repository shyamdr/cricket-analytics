"""Team Analytics page — team records, head-to-head, season performance."""

import streamlit as st

from src.ui.data import query

st.set_page_config(page_title="Team Analytics", page_icon="🏏", layout="wide")
st.title("🏆 Team Analytics")

teams = query("SELECT team_name FROM main_gold.dim_teams ORDER BY team_name")
team_names = [t["team_name"] for t in teams]
selected = st.selectbox("Select a team", team_names, index=None, placeholder="Choose a team...")

if selected:
    # Win/loss record
    record = query(
        """
        SELECT
            COUNT(*) as total_matches,
            SUM(CASE WHEN outcome_winner = $1 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome_winner IS NOT NULL AND outcome_winner != $1 THEN 1 ELSE 0 END) as losses,
            SUM(CASE WHEN outcome_result = 'no result' THEN 1 ELSE 0 END) as no_results
        FROM main_gold.dim_matches
        WHERE team1 = $1 OR team2 = $1
        """,
        [selected],
    )

    if record:
        r = record[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Matches", r["total_matches"])
        c2.metric("Wins", r["wins"])
        c3.metric("Losses", r["losses"])
        c4.metric("Win %", f"{round(r['wins'] * 100 / max(r['total_matches'], 1), 1)}%")

    # Season-wise performance
    st.subheader("Season Performance")
    seasons = query(
        """
        SELECT season as Season,
               COUNT(*) as Played,
               SUM(CASE WHEN outcome_winner = $1 THEN 1 ELSE 0 END) as Won,
               SUM(CASE WHEN outcome_winner IS NOT NULL AND outcome_winner != $1 THEN 1 ELSE 0 END) as Lost
        FROM main_gold.dim_matches
        WHERE team1 = $1 OR team2 = $1
        GROUP BY season ORDER BY season
        """,
        [selected],
    )
    if seasons:
        st.dataframe(seasons, use_container_width=True, hide_index=True)

        import pandas as pd

        df = pd.DataFrame(seasons)
        st.bar_chart(df, x="Season", y=["Won", "Lost"])

    # Head-to-head
    st.subheader("Head-to-Head Record")
    h2h = query(
        """
        SELECT
            CASE WHEN team1 = $1 THEN team2 ELSE team1 END as Opponent,
            COUNT(*) as Played,
            SUM(CASE WHEN outcome_winner = $1 THEN 1 ELSE 0 END) as Won,
            SUM(CASE WHEN outcome_winner IS NOT NULL AND outcome_winner != $1 THEN 1 ELSE 0 END) as Lost
        FROM main_gold.dim_matches
        WHERE team1 = $1 OR team2 = $1
        GROUP BY Opponent
        ORDER BY Played DESC
        """,
        [selected],
    )
    if h2h:
        st.dataframe(h2h, use_container_width=True, hide_index=True)
