-- Staged matches: cleaned types, normalized season format
with source as (
    select * from {{ source('bronze', 'matches') }}
)

select
    match_id,
    data_version,
    -- Keep the raw Cricsheet season for reference (e.g. '2020/21', '2025')
    season as season_raw,
    -- Derive season from the actual match date — format-agnostic.
    -- Works correctly across all leagues and edge cases:
    --   IPL 2007/08 (played Apr-Jun 2008) → '2008'
    --   IPL 2020/21 (COVID, played Sep-Nov 2020) → '2020'
    --   BBL 2020/21 (played Dec 2020 - Feb 2021) → '2020' or '2021' per match
    --   IPL 2025 → '2025'
    -- No hardcoded special cases needed.
    cast(extract(year from cast(date as date)) as varchar) as season,
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
