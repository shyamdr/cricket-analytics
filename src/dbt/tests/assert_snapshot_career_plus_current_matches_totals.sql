-- ADR-007 tripwire: for every (player, match) snapshot row, the identity
--     career_runs_before + runs_scored_this_match (coalesced 0) = career_runs_after
-- must hold, where career_runs_after is computed as the SAME window but
-- including the current row.
--
-- We don't expose career_runs_after as a snapshot column (the rule is "as-of
-- before" only), so this test computes it inline from the same base data and
-- asserts equality.
--
-- Why: this is the arithmetic-level proof that point-in-time windows behave
-- correctly. If career_runs_before at match N equals the sum of runs in
-- matches 1..N-1, then career_runs_before at match N+1 must equal
-- career_runs_before(N) + runs_scored(N). Breakage here indicates the frame
-- clause or order-by is subtly wrong.

with snapshot_with_next as (
    select
        player_name,
        as_of_match_id,
        as_of_date,
        career_runs_before,
        coalesce(runs_scored, 0) as runs_scored_this_match,
        career_wickets_before,
        coalesce(wickets_taken, 0) as wickets_this_match,
        lead(career_runs_before) over (
            partition by player_name order by as_of_date, as_of_match_id
        ) as next_career_runs_before,
        lead(career_wickets_before) over (
            partition by player_name order by as_of_date, as_of_match_id
        ) as next_career_wickets_before
    from {{ ref('snapshot_player_career') }}
)

select *
from snapshot_with_next
where
    -- Skip the last row per player (no "next" row to check against)
    next_career_runs_before is not null
    and (
        (coalesce(career_runs_before, 0) + runs_scored_this_match)
            != coalesce(next_career_runs_before, 0)
        or (coalesce(career_wickets_before, 0) + wickets_this_match)
            != coalesce(next_career_wickets_before, 0)
    )
