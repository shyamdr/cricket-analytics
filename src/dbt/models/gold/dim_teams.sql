
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
    -- ESPN enrichment keyed on the CURRENT franchise name for historical variants.
    -- E.g. "Delhi Daredevils" has no ESPN match, so look up "Delhi Capitals" instead.
    -- Falls back to the team's own name when there's no rename mapping.
    coalesce(et_current.espn_team_id, et.espn_team_id) as espn_team_id,
    coalesce(et_current.team_abbreviation, et.team_abbreviation) as team_abbreviation,
    coalesce(et_current.is_country, et.is_country) as is_country,
    -- Brand colors from curated seed, joined by team_name (the seed lists each
    -- name variant explicitly — including spelling variants like
    -- "Rising Pune Supergiants" vs "Rising Pune Supergiant").
    coalesce(
        tbc.brand_color,
        et_current.primary_color,
        et.primary_color
    ) as primary_color,
    tbc.brand_color_alt,
    coalesce(et_current.logo_url, et.logo_url) as logo_url
from team_stats ts
left join {{ ref('team_name_mappings') }} tnm
    on ts.team_name = tnm.team_name
-- Direct ESPN match on the team's own name (works for current/active teams)
left join espn_teams et
    on ts.team_name = et.team_long_name
-- ESPN match via the current franchise name (works for historical rename variants)
left join espn_teams et_current
    on nullif(tnm.current_franchise_name, '') = et_current.team_long_name
left join {{ ref('team_brand_colors') }} tbc
    on ts.team_name = tbc.team_name
