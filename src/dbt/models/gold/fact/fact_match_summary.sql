-- Match summary: team-level aggregates per innings
-- Reads from silver (stg_deliveries) with explicit super_over filter
with deliveries as (
    select
        d.*,
        m.season,
        m.match_date
    from {{ ref('stg_deliveries') }} d
    join {{ ref('stg_matches') }} m on d.match_id = m.match_id
    where d.is_super_over = false
)

select
    match_id,
    season,
    match_date,
    innings,
    batting_team,
    sum(total_runs) as total_runs,
    count(*) filter (where is_wicket) as total_wickets,
    count(*) filter (where is_legal_delivery) as legal_balls,
    sum(extras_runs) as total_extras,
    count(*) filter (where is_four) as total_fours,
    count(*) filter (where is_six) as total_sixes,
    count(*) filter (where is_dot_ball) as total_dot_balls,
    -- Run rate
    case
        when count(*) filter (where is_legal_delivery) > 0
            then round(
                sum(total_runs) * 6.0 / count(*) filter (where is_legal_delivery), 2
            )
        else 0
    end as run_rate,
    max(over_num) + 1 as overs_played
from deliveries
group by match_id, season, match_date, innings, batting_team
