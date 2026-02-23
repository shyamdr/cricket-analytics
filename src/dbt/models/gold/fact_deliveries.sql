-- Fact deliveries: core grain table, one row per ball
-- Enriched with match context
select
    d.match_id,
    m.season,
    m.match_date,
    d.innings,
    d.batting_team,
    d.is_super_over,
    d.over_num,
    d.ball_num,
    d.batter,
    d.bowler,
    d.non_striker,
    d.batter_runs,
    d.extras_runs,
    d.total_runs,
    d.extras_wides,
    d.extras_noballs,
    d.extras_byes,
    d.extras_legbyes,
    d.extras_penalty,
    d.is_legal_delivery,
    d.is_wicket,
    d.wicket_player_out,
    d.wicket_kind,
    d.wicket_fielder1,
    d.wicket_fielder2,
    d.is_four,
    d.is_six,
    d.is_dot_ball,
    -- Phase classification
    case
        when d.over_num between 0 and 5 then 'powerplay'
        when d.over_num between 6 and 14 then 'middle'
        when d.over_num between 15 and 19 then 'death'
    end as phase
from {{ ref('stg_deliveries') }} d
join {{ ref('stg_matches') }} m on d.match_id = m.match_id
where d.is_super_over = false
