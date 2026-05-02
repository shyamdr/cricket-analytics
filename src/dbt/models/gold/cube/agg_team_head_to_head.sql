-- agg_team_head_to_head
-- One row per (team_a, team_b) pair with historical head-to-head record.
-- Source: stg_matches (silver). Uses canonical team names via team_name_mappings.
-- Ordered so team_a < team_b alphabetically to avoid duplicate pairs.

with matches as (
    select
        m.match_id,
        m.match_date,
        m.season,
        m.venue,
        coalesce(nullif(t1.current_franchise_name, ''), m.team1) as team1,
        coalesce(nullif(t2.current_franchise_name, ''), m.team2) as team2,
        m.outcome_winner,
        m.outcome_result,
        m.outcome_by_runs,
        m.outcome_by_wickets,
        m.outcome_method
    from {{ ref('stg_matches') }} m
    left join {{ ref('team_name_mappings') }} t1 on m.team1 = t1.team_name
    left join {{ ref('team_name_mappings') }} t2 on m.team2 = t2.team_name
),

-- Normalize so team_a is always alphabetically first
normalized as (
    select
        case when team1 < team2 then team1 else team2 end as team_a,
        case when team1 < team2 then team2 else team1 end as team_b,
        match_id,
        match_date,
        season,
        venue,
        -- Map winner to canonical name
        case
            when outcome_winner = team1 then
                case when team1 < team2 then team1 else team2 end
            when outcome_winner = team2 then
                case when team1 < team2 then team2 else team1 end
            -- Handle cases where outcome_winner uses the raw name
            when outcome_winner is not null then outcome_winner
            else null
        end as winner,
        outcome_result,
        outcome_by_runs,
        outcome_by_wickets,
        outcome_method
    from matches
    where team1 != team2
)

select
    team_a,
    team_b,
    count(*) as total_matches,
    count(*) filter (where winner = team_a) as team_a_wins,
    count(*) filter (where winner = team_b) as team_b_wins,
    count(*) filter (where outcome_result = 'no result') as no_results,
    count(*) filter (where outcome_result = 'tie') as ties,
    -- Win percentages
    case
        when count(*) - count(*) filter (where outcome_result in ('no result')) > 0
        then round(count(*) filter (where winner = team_a) * 100.0 /
            (count(*) - count(*) filter (where outcome_result in ('no result'))), 1)
        else null
    end as team_a_win_pct,
    -- Last 5 results (most recent first)
    list(winner order by match_date desc)[:5] as last_5_winners,
    max(match_date) as last_match_date,
    min(match_date) as first_match_date
from normalized
group by team_a, team_b
