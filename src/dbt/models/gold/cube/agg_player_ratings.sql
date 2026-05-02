-- agg_player_ratings
-- Composite player rating per (player, match). One row per player per match
-- they participated in. All stats are time-contextual (as-of BEFORE this match).
--
-- Reads from snapshot_player_career (career + rolling stats already computed
-- with safe window macros per ADR-007) and enriches with age and role dimensions.
-- Final composite is a weighted 0-100 score.

with snapshot as (
    select * from {{ ref('snapshot_player_career') }}
),

-- Player attributes (role, DOB)
players as (
    select
        dp.player_name,
        ep.date_of_birth,
        ep.playing_roles,
        case
            when ep.playing_roles like '%wicketkeeper%' then 'wicketkeeper'
            when ep.playing_roles like '%allrounder%' then 'allrounder'
            when ep.playing_roles like '%bowler%' or ep.playing_roles like '%bowling%' then 'bowler'
            when ep.playing_roles like '%batter%' or ep.playing_roles like '%batting%' or ep.playing_roles like '%opening%' or ep.playing_roles like '%top-order%' or ep.playing_roles like '%middle-order%' then 'batter'
            else 'unknown'
        end as playing_role
    from (
        select *, row_number() over (partition by player_name order by player_id) as _rn
        from {{ ref('dim_players') }}
    ) dp
    left join {{ ref('stg_espn_players') }} ep
        on dp.key_cricinfo is not null
        and ep.espn_player_id = try_cast(dp.key_cricinfo as bigint)
    where dp._rn = 1
),

-- Base metrics: combine snapshot with player attributes
base as (
    select
        s.player_name,
        s.as_of_match_id,
        s.as_of_date,
        s.season,
        p.playing_role,
        p.date_of_birth,
        case
            when p.date_of_birth is not null
            then date_diff('year', p.date_of_birth, s.as_of_date)
        end as age_at_match,
        s.career_innings_batted_before,
        s.career_runs_before,
        s.career_balls_faced_before,
        s.career_dismissals_before,
        s.career_innings_bowled_before,
        s.career_wickets_before,
        s.career_legal_balls_bowled_before,
        s.career_runs_conceded_before,
        s.rolling_10_runs,
        s.rolling_10_balls_faced,
        s.rolling_10_wickets,
        s.rolling_10_runs_conceded,
        s.rolling_10_legal_balls_bowled,
        -- Derived batting
        case when s.career_dismissals_before > 0
            then s.career_runs_before * 1.0 / s.career_dismissals_before end as career_batting_avg,
        case when s.career_balls_faced_before > 0
            then s.career_runs_before * 100.0 / s.career_balls_faced_before end as career_batting_sr,
        -- Derived bowling
        case when s.career_legal_balls_bowled_before > 0
            then s.career_runs_conceded_before * 6.0 / s.career_legal_balls_bowled_before end as career_bowling_econ,
        case when s.career_wickets_before > 0
            then s.career_legal_balls_bowled_before * 1.0 / s.career_wickets_before end as career_bowling_sr,
        -- Rolling form
        case when s.rolling_10_balls_faced > 0
            then s.rolling_10_runs * 100.0 / s.rolling_10_balls_faced end as form_batting_sr,
        case when s.rolling_10_legal_balls_bowled > 0
            then s.rolling_10_runs_conceded * 6.0 / s.rolling_10_legal_balls_bowled end as form_bowling_econ,
        -- Confidence
        case
            when coalesce(s.career_innings_batted_before, 0) + coalesce(s.career_innings_bowled_before, 0) >= 5
            then 1.0
            else (coalesce(s.career_innings_batted_before, 0) + coalesce(s.career_innings_bowled_before, 0)) / 5.0
        end as confidence
    from snapshot s
    left join players p on s.player_name = p.player_name
),

-- Percentile-rank normalization (0-100)
normalized as (
    select
        b.*,
        coalesce(percent_rank() over (
            order by coalesce(career_innings_batted_before, 0) + coalesce(career_innings_bowled_before, 0)
        ) * 100, 0) as experience_score,
        case
            when age_at_match is null then 50
            when age_at_match between 26 and 32 then least(100, 90 + (32 - abs(29 - age_at_match)) * 2)
            when age_at_match between 22 and 25 then 60 + (age_at_match - 22) * 7
            when age_at_match between 33 and 37 then greatest(40, 80 - (age_at_match - 33) * 8)
            when age_at_match < 22 then greatest(20, 40 + age_at_match)
            else 20
        end as age_score,
        case when career_batting_avg is not null and career_batting_sr is not null
            then coalesce(percent_rank() over (
                order by career_batting_avg * 0.5 + career_batting_sr * 0.5
            ) * 100, 0)
        end as batting_score,
        case when career_bowling_econ is not null
            then coalesce((1.0 - percent_rank() over (order by career_bowling_econ)) * 100, 0)
        end as bowling_score,
        case
            when form_batting_sr is not null
            then coalesce(percent_rank() over (order by form_batting_sr) * 100, 0)
            when form_bowling_econ is not null
            then coalesce((1.0 - percent_rank() over (order by form_bowling_econ)) * 100, 0)
            else 50
        end as form_score
    from base b
)

select
    player_name,
    as_of_match_id,
    as_of_date,
    season,
    playing_role,
    age_at_match,
    confidence,
    round(experience_score, 1) as experience_score,
    round(age_score, 1) as age_score,
    round(coalesce(batting_score, 0), 1) as batting_score,
    round(coalesce(bowling_score, 0), 1) as bowling_score,
    round(form_score, 1) as form_score,
    -- Placeholders for future dimensions
    null::double as venue_score,
    null::double as pressure_score,
    null::double as vs_pace_score,
    null::double as vs_spin_score,
    null::double as adaptability_score,
    -- Composite
    round(
        case coalesce(playing_role, 'unknown')
            when 'batter' then
                0.05 * experience_score + 0.05 * age_score + 0.40 * coalesce(batting_score, 50)
                + 0.30 * form_score + 0.10 * 50 + 0.10 * 50
            when 'bowler' then
                0.05 * experience_score + 0.05 * age_score + 0.40 * coalesce(bowling_score, 50)
                + 0.30 * form_score + 0.10 * 50 + 0.10 * 50
            when 'allrounder' then
                0.05 * experience_score + 0.05 * age_score + 0.20 * coalesce(batting_score, 50)
                + 0.20 * coalesce(bowling_score, 50) + 0.25 * form_score + 0.10 * 50 + 0.15 * 50
            when 'wicketkeeper' then
                0.05 * experience_score + 0.05 * age_score + 0.40 * coalesce(batting_score, 50)
                + 0.30 * form_score + 0.10 * 50 + 0.10 * 50
            else
                0.05 * experience_score + 0.05 * age_score + 0.20 * coalesce(batting_score, 50)
                + 0.20 * coalesce(bowling_score, 50) + 0.25 * form_score + 0.10 * 50 + 0.15 * 50
        end * confidence,
        1
    ) as overall_rating,
    -- Raw metrics for display
    career_innings_batted_before,
    career_runs_before,
    round(career_batting_avg, 2) as career_batting_avg,
    round(career_batting_sr, 2) as career_batting_sr,
    career_innings_bowled_before,
    career_wickets_before,
    round(career_bowling_econ, 2) as career_bowling_econ,
    round(career_bowling_sr, 2) as career_bowling_sr,
    current_timestamp as _loaded_at
from normalized
