-- Venue dimension: unique venues with match counts
-- Enriched with ESPN ground data (capacity, timezone, ESPN ground ID)
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
)

select
    vs.venue,
    vs.city,
    vs.total_matches,
    vs.first_match_date,
    vs.last_match_date,
    -- ESPN enrichment
    ev.espn_ground_id,
    ev.ground_capacity,
    ev.venue_timezone
from venue_stats vs
left join espn_venue ev
    on vs.venue = ev.venue
    and ev.rn = 1
