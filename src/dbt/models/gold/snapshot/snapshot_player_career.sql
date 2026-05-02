-- snapshot_player_career
-- =============================================================================
-- One row per (player, match) that the player participated in.
--
-- This is the SINGLE source of truth for point-in-time player state.
-- Every "as-of this match" column (career_*, rolling_N_*) follows ADR-007
-- and is computed via the point_in_time_window / rolling_window macros — the
-- current match's contribution is NEVER included.
--
-- Source (per ADR-006 sibling rule):
--   stg_deliveries + stg_matches from silver. Does NOT read from any gold
--   model. Mirrors the aggregation patterns used in fact_batting_innings and
--   fact_bowling_innings for metric consistency.
--
-- Grain:
--   (player_name, as_of_match_id)
--
-- Participation:
--   A player has a snapshot row for match M if they appear as batter, non_striker,
--   or bowler in at least one delivery of M. Fielders are included implicitly
--   when they also bat or bowl (the vast majority of cases); pure-fielder-only
--   appearances are rare and excluded for now.
--
-- Consumers:
--   - fact_deliveries_enriched — joins on (batter, as_of_match_id) and
--     (bowler, as_of_match_id) to pull career_* and rolling_N_* columns into OBT.
--   - ML feature tables — point-in-time-correct training features.
--   - Career trajectory UI — sorted scan per player.
-- =============================================================================

{{
    config(
        materialized='table',
        unique_key=['player_name', 'as_of_match_id']
    )
}}

with deliveries as (
    -- Pull silver deliveries once with match context. Exclude super overs so
    -- match-level aggregates match the existing fact_batting/fact_bowling tables.
    select
        d.match_id,
        m.season,
        m.match_date,
        d.batting_team,
        d.batter,
        d.bowler,
        d.non_striker,
        d.batter_runs,
        d.extras_wides,
        d.extras_noballs,
        d.is_legal_delivery,
        d.is_four,
        d.is_six,
        d.is_dot_ball,
        d.is_wicket,
        d.wicket_player_out,
        d.wicket_kind
    from {{ ref('stg_deliveries') }} d
    join {{ ref('stg_matches') }} m on d.match_id = m.match_id
    where d.is_super_over = false
),

-- ---------------------------------------------------------------------------
-- Per-match batting aggregates (one row per (match, batter))
-- ---------------------------------------------------------------------------
batting_per_match as (
    select
        match_id,
        season,
        match_date,
        batter as player_name,
        count(*) filter (where is_legal_delivery) as balls_faced,
        sum(batter_runs) as runs_scored,
        count(*) filter (where is_four) as fours,
        count(*) filter (where is_six) as sixes,
        count(*) filter (where is_dot_ball and is_legal_delivery) as dots_faced,
        max(case when is_wicket and wicket_player_out = batter then 1 else 0 end) as is_out
    from deliveries
    group by match_id, season, match_date, batter
),

-- ---------------------------------------------------------------------------
-- Per-match bowling aggregates (one row per (match, bowler))
-- Runs conceded and wicket eligibility mirror fact_bowling_innings exactly.
-- ---------------------------------------------------------------------------
bowling_per_match as (
    select
        match_id,
        season,
        match_date,
        bowler as player_name,
        count(*) filter (where is_legal_delivery) as legal_balls_bowled,
        sum(batter_runs + extras_wides + extras_noballs) as runs_conceded,
        count(*) filter (
            where is_wicket
            and wicket_kind not in (
                'run out', 'retired hurt', 'retired out', 'obstructing the field'
            )
        ) as wickets_taken,
        count(*) filter (where is_dot_ball and is_legal_delivery) as dots_bowled
    from deliveries
    group by match_id, season, match_date, bowler
),

-- ---------------------------------------------------------------------------
-- Participation set: every (player, match) where the player appeared in at
-- least one delivery as batter / non_striker / bowler. Union distinct across
-- all three roles.
-- ---------------------------------------------------------------------------
participation as (
    select distinct
        match_id,
        season,
        match_date,
        batter as player_name
    from deliveries
    union
    select distinct
        match_id,
        season,
        match_date,
        non_striker as player_name
    from deliveries
    union
    select distinct
        match_id,
        season,
        match_date,
        bowler as player_name
    from deliveries
),

