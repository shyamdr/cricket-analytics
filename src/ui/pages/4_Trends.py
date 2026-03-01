"""Trends page -- scoring trends, boundary analysis, season-over-season."""

import pandas as pd
import streamlit as st

from src.config import settings
from src.ui.data import query

st.set_page_config(page_title="Trends", page_icon=None, layout="wide")
st.title("Scoring Trends")

_gold = settings.gold_schema

# Scoring trends per season
st.subheader("Average Runs Per Innings by Season")
scoring = query(f"""
    SELECT season as Season,
           ROUND(AVG(total_runs), 2) as "Avg Runs",
           ROUND(AVG(run_rate), 2) as "Avg Run Rate",
           ROUND(AVG(total_fours), 2) as "Avg 4s",
           ROUND(AVG(total_sixes), 2) as "Avg 6s"
    FROM {_gold}.fact_match_summary
    GROUP BY season ORDER BY season
""")
df_scoring = pd.DataFrame(scoring)
st.line_chart(df_scoring, x="Season", y=["Avg Runs", "Avg Run Rate"])
st.dataframe(scoring, use_container_width=True, hide_index=True)

# Boundaries per innings trend
st.subheader("Boundaries Per Innings Over the Years")
st.line_chart(df_scoring, x="Season", y=["Avg 4s", "Avg 6s"])

# Highest team totals
st.subheader("Top 10 Highest Team Totals")
highest = query(f"""
    SELECT ms.match_id, ms.season as Season, ms.batting_team as Team,
           ms.total_runs as Runs, ms.overs_played as Overs,
           ROUND(ms.run_rate, 2) as "Run Rate",
           m.venue as Venue
    FROM {_gold}.fact_match_summary ms
    JOIN {_gold}.dim_matches m ON ms.match_id = m.match_id
    ORDER BY ms.total_runs DESC
    LIMIT 10
""")
st.dataframe(highest, use_container_width=True, hide_index=True)

# Lowest team totals (completed innings)
st.subheader("Top 10 Lowest Team Totals (All Out)")
lowest = query(f"""
    SELECT ms.match_id, ms.season as Season, ms.batting_team as Team,
           ms.total_runs as Runs, ms.total_wickets as Wickets,
           ms.overs_played as Overs, m.venue as Venue
    FROM {_gold}.fact_match_summary ms
    JOIN {_gold}.dim_matches m ON ms.match_id = m.match_id
    WHERE ms.total_wickets = 10
    ORDER BY ms.total_runs ASC
    LIMIT 10
""")
st.dataframe(lowest, use_container_width=True, hide_index=True)
