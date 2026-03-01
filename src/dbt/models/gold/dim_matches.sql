-- Match dimension: one row per match with derived analytical columns
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
    match_type,
    gender,
    max_overs,

    -- Derived: classify match result into a single enum
    case
        when outcome_result = 'no result' then 'no_result'
        when outcome_result = 'tie' and outcome_eliminator is not null then 'tie_super_over'
        when outcome_method = 'D/L' then 'dls_win'
        when outcome_winner is not null then 'normal_win'
        else 'unknown'
    end as match_result_type,

    -- Derived: human-readable winning margin
    case
        when outcome_result = 'no result' then 'no result'
        when outcome_result = 'tie' and outcome_eliminator is not null
            then outcome_eliminator || ' won via super over'
        when outcome_by_runs is not null
            then outcome_by_runs || ' runs'
        when outcome_by_wickets is not null
            then outcome_by_wickets || ' wickets'
        else null
    end as winning_margin,

    -- Placeholder: populated by venue-team enrichment in a future phase
    cast(null as boolean) as is_home_team

from {{ ref('stg_matches') }}