-- ---------------------------------------------------------------------------
-- Merge participation with per-match aggregates. A row exists per (player,
-- match) regardless of whether they batted or bowled; missing side is NULL.
-- This is the "per-match contribution" base over which we compute career and
-- rolling windows.
-- ---------------------------------------------------------------------------
per_match as (
    select
        p.player_name,
        p.match_id,
        p.season,
        p.match_date,
        -- Batting contribution (NULL if didn't bat)
        b.balls_faced,
        b.runs_scored,
        b.fours,
        b.sixes,
        b.dots_faced,
        b.is_out as was_dismissed_this_match,
        -- Bowling contribution (NULL if didn't bowl)
        bw.legal_balls_bowled,
        bw.runs_conceded,
        bw.wickets_taken,
        bw.dots_bowled,
        -- Batted / bowled flags for counting career innings correctly
        case when b.player_name is not null then 1 else 0 end as did_bat,
        case when bw.player_name is not null then 1 else 0 end as did_bowl
    from participation p
    left join batting_per_match b
        on p.player_name = b.player_name and p.match_id = b.match_id
    left join bowling_per_match bw
        on p.player_name = bw.player_name and p.match_id = bw.match_id
)

-- ---------------------------------------------------------------------------
-- Final projection with point-in-time windows.
--
-- The order-by key is `(match_date, match_id)` so ties on date resolve
-- deterministically (two IPL matches on the same day — the tiebreaker is the
-- Cricsheet match_id).
--
-- Every career_* column uses point_in_time_window (strictly prior rows).
-- Every rolling_N_* column uses rolling_window (N prior rows, current excluded).
-- The current match's contribution is NEVER in any of these aggregates —
-- this is what makes the snapshot usable for ML training without leakage.
-- ---------------------------------------------------------------------------
select
    -- ========= Identity / as-of reference =========
    player_name,
    match_id as as_of_match_id,
    match_date as as_of_date,
    season,

    -- ========= This-match contribution =========
    -- Useful for career trajectory charts (plot "runs_scored" over match_date)
    -- and for reproducing career totals ("career_runs_before + runs_scored =
    -- career_runs_after").
    coalesce(did_bat, 0) as did_bat,
    coalesce(did_bowl, 0) as did_bowl,
    balls_faced,
    runs_scored,
    fours,
    sixes,
    dots_faced,
    was_dismissed_this_match,
    legal_balls_bowled,
    runs_conceded,
    wickets_taken,
    dots_bowled,

    -- ========= Career batting, as-of BEFORE this match =========
    {{ point_in_time_window(
        'sum(did_bat)',
        partition_by='player_name',
        order_by='match_date, match_id'
    ) }} as career_innings_batted_before,

    {{ point_in_time_window(
        'sum(coalesce(runs_scored, 0))',
        partition_by='player_name',
        order_by='match_date, match_id'
    ) }} as career_runs_before,

    {{ point_in_time_window(
        'sum(coalesce(balls_faced, 0))',
        partition_by='player_name',
        order_by='match_date, match_id'
    ) }} as career_balls_faced_before,

    {{ point_in_time_window(
        'sum(coalesce(fours, 0))',
        partition_by='player_name',
        order_by='match_date, match_id'
    ) }} as career_fours_before,

    {{ point_in_time_window(
        'sum(coalesce(sixes, 0))',
        partition_by='player_name',
        order_by='match_date, match_id'
    ) }} as career_sixes_before,

    {{ point_in_time_window(
        'sum(coalesce(was_dismissed_this_match, 0))',
        partition_by='player_name',
        order_by='match_date, match_id'
    ) }} as career_dismissals_before,

    -- ========= Career bowling, as-of BEFORE this match =========
    {{ point_in_time_window(
        'sum(did_bowl)',
        partition_by='player_name',
        order_by='match_date, match_id'
    ) }} as career_innings_bowled_before,

    {{ point_in_time_window(
        'sum(coalesce(legal_balls_bowled, 0))',
        partition_by='player_name',
        order_by='match_date, match_id'
    ) }} as career_legal_balls_bowled_before,

    {{ point_in_time_window(
        'sum(coalesce(runs_conceded, 0))',
        partition_by='player_name',
        order_by='match_date, match_id'
    ) }} as career_runs_conceded_before,

    {{ point_in_time_window(
        'sum(coalesce(wickets_taken, 0))',
        partition_by='player_name',
        order_by='match_date, match_id'
    ) }} as career_wickets_before,

    -- ========= Rolling batting form (last 10 innings, excluding current) =========
    -- The rolling_window macro uses `rows between 10 preceding and 1 preceding`,
    -- so these windows look at up to 10 prior match rows. For players with
    -- fewer than 10 prior matches the window is short; for first-match debut
    -- the aggregates return NULL — the correct answer ("no prior form").
    {{ rolling_window(
        'sum(coalesce(runs_scored, 0))',
        partition_by='player_name',
        order_by='match_date, match_id',
        rows=10
    ) }} as rolling_10_runs,

    {{ rolling_window(
        'sum(coalesce(balls_faced, 0))',
        partition_by='player_name',
        order_by='match_date, match_id',
        rows=10
    ) }} as rolling_10_balls_faced,

    -- ========= Rolling bowling form (last 10 innings bowled, excluding current) =========
    {{ rolling_window(
        'sum(coalesce(wickets_taken, 0))',
        partition_by='player_name',
        order_by='match_date, match_id',
        rows=10
    ) }} as rolling_10_wickets,

    {{ rolling_window(
        'sum(coalesce(runs_conceded, 0))',
        partition_by='player_name',
        order_by='match_date, match_id',
        rows=10
    ) }} as rolling_10_runs_conceded,

    {{ rolling_window(
        'sum(coalesce(legal_balls_bowled, 0))',
        partition_by='player_name',
        order_by='match_date, match_id',
        rows=10
    ) }} as rolling_10_legal_balls_bowled,

    current_timestamp as _loaded_at
from per_match
-- Materialization: `table` with full refresh. Snapshots with cumulative
-- window functions cannot be safely incremental because a new match for a
-- player requires re-computing all downstream snapshot rows for that player
-- (cumulative totals change). At our scale (~185K rows projected for full
-- coverage), a full rebuild is sub-second and avoids partial-update bugs.
