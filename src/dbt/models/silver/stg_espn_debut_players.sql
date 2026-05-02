-- Staged ESPN debut players per match.
-- Grain: one row per (espn_match_id, espn_player_id).
-- Extracted from stg_espn_matches.debut_players_json.
-- Returns empty result set if bronze.espn_matches doesn't exist yet.
{% if source_exists('bronze', 'espn_matches') %}
with matches as (
    select
        espn_match_id,
        cricsheet_match_id as match_id,
        debut_players_json
    from {{ source('bronze', 'espn_matches') }}
    where debut_players_json is not null
      and debut_players_json != '[]'
),

unnested as (
    select
        m.espn_match_id,
        m.match_id,
        unnest(from_json(m.debut_players_json, '["json"]')) as entry
    from matches m
)

select
    espn_match_id,
    match_id,
    try_cast(entry->'player'->>'id' as bigint) as espn_player_id,
    try_cast(entry->'player'->>'name' as varchar) as player_name,
    try_cast(entry->'player'->>'longName' as varchar) as player_long_name,
    try_cast(entry->'team'->>'id' as bigint) as espn_team_id,
    try_cast(entry->'team'->>'name' as varchar) as team_name,
    try_cast(entry->>'classId' as bigint) as class_id,
    current_timestamp as _loaded_at
from unnested
{% else %}
select
    null::bigint as espn_match_id,
    null::varchar as match_id,
    null::bigint as espn_player_id,
    null::varchar as player_name,
    null::varchar as player_long_name,
    null::bigint as espn_team_id,
    null::varchar as team_name,
    null::bigint as class_id,
    current_timestamp as _loaded_at
where false
{% endif %}
