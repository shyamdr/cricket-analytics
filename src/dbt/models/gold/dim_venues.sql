
-- Venue dimension: unique venues with match counts
-- Normalized via venue_name_mappings seed (alias → canonical name)
-- Enriched with ESPN ground data (capacity, timezone, ESPN ground ID)
-- and geocoded coordinates from bronze.venue_coordinates
-- Venue images from standalone espn_images enrichment
with venue_stats as (
    select
        venue,
        city,
        count(distinct match_id) as total_matches,
        min(match_date) as first_match_date,
        max(match_date) as last_match_date
    from {{ ref('stg_matches') }}
    where venue is not null
    group by venue, city
),

-- ESPN venue data: pick the most common ground_id per venue
-- (handles slight name variations across ESPN records)
espn_venue as (
    select
        m.venue,
        e.espn_ground_id,
        e.ground_capacity,
        e.venue_timezone,
        row_number() over (
            partition by m.venue
            order by count(*) desc
        ) as rn
    from {{ ref('stg_matches') }} m
    join {{ ref('stg_espn_matches') }} e on m.match_id = e.match_id
    where e.espn_ground_id is not null
    group by m.venue, e.espn_ground_id, e.ground_capacity, e.venue_timezone
),

-- Geocoded coordinates from bronze.venue_coordinates (populated by geocoding enrichment job)
geocoded as (
    select
        venue,
        city,
        latitude,
        longitude,
        formatted_address,
        place_id,
        geocode_status
    from {{ source('bronze', 'venue_coordinates') }}
    where geocode_status = 'ok'
),

-- Venue images from standalone image enrichment (keyed by espn_ground_id)
venue_images as (
    select entity_id, image_url as venue_image_url
    from {{ ref('stg_espn_images') }}
    where entity_type = 'venue'
)

select
    vs.venue,
    vs.city,
    -- Canonical names from venue_name_mappings seed (like team_name_mappings for teams)
    -- If a mapping exists, use the canonical name; otherwise keep the original
    coalesce(vnm.canonical_venue, vs.venue) as canonical_venue,
    coalesce(vnm.canonical_city, vs.city) as canonical_city,
    vs.total_matches,
    vs.first_match_date,
    vs.last_match_date,
    -- Geocoded coordinates
    gc.latitude,
    gc.longitude,
    gc.formatted_address,
    gc.place_id,
    -- ESPN enrichment
    ev.espn_ground_id,
    ev.ground_capacity,
    ev.venue_timezone,
    -- Venue image
    vi.venue_image_url
from venue_stats vs
left join espn_venue ev
    on vs.venue = ev.venue
    and ev.rn = 1
left join {{ ref('venue_name_mappings') }} vnm
    on vs.venue = vnm.venue_name
    and (vs.city = vnm.city_name or (vs.city is null and vnm.city_name is null))
left join geocoded gc
    on vs.venue = gc.venue
    and (vs.city = gc.city or (vs.city is null and gc.city is null))
left join venue_images vi
    on ev.espn_ground_id is not null
    and vi.entity_id = cast(ev.espn_ground_id as varchar)
