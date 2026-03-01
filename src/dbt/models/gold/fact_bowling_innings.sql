-- Bowling innings: per-bowler-per-match aggregates
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
    bowler,
    count(*) filter (where is_legal_delivery) as legal_balls,
    -- Overs bowled (e.g. 4.0, 3.2)
    floor(count(*) filter (where is_legal_delivery) / 6)
        + (count(*) filter (where is_legal_delivery) % 6) * 0.1 as overs_bowled,
    sum(total_runs) as runs_conceded,
    count(*) filter (where is_wicket
        and wicket_kind not in ('run out', 'retired hurt', 'retired out', 'obstructing the field')
    ) as wickets,
    count(*) filter (where is_dot_ball) as dot_balls,
    sum(extras_wides) as wides,
    sum(extras_noballs) as noballs,
    count(*) filter (where is_four) as fours_conceded,
    count(*) filter (where is_six) as sixes_conceded,
    -- Economy rate: runs per over
    case
        when count(*) filter (where is_legal_delivery) > 0
            then round(
                sum(total_runs) * 6.0 / count(*) filter (where is_legal_delivery), 2
            )
        else 0
    end as economy_rate
from deliveries
group by match_id, season, match_date, innings, batting_team, bowler
