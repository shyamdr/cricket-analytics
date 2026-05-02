-- Staged ESPN series reference data.
-- Grain: one row per series_id.
-- Returns empty result set if bronze.espn_series doesn't exist yet.
{% if source_exists('bronze', 'espn_series') %}
select
    series_id,
    series_name,
    season,
    series_slug,
    discovered_from,
    created_at,
    current_timestamp as _loaded_at
from {{ source('bronze', 'espn_series') }}
{% else %}
select
    null::bigint as series_id,
    null::varchar as series_name,
    null::varchar as season,
    null::varchar as series_slug,
    null::varchar as discovered_from,
    null::timestamp as created_at,
    current_timestamp as _loaded_at
where false
{% endif %}
