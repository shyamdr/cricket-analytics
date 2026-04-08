
-- Staged ESPN image URLs for players, teams, and venues.
-- One row per entity. Sourced from standalone image enrichment scraper.
-- Returns empty result set if bronze.espn_images doesn't exist yet.
{% if source_exists('bronze', 'espn_images') %}
select
    entity_type,
    entity_id,
    entity_name,
    image_url,
    headshot_url,
    current_timestamp as _loaded_at
from {{ source('bronze', 'espn_images') }}
{% else %}
select
    null::varchar as entity_type,
    null::varchar as entity_id,
    null::varchar as entity_name,
    null::varchar as image_url,
    null::varchar as headshot_url,
    current_timestamp as _loaded_at
where false
{% endif %}
