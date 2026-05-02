-- ADR-007 tripwire: a player's very first snapshot row must have NULL (or 0-equivalent)
-- for every *_before column.
--
-- Why: the point_in_time_window macro uses `rows between unbounded preceding and
-- 1 preceding`. For the earliest row in a player's partition there are zero
-- prior rows, so aggregate expressions return NULL. If a first-match row shows
-- a non-NULL nonzero *_before value, the window is including the current row
-- (data leakage) or the partition is wrong.
--
-- Catches: the classic "forgot the frame clause" bug where window defaults to
-- `range between unbounded preceding and current row`, inflating the first-row
-- value by the current row's contribution.

with first_match_per_player as (
    select
        player_name,
        as_of_match_id,
        career_runs_before,
        career_balls_faced_before,
        career_innings_batted_before,
        career_wickets_before,
        career_legal_balls_bowled_before,
        career_runs_conceded_before,
        row_number() over (
            partition by player_name order by as_of_date, as_of_match_id
        ) as rn
    from {{ ref('snapshot_player_career') }}
)

select *
from first_match_per_player
where
    rn = 1
    and (
        -- Any non-null non-zero here means window function leaked
        coalesce(career_runs_before, 0) > 0
        or coalesce(career_balls_faced_before, 0) > 0
        or coalesce(career_innings_batted_before, 0) > 0
        or coalesce(career_wickets_before, 0) > 0
        or coalesce(career_legal_balls_bowled_before, 0) > 0
        or coalesce(career_runs_conceded_before, 0) > 0
    )
