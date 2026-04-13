
-- Staged ESPN team data.
-- One row per team (dimension table). Keyed by espn_team_id.
-- Returns empty result set if bronze.espn_teams doesn't exist yet.
{% if source_exists('bronze', 'espn_teams') %}
select
    espn_team_id,
    team_name,
    team_long_name,
    team_abbreviation,
    team_unofficial_name,
    team_slug,
    is_country,
    primary_color,
    image_url,
    country_name,
    country_abbreviation,
    current_timestamp as _loaded_at
from {{ source('bronze', 'espn_teams') }}
{% else %}
select
    null::bigint as espn_team_id,
    null::varchar as team_name,
    null::varchar as team_long_name,
    null::varchar as team_abbreviation,
    null::varchar as team_unofficial_name,
    null::varchar as team_slug,
    null::boolean as is_country,
    null::varchar as primary_color,
    null::varchar as image_url,
    null::varchar as country_name,
    null::varchar as country_abbreviation,
    current_timestamp as _loaded_at
where false
{% endif %}
