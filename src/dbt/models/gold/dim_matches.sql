-- Match dimension: one row per match with derived analytical columns
-- Enriched with ESPN data (captains, home team, timing, venue details)
select
    m.match_id,
    m.season,
    m.match_date,
    m.city,
    m.venue,
    m.team1,
    m.team2,
    m.toss_winner,
    m.toss_decision,
    m.outcome_winner,
    m.outcome_by_runs,
    m.outcome_by_wickets,
    m.outcome_method,
    m.outcome_result,
    m.outcome_eliminator,
    m.player_of_match,
    m.event_name,
    m.event_match_number,
    m.event_stage,
    m.match_type,
    m.gender,
    m.max_overs,

    -- Derived: classify match result into a single enum
    case
        when m.outcome_result = 'no result' then 'no_result'
        when m.outcome_result = 'tie' and m.outcome_eliminator is not null then 'tie_super_over'
        when m.outcome_method = 'D/L' then 'dls_win'
        when m.outcome_method = 'Awarded' then 'awarded'
        when m.outcome_winner is not null then 'normal_win'
        else 'unknown'
    end as match_result_type,

    -- Derived: human-readable winning margin
    case
        when m.outcome_result = 'no result' then 'no result'
        when m.outcome_result = 'tie' and m.outcome_eliminator is not null
            then m.outcome_eliminator || ' won via super over'
        when m.outcome_by_runs is not null
            then m.outcome_by_runs || ' runs'
        when m.outcome_by_wickets is not null
            then m.outcome_by_wickets || ' wickets'
        else null
    end as winning_margin,

    -- ESPN enrichment: captains and keepers
    e.team1_captain,
    e.team1_keeper,
    e.team2_captain,
    e.team2_keeper,

    -- ESPN enrichment: home team flags
    e.team1_is_home,
    e.team2_is_home,

    -- ESPN enrichment: timing
    e.floodlit,
    e.start_time,
    e.end_time,
    e.hours_info,
    e.venue_timezone,

    -- ESPN enrichment: venue and classification
    e.espn_match_id,
    e.espn_ground_id,
    e.ground_capacity,
    e.international_class_id,
    e.sub_class_id,

    -- ESPN enrichment: JSON blobs for downstream use
    e.replacement_players_json,
    e.teams_enrichment_json

from {{ ref('stg_matches') }} m
left join {{ ref('stg_espn_matches') }} e on m.match_id = e.match_id
