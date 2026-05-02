-- ADR-007 tripwire: point-in-time career columns must be monotonic non-decreasing
-- per player as match_date ascends.
--
-- Why: career_runs_before, career_wickets_before, career_innings_batted_before,
-- etc. are cumulative sums of prior-row values. They can only grow or stay flat.
-- If any successive row shows a DECREASE for the same player, a window function
-- is misconfigured (wrong partition, wrong order, wrong frame bound).
--
-- Catches: accidental use of PARTITION BY other than player_name,
-- non-deterministic ORDER BY, ROWS frame bounds that include the current or
-- future rows (classic data leakage bug).

with ordered as (
    select
        player_name,
        as_of_match_id,
        as_of_date,
        career_runs_before,
        career_balls_faced_before,
        career_innings_batted_before,
        career_wickets_before,
        career_legal_balls_bowled_before,
        career_runs_conceded_before,
        lag(career_runs_before) over (
            partition by player_name order by as_of_date, as_of_match_id
        ) as prev_runs,
        lag(career_balls_faced_before) over (
            partition by player_name order by as_of_date, as_of_match_id
        ) as prev_balls,
        lag(career_innings_batted_before) over (
            partition by player_name order by as_of_date, as_of_match_id
        ) as prev_innings_batted,
        lag(career_wickets_before) over (
            partition by player_name order by as_of_date, as_of_match_id
        ) as prev_wickets,
        lag(career_legal_balls_bowled_before) over (
            partition by player_name order by as_of_date, as_of_match_id
        ) as prev_balls_bowled,
        lag(career_runs_conceded_before) over (
            partition by player_name order by as_of_date, as_of_match_id
        ) as prev_runs_conceded
    from {{ ref('snapshot_player_career') }}
)

select *
from ordered
where
    -- Coalesce nulls so the first row (prev = NULL) doesn't falsely trigger
    career_runs_before < coalesce(prev_runs, career_runs_before)
    or career_balls_faced_before < coalesce(prev_balls, career_balls_faced_before)
    or career_innings_batted_before < coalesce(prev_innings_batted, career_innings_batted_before)
    or career_wickets_before < coalesce(prev_wickets, career_wickets_before)
    or career_legal_balls_bowled_before < coalesce(prev_balls_bowled, career_legal_balls_bowled_before)
    or career_runs_conceded_before < coalesce(prev_runs_conceded, career_runs_conceded_before)
