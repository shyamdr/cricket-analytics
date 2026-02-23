-- Venue dimension: unique venues with match counts
select
    venue,
    city,
    count(distinct match_id) as total_matches,
    min(match_date) as first_match_date,
    max(match_date) as last_match_date
from {{ ref('stg_matches') }}
where venue is not null
group by venue, city
