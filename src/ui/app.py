"""Cricket Analytics -- Streamlit UI."""

import streamlit as st

st.set_page_config(
    page_title="Cricket Analytics",
    page_icon=None,
    layout="wide",
)

st.title("Cricket Analytics")
st.markdown("Explore cricket stats powered by DuckDB. Use the sidebar to navigate between pages.")

# Summary stats
from src.tables import (  # noqa: E402
    BATTING_INNINGS,
    BOWLING_INNINGS,
    MATCHES,
    PLAYERS,
    TEAMS,
    VENUES,
)
from src.ui.data import query  # noqa: E402

col1, col2, col3, col4 = st.columns(4)
with col1:
    n = query(f"SELECT COUNT(*) as n FROM {MATCHES}")[0]["n"]
    st.metric("Matches", f"{n:,}")
with col2:
    n = query(f"SELECT COUNT(*) as n FROM {PLAYERS}")[0]["n"]
    st.metric("Players", f"{n:,}")
with col3:
    n = query(f"SELECT COUNT(*) as n FROM {TEAMS}")[0]["n"]
    st.metric("Teams", n)
with col4:
    n = query(f"SELECT COUNT(*) as n FROM {VENUES}")[0]["n"]
    st.metric("Venues", n)

st.divider()

st.subheader("Top 10 Run Scorers (All Time)")
top_batters = query(f"""
    SELECT batter as Player, COUNT(*) as Innings,
           SUM(runs_scored) as Runs,
           ROUND(AVG(strike_rate), 2) as "Strike Rate",
           SUM(fours) as "4s", SUM(sixes) as "6s"
    FROM {BATTING_INNINGS}
    GROUP BY batter ORDER BY Runs DESC LIMIT 10
""")
st.dataframe(top_batters, use_container_width=True, hide_index=True)

st.subheader("Top 10 Wicket Takers (All Time)")
top_bowlers = query(f"""
    SELECT bowler as Player, COUNT(*) as Innings,
           SUM(wickets) as Wickets,
           ROUND(AVG(economy_rate), 2) as Economy,
           ROUND(SUM(runs_conceded) * 1.0 / NULLIF(SUM(wickets), 0), 2) as Average
    FROM {BOWLING_INNINGS}
    GROUP BY bowler ORDER BY Wickets DESC LIMIT 10
""")
st.dataframe(top_bowlers, use_container_width=True, hide_index=True)
