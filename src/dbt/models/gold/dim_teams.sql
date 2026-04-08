
-- Team dimension: all team names that have appeared in match data
-- Franchise rename mappings loaded from seed CSV (team_name_mappings)
-- Team logos from standalone espn_images enrichment
with all_teams as (
    select team1 as team_name from {{ ref('stg_matches') }}
    union
    select team2 as team_name from {{ ref('stg_matches') }}
),

team_stats as (
    select
        t.team_name,
        min(m.match_date) as first_match_date,
        max(m.match_date) as last_match_date,
        count(distinct m.match_id) as total_matches
    from all_teams t
    join {{ ref('stg_matches') }} m
        on t.team_name in (m.team1, m.team2)
    group by t.team_name
),

-- Team logos from standalone image enrichment
team_images as (
    select entity_id, entity_name, image_url as logo_url
    from {{ ref('stg_espn_images') }}
    where entity_type = 'team'
)

select
    ts.team_name,
    case
        when tnm.team_name is null then ts.team_name  -- not in mappings = active, never renamed
        when tnm.current_franchise_name = '' then null  -- in mappings with empty value = defunct
        else tnm.current_franchise_name  -- renamed franchise
    end as current_franchise_name,
    ts.first_match_date,
    ts.last_match_date,
    ts.total_matches,
    -- Image enrichment
    ti.logo_url
from team_stats ts
left join {{ ref('team_name_mappings') }} tnm
    on ts.team_name = tnm.team_name
left join team_images ti
    on ts.team_name = ti.entity_name
