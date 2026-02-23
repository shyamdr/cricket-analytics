-- Match dimension: one row per IPL match
select
    match_id,
    season,
    match_date,
    city,
    venue,
    team1,
    team2,
    toss_winner,
    toss_decision,
    outcome_winner,
    outcome_by_runs,
    outcome_by_wickets,
    outcome_method,
    outcome_result,
    outcome_eliminator,
    player_of_match,
    event_name,
    event_match_number,
    event_stage,
    max_overs
from {{ ref('stg_matches') }}
