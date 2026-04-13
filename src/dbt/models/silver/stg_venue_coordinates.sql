-- Staged venue coordinates from geocoding enrichment.
-- One row per (venue, city) combo with lat/lng and geocode status.
-- Returns empty result set if bronze.venue_coordinates doesn't exist yet.
{% if source_exists('bronze', 'venue_coordinates') %}
select
    venue,
    city,
    cast(latitude as double) as latitude,
    cast(longitude as double) as longitude,
    formatted_address,
    place_id,
    geocode_status,
    current_timestamp as _loaded_at

from {{ source('bronze', 'venue_coordinates') }}
where geocode_status = 'ok'

{% else %}
select
    null::varchar as venue,
    null::varchar as city,
    null::double as latitude,
    null::double as longitude,
    null::varchar as formatted_address,
    null::varchar as place_id,
    null::varchar as geocode_status,
    current_timestamp as _loaded_at
where false
{% endif %}
