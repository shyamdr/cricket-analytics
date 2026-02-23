"""Match Explorer page — browse and drill into individual matches."""

import streamlit as st

from src.ui.data import query

st.set_page_config(page_title="Match Explorer", page_icon="🏏", layout="wide")
st.title("📋 Match Explorer")

# Filters
col1, col2 = st.columns(2)
with col1:
    seasons = query("SELECT DISTINCT season FROM main_gold.dim_matches ORDER BY season")
    season_list = ["All"] + [s["season"] for s in seasons]
    selected_season = st.selectbox("Season", season_list)

with col2:
    team_filter = st.text_input("Team filter", placeholder="e.g. Mumbai Indians")

# Build query
conditions = []
params = []
idx = 1

if selected_season != "All":
    conditions.append(f"season = ${idx}")
    params.append(selected_season)
    idx += 1

if team_filter:
    conditions.append(f"(team1 ILIKE '%' || ${idx} || '%' OR team2 ILIKE '%' || ${idx} || '%')")
    params.append(team_filter)
    idx += 1

where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
params.extend([100])

matches = query(
    f"""
    SELECT match_id, season, match_date, venue, city,
           team1, team2, outcome_winner,
           outcome_by_runs, outcome_by_wickets, player_of_match
    FROM main_gold.dim_matches
    {where}
    ORDER BY match_date DESC
    LIMIT ${idx}
    """,
    params,
)

st.write(f"Showing {len(matches)} matches")
st.dataframe(matches, use_container_width=True, hide_index=True)

# Match detail
st.divider()
st.subheader("Match Detail")
match_ids = [m["match_id"] for m in matches]
selected_match = st.selectbox(
    "Select a match", match_ids, index=None, placeholder="Pick a match..."
)

if selected_match:
    # Match info
    info = query("SELECT * FROM main_gold.dim_matches WHERE match_id = $1", [selected_match])
    if info:
        m = info[0]
        st.markdown(
            f"**{m['team1']}** vs **{m['team2']}** — {m['venue']}, {m['city']} "
            f"({m['match_date']})"
        )
        if m["outcome_winner"]:
            margin = (
                f"by {m['outcome_by_runs']} runs"
                if m["outcome_by_runs"]
                else f"by {m['outcome_by_wickets']} wickets"
            )
            st.markdown(f"**Winner:** {m['outcome_winner']} {margin}")
        if m["player_of_match"]:
            st.markdown(f"**Player of the Match:** {m['player_of_match']}")

    # Batting scorecard
    st.subheader("Batting")
    batting = query(
        """
        SELECT innings as Inn, batter as Batter, batting_team as Team,
               runs_scored as Runs, balls_faced as Balls,
               fours as "4s", sixes as "6s",
               ROUND(strike_rate, 2) as SR, dismissal_kind as Dismissal
        FROM main_gold.fact_batting_innings
        WHERE match_id = $1
        ORDER BY innings, runs_scored DESC
        """,
        [selected_match],
    )
    st.dataframe(batting, use_container_width=True, hide_index=True)

    # Bowling scorecard
    st.subheader("Bowling")
    bowling = query(
        """
        SELECT innings as Inn, bowler as Bowler,
               overs_bowled as Overs, runs_conceded as Runs,
               wickets as Wkts, ROUND(economy_rate, 2) as Econ,
               dot_balls as Dots
        FROM main_gold.fact_bowling_innings
        WHERE match_id = $1
        ORDER BY innings, wickets DESC
        """,
        [selected_match],
    )
    st.dataframe(bowling, use_container_width=True, hide_index=True)
