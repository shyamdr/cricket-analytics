-- Team dimension: all team names that have appeared in IPL
-- Includes historical name mappings
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
)

select
    team_name,
    -- Map historical names to current franchise
    case team_name
        when 'Delhi Daredevils' then 'Delhi Capitals'
        when 'Deccan Chargers' then 'Sunrisers Hyderabad'
        when 'Kings XI Punjab' then 'Punjab Kings'
        when 'Royal Challengers Bangalore' then 'Royal Challengers Bengaluru'
        when 'Rising Pune Supergiant' then null
        when 'Rising Pune Supergiants' then null
        when 'Gujarat Lions' then null
        when 'Kochi Tuskers Kerala' then null
        when 'Pune Warriors' then null
        else team_name
    end as current_franchise_name,
    first_match_date,
    last_match_date,
    total_matches
from team_stats
