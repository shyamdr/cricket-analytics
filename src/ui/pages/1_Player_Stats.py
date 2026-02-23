"""Player Stats page — search and explore individual player performance."""

import streamlit as st

from src.ui.data import query

st.set_page_config(page_title="Player Stats", page_icon="🏏", layout="wide")
st.title("👤 Player Stats")

# Player search
players = query("SELECT player_name FROM main_gold.dim_players ORDER BY player_name")
player_names = [p["player_name"] for p in players]
selected = st.selectbox(
    "Select a player", player_names, index=None, placeholder="Type to search..."
)

if selected:
    # Career batting stats
    batting = query(
        """
        SELECT COUNT(*) as innings, SUM(runs_scored) as runs,
               MAX(runs_scored) as highest, ROUND(AVG(runs_scored), 2) as avg_runs,
               ROUND(AVG(strike_rate), 2) as strike_rate,
               SUM(fours) as fours, SUM(sixes) as sixes,
               SUM(CASE WHEN runs_scored >= 50 AND runs_scored < 100 THEN 1 ELSE 0 END) as fifties,
               SUM(CASE WHEN runs_scored >= 100 THEN 1 ELSE 0 END) as centuries
        FROM main_gold.fact_batting_innings WHERE batter = $1
        """,
        [selected],
    )

    bowling = query(
        """
        SELECT COUNT(*) as innings, SUM(wickets) as wickets,
               SUM(runs_conceded) as runs_conceded,
               ROUND(AVG(economy_rate), 2) as economy,
               ROUND(SUM(runs_conceded) * 1.0 / NULLIF(SUM(wickets), 0), 2) as avg,
               MAX(wickets) as best_wickets
        FROM main_gold.fact_bowling_innings WHERE bowler = $1
        """,
        [selected],
    )

    st.subheader("Batting Career")
    if batting and batting[0]["innings"] > 0:
        b = batting[0]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Innings", b["innings"])
        c2.metric("Runs", f"{b['runs']:,}")
        c3.metric("Highest", b["highest"])
        c4.metric("Strike Rate", b["strike_rate"])
        c5.metric("50s / 100s", f"{b['fifties']} / {b['centuries']}")
    else:
        st.info("No batting data found.")

    st.subheader("Bowling Career")
    if bowling and bowling[0]["innings"] > 0:
        bw = bowling[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Innings", bw["innings"])
        c2.metric("Wickets", bw["wickets"])
        c3.metric("Economy", bw["economy"])
        c4.metric("Best", f"{bw['best_wickets']}w")
    else:
        st.info("No bowling data found.")

    # Season breakdown
    st.subheader("Season-by-Season Batting")
    season_data = query(
        """
        SELECT season as Season, COUNT(*) as Inn,
               SUM(runs_scored) as Runs, MAX(runs_scored) as HS,
               ROUND(AVG(strike_rate), 2) as SR,
               SUM(fours) as "4s", SUM(sixes) as "6s"
        FROM main_gold.fact_batting_innings
        WHERE batter = $1
        GROUP BY season ORDER BY season
        """,
        [selected],
    )
    if season_data:
        st.dataframe(season_data, use_container_width=True, hide_index=True)

        # Runs per season chart
        import pandas as pd

        df = pd.DataFrame(season_data)
        st.bar_chart(df, x="Season", y="Runs")
