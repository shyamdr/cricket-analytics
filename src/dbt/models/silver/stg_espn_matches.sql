-- Staged ESPN match enrichment data.
-- Cleans types and provides a stable interface for gold layer joins.
select
    cricsheet_match_id as match_id,
    espn_match_id,
    espn_series_id,
    floodlit,
    cast(start_time as timestamp) as start_time,
    cast(end_time as timestamp) as end_time,
    hours_info,
    -- Classification
    international_class_id,
    sub_class_id,
    -- Venue enrichment
    espn_ground_id,
    ground_capacity,
    venue_timezone,
    -- Team 1
    team1_name,
    team1_espn_id,
    team1_captain,
    team1_keeper,
    team1_is_home,
    team1_points,
    team1_primary_color,
    -- Team 2
    team2_name,
    team2_espn_id,
    team2_captain,
    team2_keeper,
    team2_is_home,
    team2_points,
    team2_primary_color,
    -- JSON blobs
    replacement_players_json,
    debut_players_json,
    teams_enrichment_json,
    -- Audit
    current_timestamp as _loaded_at

from {{ source('bronze', 'espn_matches') }}
