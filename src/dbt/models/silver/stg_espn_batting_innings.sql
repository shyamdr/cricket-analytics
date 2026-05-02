-- Staged ESPN batting innings details.
-- Grain: one row per (espn_match_id, inning_number, espn_player_id).
-- Extracted from bronze.espn_innings.batsmen_details_json.
-- Batting position derived from array order (1 = opener, 11 = last).
-- Returns empty result set if bronze.espn_innings doesn't exist yet.
{% if source_exists('bronze', 'espn_innings') %}
with innings as (
    select
        espn_match_id,
        inning_number,
        batsmen_details_json
    from {{ source('bronze', 'espn_innings') }}
    where batsmen_details_json is not null
      and batsmen_details_json != '[]'
),

unnested as (
    select
        i.espn_match_id,
        i.inning_number,
        unnest(from_json(i.batsmen_details_json, '["json"]')) as batter,
        generate_subscripts(from_json(i.batsmen_details_json, '["json"]'), 1) as batting_position
    from innings i
)

select
    espn_match_id,
    inning_number,
    try_cast(batter->>'espn_player_id' as bigint) as espn_player_id,
    try_cast(batter->>'player_name' as varchar) as player_name,
    try_cast(batter->>'batted_type' as varchar) as batted_type,
    try_cast(batter->>'minutes' as integer) as minutes,
    try_cast(batter->>'dismissal_text_short' as varchar) as dismissal_text_short,
    try_cast(batter->>'dismissal_text_long' as varchar) as dismissal_text_long,
    try_cast(batter->>'dismissal_text_commentary' as varchar) as dismissal_text_commentary,
    batting_position,
    current_timestamp as _loaded_at
from unnested
{% else %}
select
    null::bigint as espn_match_id,
    null::bigint as inning_number,
    null::bigint as espn_player_id,
    null::varchar as player_name,
    null::varchar as batted_type,
    null::integer as minutes,
    null::varchar as dismissal_text_short,
    null::varchar as dismissal_text_long,
    null::varchar as dismissal_text_commentary,
    null::bigint as batting_position,
    current_timestamp as _loaded_at
where false
{% endif %}
