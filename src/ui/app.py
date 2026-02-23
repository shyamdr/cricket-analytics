"""Cricket Analytics — Streamlit UI."""

import streamlit as st

st.set_page_config(
    page_title="Cricket Analytics",
    page_icon="🏏",
    layout="wide",
)

st.title("🏏 IPL Cricket Analytics")
st.markdown("Explore IPL stats powered by DuckDB. " "Use the sidebar to navigate between pages.")

# Summary stats
from src.ui.data import query  # noqa: E402

col1, col2, col3, col4 = st.columns(4)
with col1:
    n = query("SELECT COUNT(*) as n FROM main_gold.dim_matches")[0]["n"]
    st.metric("Matches", f"{n:,}")
with col2:
    n = query("SELECT COUNT(*) as n FROM main_gold.dim_players")[0]["n"]
    st.metric("Players", f"{n:,}")
with col3:
    n = query("SELECT COUNT(*) as n FROM main_gold.dim_teams")[0]["n"]
    st.metric("Teams", n)
with col4:
    n = query("SELECT COUNT(*) as n FROM main_gold.dim_venues")[0]["n"]
    st.metric("Venues", n)

st.divider()

st.subheader("Top 10 Run Scorers (All Time)")
top_batters = query("""
    SELECT batter as Player, COUNT(*) as Innings,
           SUM(runs_scored) as Runs,
           ROUND(AVG(strike_rate), 2) as "Strike Rate",
           SUM(fours) as "4s", SUM(sixes) as "6s"
    FROM main_gold.fact_batting_innings
    GROUP BY batter ORDER BY Runs DESC LIMIT 10
""")
st.dataframe(top_batters, use_container_width=True, hide_index=True)

st.subheader("Top 10 Wicket Takers (All Time)")
top_bowlers = query("""
    SELECT bowler as Player, COUNT(*) as Innings,
           SUM(wickets) as Wickets,
           ROUND(AVG(economy_rate), 2) as Economy,
           ROUND(SUM(runs_conceded) * 1.0 / NULLIF(SUM(wickets), 0), 2) as Average
    FROM main_gold.fact_bowling_innings
    GROUP BY bowler ORDER BY Wickets DESC LIMIT 10
""")
st.dataframe(top_bowlers, use_container_width=True, hide_index=True)
