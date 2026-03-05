-- Staged ESPN match enrichment data.
-- Cleans types and provides a stable interface for gold layer joins.
-- Returns empty result set if bronze.espn_matches doesn't exist yet (enrichment not run).
{% if source_exists('bronze', 'espn_matches') %}
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
{% else %}
-- Source table does not exist yet — return empty with correct schema
select
    null::varchar as match_id,
    null::bigint as espn_match_id,
    null::bigint as espn_series_id,
    null::varchar as floodlit,
    null::timestamp as start_time,
    null::timestamp as end_time,
    null::varchar as hours_info,
    null::bigint as international_class_id,
    null::bigint as sub_class_id,
    null::bigint as espn_ground_id,
    null::bigint as ground_capacity,
    null::varchar as venue_timezone,
    null::varchar as team1_name,
    null::bigint as team1_espn_id,
    null::varchar as team1_captain,
    null::varchar as team1_keeper,
    null::boolean as team1_is_home,
    null::double as team1_points,
    null::varchar as team1_primary_color,
    null::varchar as team2_name,
    null::bigint as team2_espn_id,
    null::varchar as team2_captain,
    null::varchar as team2_keeper,
    null::boolean as team2_is_home,
    null::double as team2_points,
    null::varchar as team2_primary_color,
    null::varchar as replacement_players_json,
    null::varchar as debut_players_json,
    null::varchar as teams_enrichment_json,
    current_timestamp as _loaded_at
where false
{% endif %}
