
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

-- Team data from ESPN enrichment
espn_teams as (
    select
        team_long_name,
        espn_team_id,
        team_abbreviation,
        is_country,
        primary_color,
        image_url as logo_url
    from {{ ref('stg_espn_teams') }}
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
    -- ESPN enrichment (fallback to seed for teams not in ESPN)
    coalesce(et.espn_team_id, tbc.espn_team_id) as espn_team_id,
    coalesce(et.team_abbreviation, tbc.team_name) as team_abbreviation,
    et.is_country,
    -- Brand colors from curated seed (ESPN colors are unreliable)
    coalesce(tbc.brand_color, et.primary_color) as primary_color,
    tbc.brand_color_alt,
    et.logo_url
from team_stats ts
left join {{ ref('team_name_mappings') }} tnm
    on ts.team_name = tnm.team_name
left join espn_teams et
    on ts.team_name = et.team_long_name
left join {{ ref('team_brand_colors') }} tbc
    on ts.team_name = tbc.team_name
