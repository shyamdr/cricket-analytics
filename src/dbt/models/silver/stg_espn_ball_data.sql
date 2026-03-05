-- Staged ESPN per-ball spatial and prediction data.
-- Grain: one row per ball bowled. Full ball data from commentary API scraping.
-- Returns empty result set if bronze.espn_ball_data doesn't exist yet.
{% if source_exists('bronze', 'espn_ball_data') %}
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
{% else %}
select
    null::varchar as espn_ball_id,
    null::bigint as espn_match_id,
    null::varchar as match_id,
    null::integer as inning_number,
    null::integer as over_number,
    null::integer as ball_number,
    null::double as overs_actual,
    null::bigint as batsman_player_id,
    null::bigint as bowler_player_id,
    null::bigint as non_striker_player_id,
    null::integer as batsman_runs,
    null::integer as total_runs,
    null::integer as total_inning_runs,
    null::integer as total_inning_wickets,
    null::boolean as is_four,
    null::boolean as is_six,
    null::boolean as is_wicket,
    null::varchar as dismissal_type,
    null::bigint as out_player_id,
    null::integer as wides,
    null::integer as noballs,
    null::integer as byes,
    null::integer as legbyes,
    null::integer as penalties,
    null::double as wagon_x,
    null::double as wagon_y,
    null::integer as wagon_zone,
    null::varchar as pitch_line,
    null::varchar as pitch_length,
    null::varchar as shot_type,
    null::integer as shot_control,
    null::double as predicted_score,
    null::double as win_probability,
    current_timestamp as _loaded_at
where false
{% endif %}
