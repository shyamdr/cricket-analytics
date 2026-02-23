-- Batting innings: per-batter-per-match aggregates
with deliveries as (
    select * from {{ ref('fact_deliveries') }}
)

select
    match_id,
    season,
    match_date,
    innings,
    batting_team,
    batter,
    count(*) filter (where is_legal_delivery) as balls_faced,
    sum(batter_runs) as runs_scored,
    count(*) filter (where is_four) as fours,
    count(*) filter (where is_six) as sixes,
    count(*) filter (where is_dot_ball) as dot_balls,
    -- Strike rate: (runs / balls) * 100
    case
        when count(*) filter (where is_legal_delivery) > 0
            then round(sum(batter_runs) * 100.0 / count(*) filter (where is_legal_delivery), 2)
        else 0
    end as strike_rate,
    -- Was the batter dismissed?
    max(case when is_wicket and wicket_player_out = batter then true else false end) as is_out,
    max(case when is_wicket and wicket_player_out = batter then wicket_kind else null end) as dismissal_kind,
    max(case when is_wicket and wicket_player_out = batter then bowler else null end) as dismissed_by
from deliveries
group by match_id, season, match_date, innings, batting_team, batter
