-- Staged ESPN partnerships per innings.
-- Grain: one row per (espn_match_id, inning_number, partnership_number).
-- Extracted from bronze.espn_innings.partnerships_json.
-- NOT joined to OBT (wrong grain — one row per partnership, not per ball).
-- Returns empty result set if bronze.espn_innings doesn't exist yet.
{% if source_exists('bronze', 'espn_innings') %}
with innings as (
    select
        espn_match_id,
        inning_number,
        partnerships_json
    from {{ source('bronze', 'espn_innings') }}
    where partnerships_json is not null
      and partnerships_json != '[]'
),

unnested as (
    select
        i.espn_match_id,
        i.inning_number,
        unnest(from_json(i.partnerships_json, '["json"]')) as p,
        generate_subscripts(from_json(i.partnerships_json, '["json"]'), 1) as partnership_number
    from innings i
)

select
    espn_match_id,
    inning_number,
    partnership_number,
    try_cast(p->>'player1_id' as bigint) as player1_espn_id,
    try_cast(p->>'player1_name' as varchar) as player1_name,
    try_cast(p->>'player1_runs' as integer) as player1_runs,
    try_cast(p->>'player1_balls' as integer) as player1_balls,
    try_cast(p->>'player2_id' as bigint) as player2_espn_id,
    try_cast(p->>'player2_name' as varchar) as player2_name,
    try_cast(p->>'player2_runs' as integer) as player2_runs,
    try_cast(p->>'player2_balls' as integer) as player2_balls,
    try_cast(p->>'total_runs' as integer) as total_runs,
    try_cast(p->>'total_balls' as integer) as total_balls,
    try_cast(p->>'out_player_id' as bigint) as out_player_espn_id,
    current_timestamp as _loaded_at
from unnested
{% else %}
select
    null::bigint as espn_match_id,
    null::bigint as inning_number,
    null::bigint as partnership_number,
    null::bigint as player1_espn_id,
    null::varchar as player1_name,
    null::integer as player1_runs,
    null::integer as player1_balls,
    null::bigint as player2_espn_id,
    null::varchar as player2_name,
    null::integer as player2_runs,
    null::integer as player2_balls,
    null::integer as total_runs,
    null::integer as total_balls,
    null::bigint as out_player_espn_id,
    current_timestamp as _loaded_at
where false
{% endif %}
