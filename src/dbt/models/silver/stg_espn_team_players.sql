-- Staged ESPN team player roster per match.
-- Grain: one row per (espn_match_id, espn_team_id, espn_player_id).
-- Extracted from stg_espn_matches.teams_enrichment_json.
-- Provides per-player per-match role (captain, keeper, player).
-- Returns empty result set if bronze.espn_matches doesn't exist yet.
{% if source_exists('bronze', 'espn_matches') %}
with matches as (
    select
        espn_match_id,
        cricsheet_match_id as match_id,
        teams_enrichment_json
    from {{ source('bronze', 'espn_matches') }}
    where teams_enrichment_json is not null
      and teams_enrichment_json != '[]'
),

teams as (
    select
        m.espn_match_id,
        m.match_id,
        unnest(from_json(m.teams_enrichment_json, '["json"]')) as team
    from matches m
),

players as (
    select
        t.espn_match_id,
        t.match_id,
        try_cast(t.team->>'espn_team_id' as bigint) as espn_team_id,
        try_cast(t.team->>'team_name' as varchar) as team_name,
        try_cast(t.team->>'team_long_name' as varchar) as team_long_name,
        unnest(from_json(try_cast(t.team->>'players' as varchar), '["json"]')) as player
    from teams t
)

select
    espn_match_id,
    match_id,
    espn_team_id,
    team_name,
    team_long_name,
    try_cast(player->>'espn_player_id' as bigint) as espn_player_id,
    try_cast(player->>'player_name' as varchar) as player_name,
    try_cast(player->>'player_long_name' as varchar) as player_long_name,
    try_cast(player->>'role_code' as varchar) as role_code,
    try_cast(player->>'role' as varchar) as role,
    try_cast(player->>'is_captain' as boolean) as is_captain,
    try_cast(player->>'is_keeper' as boolean) as is_keeper,
    current_timestamp as _loaded_at
from players
{% else %}
select
    null::bigint as espn_match_id,
    null::varchar as match_id,
    null::bigint as espn_team_id,
    null::varchar as team_name,
    null::varchar as team_long_name,
    null::bigint as espn_player_id,
    null::varchar as player_name,
    null::varchar as player_long_name,
    null::varchar as role_code,
    null::varchar as role,
    null::boolean as is_captain,
    null::boolean as is_keeper,
    current_timestamp as _loaded_at
where false
{% endif %}
