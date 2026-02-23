-- Staged deliveries: proper types, computed flags
with source as (
    select * from {{ source('bronze', 'deliveries') }}
)

select
    match_id,
    innings,
    batting_team,
    is_super_over,
    over_num,
    ball_num,
    batter,
    bowler,
    non_striker,
    batter_runs,
    extras_runs,
    total_runs,
    coalesce(extras_wides, 0) as extras_wides,
    coalesce(extras_noballs, 0) as extras_noballs,
    coalesce(extras_byes, 0) as extras_byes,
    coalesce(extras_legbyes, 0) as extras_legbyes,
    coalesce(extras_penalty, 0) as extras_penalty,
    -- A ball counts as legal if it's not a wide or no-ball
    case
        when coalesce(extras_wides, 0) = 0 and coalesce(extras_noballs, 0) = 0
            then true
        else false
    end as is_legal_delivery,
    is_wicket,
    wicket_player_out,
    wicket_kind,
    wicket_fielder1,
    wicket_fielder2,
    -- Boundary flags
    case when batter_runs = 4 then true else false end as is_four,
    case when batter_runs = 6 then true else false end as is_six,
    -- Dot ball: legal delivery with 0 total runs
    case
        when coalesce(extras_wides, 0) = 0
            and coalesce(extras_noballs, 0) = 0
            and total_runs = 0
            then true
        else false
    end as is_dot_ball
from source
