
-- Staged ESPN ground/venue data.
-- One row per ground (dimension table). Keyed by espn_ground_id.
-- Returns empty result set if bronze.espn_grounds doesn't exist yet.
{% if source_exists('bronze', 'espn_grounds') %}
select
    espn_ground_id,
    ground_name,
    ground_long_name,
    ground_small_name,
    ground_slug,
    town_name,
    town_area,
    timezone,
    country_name,
    country_abbreviation,
    capacity,
    image_url,
    current_timestamp as _loaded_at
from {{ source('bronze', 'espn_grounds') }}
{% else %}
select
    null::bigint as espn_ground_id,
    null::varchar as ground_name,
    null::varchar as ground_long_name,
    null::varchar as ground_small_name,
    null::varchar as ground_slug,
    null::varchar as town_name,
    null::varchar as town_area,
    null::varchar as timezone,
    null::varchar as country_name,
    null::varchar as country_abbreviation,
    null::varchar as capacity,
    null::varchar as image_url,
    current_timestamp as _loaded_at
where false
{% endif %}
