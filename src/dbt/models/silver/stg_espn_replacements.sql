-- Staged ESPN replacement (impact) players per match.
-- Grain: one row per (espn_match_id, inning, over_decimal, player_in_id).
-- Extracted from stg_espn_matches.replacement_players_json.
-- Returns empty result set if bronze.espn_matches doesn't exist yet.
{% if source_exists('bronze', 'espn_matches') %}
with matches as (
    select
        espn_match_id,
        cricsheet_match_id as match_id,
        replacement_players_json
    from {{ source('bronze', 'espn_matches') }}
    where replacement_players_json is not null
      and replacement_players_json != '[]'
),

unnested as (
    select
        m.espn_match_id,
        m.match_id,
        unnest(from_json(m.replacement_players_json, '["json"]')) as rep
    from matches m
)

select
    espn_match_id,
    match_id,
    try_cast(rep->>'player_in_id' as bigint) as player_in_espn_id,
    try_cast(rep->>'player_in_name' as varchar) as player_in_name,
    try_cast(rep->>'player_out_id' as bigint) as player_out_espn_id,
    try_cast(rep->>'player_out_name' as varchar) as player_out_name,
    try_cast(rep->>'team' as varchar) as team_name,
    try_cast(rep->>'inning' as integer) as inning_number,
    try_cast(rep->>'over' as double) as over_decimal,
    try_cast(rep->>'replacement_type' as integer) as replacement_type_code,
    current_timestamp as _loaded_at
from unnested
{% else %}
select
    null::bigint as espn_match_id,
    null::varchar as match_id,
    null::bigint as player_in_espn_id,
    null::varchar as player_in_name,
    null::bigint as player_out_espn_id,
    null::varchar as player_out_name,
    null::varchar as team_name,
    null::integer as inning_number,
    null::double as over_decimal,
    null::integer as replacement_type_code,
    current_timestamp as _loaded_at
where false
{% endif %}
