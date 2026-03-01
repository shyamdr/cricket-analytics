-- Staged matches: cleaned types, normalized season format
with source as (
    select * from {{ source('bronze', 'matches') }}
)

select
    match_id,
    data_version,
    -- Normalize season: extract the calendar year matches were actually played in.
    -- "2007/08" → "2008" (IPL 1, played Apr-Jun 2008)
    -- "2009/10" → "2010" (IPL 3, played Mar-Apr 2010)
    -- "2020/21" → "2020" (IPL played Sep-Nov 2020 in UAE due to COVID)
    case
        when season = '2020/21'
            then '2020'
        when season like '%/%'
            then '20' || split_part(season, '/', 2)
        else season
    end as season,
    cast(date as date) as match_date,
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
    match_type,
    gender,
    overs as max_overs,
    balls_per_over,
    players_team1_json,
    players_team2_json,
    registry_json,
    current_timestamp as _loaded_at
from source
