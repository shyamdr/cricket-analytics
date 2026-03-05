-- Staged ESPN per-ball spatial and prediction data.
-- Grain: one row per ball bowled. Full ball data from commentary API scraping.
-- Joins to Cricsheet deliveries via cricsheet_match_id + over + ball.
select
    espn_ball_id,
    espn_match_id,
    cricsheet_match_id as match_id,
    inning_number,
    over_number,
    ball_number,
    overs_actual,
    -- Player IDs (ESPN)
    batsman_player_id,
    bowler_player_id,
    non_striker_player_id,
    -- Runs (redundant with Cricsheet but useful for validation)
    batsman_runs,
    total_runs,
    total_inning_runs,
    total_inning_wickets,
    -- Events
    is_four,
    is_six,
    is_wicket,
    dismissal_type,
    out_player_id,
    -- Extras
    wides,
    noballs,
    byes,
    legbyes,
    penalties,
    -- Spatial / shot data (unique to ESPN — the gold mine)
    wagon_x,
    wagon_y,
    wagon_zone,
    pitch_line,
    pitch_length,
    shot_type,
    shot_control,
    -- Predictions
    predicted_score,
    win_probability,
    -- Audit
    current_timestamp as _loaded_at

from {{ source('bronze', 'espn_ball_data') }}
