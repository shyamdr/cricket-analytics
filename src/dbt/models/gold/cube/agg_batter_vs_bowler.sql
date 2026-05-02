-- agg_batter_vs_bowler
-- One row per (batter, bowler) pair with historical matchup stats.
-- Source: stg_deliveries + stg_matches (silver — sibling rule).
-- Only includes pairs with at least 1 ball faced.
-- Super overs excluded.

with deliveries as (
    select
        d.match_id,
        d.batter,
        d.bowler,
        d.batter_runs,
        d.extras_wides,
        d.extras_noballs,
        d.is_legal_delivery,
        d.is_wicket,
        d.wicket_kind,
        d.wicket_player_out,
        d.is_four,
        d.is_six,
        d.is_dot_ball,
        m.season,
        m.match_date
    from {{ ref('stg_deliveries') }} d
    join {{ ref('stg_matches') }} m on d.match_id = m.match_id
    where d.is_super_over = false
)

select
    batter,
    bowler,
    count(distinct match_id) as matches,
    count(*) filter (where is_legal_delivery) as balls_faced,
    sum(batter_runs) as runs_scored,
    count(*) filter (
        where is_wicket
        and wicket_player_out = batter
        and wicket_kind not in ('run out', 'retired hurt', 'retired out', 'obstructing the field')
    ) as dismissals,
    count(*) filter (where is_four) as fours,
    count(*) filter (where is_six) as sixes,
    count(*) filter (where is_dot_ball and is_legal_delivery) as dot_balls,
    -- Strike rate
    case
        when count(*) filter (where is_legal_delivery) > 0
        then round(sum(batter_runs) * 100.0 / count(*) filter (where is_legal_delivery), 2)
        else 0
    end as strike_rate,
    -- Dot ball percentage
    case
        when count(*) filter (where is_legal_delivery) > 0
        then round(count(*) filter (where is_dot_ball and is_legal_delivery) * 100.0 / count(*) filter (where is_legal_delivery), 2)
        else 0
    end as dot_ball_percentage,
    -- Boundary percentage
    case
        when count(*) filter (where is_legal_delivery) > 0
        then round((count(*) filter (where is_four) + count(*) filter (where is_six)) * 100.0 / count(*) filter (where is_legal_delivery), 2)
        else 0
    end as boundary_percentage,
    -- Average (runs per dismissal)
    case
        when count(*) filter (
            where is_wicket and wicket_player_out = batter
            and wicket_kind not in ('run out', 'retired hurt', 'retired out', 'obstructing the field')
        ) > 0
        then round(sum(batter_runs) * 1.0 / count(*) filter (
            where is_wicket and wicket_player_out = batter
            and wicket_kind not in ('run out', 'retired hurt', 'retired out', 'obstructing the field')
        ), 2)
        else null
    end as average,
    -- Last encounter date
    max(match_date) as last_match_date,
    min(match_date) as first_match_date
from deliveries
group by batter, bowler
having count(*) filter (where is_legal_delivery) >= 1
