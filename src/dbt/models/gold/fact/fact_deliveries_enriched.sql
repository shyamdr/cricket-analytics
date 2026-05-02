-- fact_deliveries_enriched (OBT — Event Spine)
-- =============================================================================
-- One row per delivery (super overs excluded), with every piece of context
-- pre-joined. See docs/obt-field-catalog.md for the full field inventory.
--
-- Source (per ADR-006 sibling rule):
--   stg_deliveries + stg_matches (silver) for ball events and match metadata.
--   dim_* tables used as lookup joins for denormalized context.
--   snapshot_player_career for rolling and career AS-OF-BEFORE columns.
--   ESPN silver models for spatial, commentary, fielding, and player context.
--
-- Grain: (match_id, innings, over_num, ball_num)
-- Materialization: incremental by match_id.
-- =============================================================================

{{
    config(
        materialized='incremental',
        unique_key=['match_id', 'innings', 'over_num', 'ball_num']
    )
}}

with base_deliveries as (
    select
        d.*,
        -- Pre-compute bowler-wicket flag (avoids Jinja string-escape issues in macros)
        case
            when d.is_wicket
                and d.wicket_kind not in (
                    'run out', 'retired hurt', 'retired out', 'obstructing the field'
                )
            then 1 else 0
        end as is_bowler_wicket
    from {{ ref('stg_deliveries') }} d
    where d.is_super_over = false
    {% if is_incremental() %}
        and d.match_id not in (select distinct match_id from {{ this }})
    {% endif %}
),

-- Match metadata from silver
match_ctx as (
    select
        m.match_id,
        m.season,
        m.match_date,
        m.city,
        m.venue,
        m.team1,
        m.team2,
        m.team_type,
        m.toss_winner,
        m.toss_decision,
        m.event_name,
        m.event_stage,
        m.event_group,
        m.match_type,
        m.gender,
        m.max_overs,
        m.player_of_match,
        m.event_match_number,
        m.outcome_winner,
        m.outcome_by_runs,
        m.outcome_by_wickets,
        m.outcome_method,
        m.outcome_result,
        m.outcome_eliminator,
        m.umpire_1,
        m.umpire_2,
        m.tv_umpire,
        m.reserve_umpire,
        m.match_referee
    from {{ ref('stg_matches') }} m
),

-- ESPN match enrichment
espn_match as (
    select * from {{ ref('stg_espn_matches') }}
),

-- ESPN ball-level spatial + shot data
espn_ball as (
    select * from {{ ref('stg_espn_ball_data') }}
),

-- ESPN ball commentary (deduplicated by espn_ball_id — rare duplicates from scraping)
espn_comm as (
    select *
    from (
        select *,
            row_number() over (partition by espn_ball_id order by espn_ball_id) as _rn
        from {{ ref('stg_espn_ball_commentary') }}
    )
    where _rn = 1
),

-- ESPN innings-level fielding
espn_inn as (
    select * from {{ ref('stg_espn_innings') }}
),

-- ESPN batting innings (batting position)
espn_bat_inn as (
    select * from {{ ref('stg_espn_batting_innings') }}
),

-- ESPN team players (per-match roles: captain, keeper)
espn_tp as (
    select * from {{ ref('stg_espn_team_players') }}
),

-- ESPN debut players
espn_debut as (
    select * from {{ ref('stg_espn_debut_players') }}
),

-- Player dimension (for batter/bowler attributes — deduplicated by name)
dim_p as (
    select *
    from (
        select *,
            row_number() over (partition by player_name order by player_id) as _rn
        from {{ ref('dim_players') }}
    )
    where _rn = 1
),

-- ESPN player bio (for handedness, styles, DOB, overseas)
espn_pl as (
    select * from {{ ref('stg_espn_players') }}
),

-- Venue dimension
dim_v as (
    select * from {{ ref('dim_venues') }}
),

-- Team dimension (for colors)
dim_t as (
    select team_name, primary_color from {{ ref('dim_teams') }}
),

-- Weather (match-start hour — use hour 14 as proxy for afternoon start)
weather_start as (
    select
        wh.match_id,
        wh.temperature_2m as weather_temp_c,
        wh.relative_humidity_2m as weather_humidity_pct,
        wh.dew_point_2m as weather_dew_point_c,
        wh.apparent_temperature as weather_apparent_temp_c,
        wh.precipitation as weather_precipitation_mm,
        wh.weather_code as weather_weather_code,
        wh.wind_speed_10m as weather_wind_speed_kmh,
        wh.wind_direction_10m as weather_wind_direction_deg,
        wh.wind_gusts_10m as weather_wind_gusts_kmh,
        wh.cloud_cover as weather_cloud_cover_pct,
        wh.is_day as weather_is_day,
        wd.temp_max as daily_temp_max_c,
        wd.temp_min as daily_temp_min_c,
        wd.wind_gusts_max as daily_wind_gusts_max_kmh,
        wd.precipitation_sum as daily_precipitation_sum_mm
    from {{ ref('stg_weather_hourly') }} wh
    left join {{ ref('stg_weather_daily') }} wd on wh.match_id = wd.match_id
    where wh.hour_local = 14
),

-- Snapshot: batter career state
snap_batter as (
    select * from {{ ref('snapshot_player_career') }}
),

-- Snapshot: bowler career state
snap_bowler as (
    select * from {{ ref('snapshot_player_career') }}
),

-- 1st innings total per match (for target/required run rate in 2nd innings)
first_innings_total as (
    select
        match_id,
        sum(total_runs) as first_innings_runs
    from base_deliveries
    where innings = 1
    group by match_id
),

-- Team name canonicalization (Delhi Daredevils → Delhi Capitals, etc.)
team_canonical as (
    select
        team_name as raw_name,
        coalesce(nullif(current_franchise_name, ''), team_name) as canonical_name
    from {{ ref('team_name_mappings') }}
    union all
    -- Teams not in the mapping seed keep their original name
    select distinct t.team_name, t.team_name
    from (
        select team1 as team_name from {{ ref('stg_matches') }}
        union
        select team2 from {{ ref('stg_matches') }}
    ) t
    left join {{ ref('team_name_mappings') }} tnm on t.team_name = tnm.team_name
    where tnm.team_name is null
),

-- =========================================================================
-- MAIN ASSEMBLY
-- =========================================================================
assembled as (
    select
        -- ========= Ball identity =========
        bd.match_id,
        mc.season,
        mc.match_date,
        bd.innings,
        bd.over_num,
        bd.ball_num,
        bd.batter,
        bd.bowler,
        bd.non_striker,

        -- ========= Match context =========
        bd.batting_team as batting_team_raw,
        coalesce(tc_bat.canonical_name, bd.batting_team) as batting_team,
        case when bd.batting_team = mc.team1 then mc.team2 else mc.team1 end as bowling_team_raw,
        coalesce(tc_bowl.canonical_name, case when bd.batting_team = mc.team1 then mc.team2 else mc.team1 end) as bowling_team,
        mc.city,
        mc.venue,
        mc.team1,
        mc.team2,
        mc.team_type,
        mc.toss_winner,
        mc.toss_decision,
        mc.event_name,
        mc.event_stage,
        mc.event_group,
        mc.match_type,
        mc.gender,
        mc.max_overs,

        -- ========= Match outcome (denormalized per ball) =========
        mc.player_of_match,
        mc.event_match_number,
        mc.outcome_winner,
        mc.outcome_by_runs,
        mc.outcome_by_wickets,
        mc.outcome_method,
        mc.outcome_result,
        mc.outcome_eliminator,

        -- ========= Umpires / officials =========
        mc.umpire_1,
        mc.umpire_2,
        mc.tv_umpire,
        mc.reserve_umpire,
        mc.match_referee,

        -- ========= Venue context =========
        dv.canonical_venue,
        dv.canonical_city,
        dv.latitude as venue_latitude,
        dv.longitude as venue_longitude,
        dv.formatted_address as venue_address,
        em.venue_timezone,
        em.ground_capacity,
        em.espn_ground_id,
        em.ground_name as espn_ground_name,
        em.ground_long_name as espn_ground_long_name,
        em.ground_country_name,
        em.ground_country_abbreviation,

        -- ========= ESPN match context =========
        em.espn_match_id,
        em.espn_series_id,
        em.floodlit,
        em.start_time as match_start_time,
        em.end_time as match_end_time,
        em.hours_info,
        em.international_class_id,
        em.sub_class_id,
        em.team1_captain,
        em.team2_captain,
        em.team1_keeper,
        em.team2_keeper,
        em.team1_is_home,
        em.team2_is_home,
        em.team1_long_name,
        em.team2_long_name,
        em.team1_abbreviation,
        em.team2_abbreviation,
        em.team1_points as team1_points_before_match,
        em.team2_points as team2_points_before_match,
        -- Team colors (from dim_teams, for UI rendering convenience)
        dt_bat.primary_color as batting_team_primary_color,
        dt_bowl.primary_color as bowling_team_primary_color,

        -- ========= MVP (match-level, denormalized) =========
        em.mvp_player_name as match_mvp_player_name,
        em.mvp_smart_runs as match_mvp_smart_runs,
        em.mvp_smart_wickets as match_mvp_smart_wickets,
        em.mvp_batting_impact as match_mvp_batting_impact,
        em.mvp_bowling_impact as match_mvp_bowling_impact,
        em.mvp_total_impact as match_mvp_total_impact,

        -- ========= Ball-level event columns (Cricsheet) =========
        bd.batter_runs,
        bd.extras_runs,
        bd.total_runs,
        bd.non_boundary,
        bd.extras_wides,
        bd.extras_noballs,
        bd.extras_byes,
        bd.extras_legbyes,
        bd.extras_penalty,
        bd.is_legal_delivery,
        bd.is_four,
        bd.is_six,
        bd.is_dot_ball,
        bd.is_wicket,
        bd.wicket_player_out,
        bd.wicket_kind,
        bd.wicket_fielder1,
        bd.wicket_fielder2,
        bd.is_bowler_wicket,

        -- ========= DRS review (Cricsheet per-ball) =========
        bd.review_by,
        bd.review_umpire,
        bd.review_batter,
        bd.review_decision,
        bd.review_type,
        bd.review_umpires_call,

        -- ========= Impact player replacement (Cricsheet per-ball) =========
        bd.replacement_player_in,
        bd.replacement_player_out,
        bd.replacement_team,
        bd.replacement_reason,

        -- ========= ESPN ball-level spatial / shot data =========
        eb.espn_ball_id,
        eb.overs_actual as overs_actual_espn,
        eb.batsman_player_id as espn_batsman_id,
        eb.bowler_player_id as espn_bowler_id,
        eb.non_striker_player_id as espn_non_striker_id,
        eb.out_player_id as espn_out_player_id,
        eb.dismissal_type as espn_dismissal_type_code,
        eb.wagon_x,
        eb.wagon_y,
        eb.wagon_zone,
        eb.pitch_line,
        eb.pitch_length,
        eb.shot_type,
        eb.shot_control,
        eb.ball_timestamp,
        eb.win_probability as espn_win_probability,
        eb.predicted_score as espn_predicted_score,
        -- ESPN duplicate ball-level fields (kept alongside Cricsheet for cross-validation + future ESPN-primary migration)
        eb.batsman_runs as espn_batsman_runs,
        eb.total_runs as espn_total_runs,
        eb.total_inning_runs as espn_total_inning_runs,
        eb.total_inning_wickets as espn_total_inning_wickets,
        eb.wides as espn_wides,
        eb.noballs as espn_noballs,
        eb.byes as espn_byes,
        eb.legbyes as espn_legbyes,
        eb.penalties as espn_penalties,

        -- ========= ESPN ball commentary =========
        ec.ball_title,
        ec.commentary_text,
        ec.pre_text,
        ec.post_text,
        ec.batsman_stat_text,
        ec.bowler_stat_text,
        ec.smart_stat_raw_json,
        ec.espn_dismissal_text_short,
        ec.espn_dismissal_text_long,
        ec.espn_dismissal_text_commentary,
        ec.espn_dismissal_fielder_text,
        ec.espn_dismissal_bowler_text,

        -- ========= Fielding events (ESPN commentary) =========
        ec.had_dropped_catch,
        ec.dropped_catch_fielders,
        ec.had_drs_review,
        ec.drs_review_successful,
        ec.had_run_out_chance,
        ec.run_out_chance_fielders,
        ec.had_stumping_chance,
        ec.stumping_chance_fielder,
        ec.had_player_replacement as espn_had_player_replacement,

        -- ========= Over summary (ESPN — last ball of over only) =========
        ec.is_maiden_over,
        ec.over_runs_total,
        ec.over_wickets_total,
        ec.is_complete_over,

        -- ========= Innings-level fielding (ESPN) =========
        ei.runs_saved as innings_runs_saved,
        ei.catches_dropped as innings_catches_dropped,

        -- ========= Batter context (ESPN player bio) =========
        batter_pl.espn_player_id as batter_espn_id,
        -- Clean JSON array strings: '["rhb"]' → 'rhb', '["ob", "lbg"]' → 'ob, lbg', '[]' → NULL
        nullif(replace(replace(replace(batter_pl.batting_styles, '["', ''), '"]', ''), '", "', ', '), '') as batter_batting_styles,
        nullif(replace(replace(replace(batter_pl.bowling_styles, '["', ''), '"]', ''), '", "', ', '), '') as batter_bowling_styles,
        nullif(replace(replace(replace(batter_pl.playing_roles, '["', ''), '"]', ''), '", "', ', '), '') as batter_playing_roles,
        batter_pl.is_overseas as batter_is_overseas,
        batter_pl.country_team_id as batter_country_team_id,
        batter_pl.date_of_birth as batter_date_of_birth,
        case
            when batter_pl.date_of_birth is not null
            then date_diff('year', batter_pl.date_of_birth, mc.match_date)
        end as batter_age_at_match,

        -- ========= Bowler context (ESPN player bio) =========
        bowler_pl.espn_player_id as bowler_espn_id,
        nullif(replace(replace(replace(bowler_pl.batting_styles, '["', ''), '"]', ''), '", "', ', '), '') as bowler_batting_styles,
        nullif(replace(replace(replace(bowler_pl.bowling_styles, '["', ''), '"]', ''), '", "', ', '), '') as bowler_bowling_styles,
        nullif(replace(replace(replace(bowler_pl.playing_roles, '["', ''), '"]', ''), '", "', ', '), '') as bowler_playing_roles,
        bowler_pl.is_overseas as bowler_is_overseas,
        bowler_pl.country_team_id as bowler_country_team_id,
        bowler_pl.date_of_birth as bowler_date_of_birth,
        case
            when bowler_pl.date_of_birth is not null
            then date_diff('year', bowler_pl.date_of_birth, mc.match_date)
        end as bowler_age_at_match,

        -- ========= Batting position (ESPN batting innings) =========
        ebi.batting_position as batter_batting_position,
        ebi.batted_type as batter_batted_type,
        ebi.minutes as batter_minutes_at_crease,

        -- ========= Per-match roles (ESPN team players) =========
        batter_tp.is_captain as batter_is_captain_this_match,
        batter_tp.is_keeper as batter_is_keeper_this_match,
        bowler_tp.is_captain as bowler_is_captain_this_match,

        -- ========= Debut flags (ESPN) =========
        case when batter_debut.espn_player_id is not null then true else false end as batter_is_debut_this_match,
        case when bowler_debut.espn_player_id is not null then true else false end as bowler_is_debut_this_match,

        -- ========= Weather at match start =========
        ws.weather_temp_c,
        ws.weather_humidity_pct,
        ws.weather_dew_point_c,
        ws.weather_apparent_temp_c,
        ws.weather_precipitation_mm,
        ws.weather_weather_code,
        ws.weather_wind_speed_kmh,
        ws.weather_wind_direction_deg,
        ws.weather_wind_gusts_kmh,
        ws.weather_cloud_cover_pct,
        ws.weather_is_day,
        ws.daily_temp_max_c,
        ws.daily_temp_min_c,
        ws.daily_wind_gusts_max_kmh,
        ws.daily_precipitation_sum_mm,

        -- ========= BATTER career state (from snapshot — ADR-007) =========
        sb.career_innings_batted_before as batter_career_innings_before,
        sb.career_runs_before as batter_career_runs_before,
        sb.career_balls_faced_before as batter_career_balls_faced_before,
        sb.career_fours_before as batter_career_fours_before,
        sb.career_sixes_before as batter_career_sixes_before,
        sb.career_dismissals_before as batter_career_dismissals_before,
        sb.rolling_10_runs as batter_rolling_10_runs,
        sb.rolling_10_balls_faced as batter_rolling_10_balls_faced,

        -- ========= BOWLER career state (from snapshot — ADR-007) =========
        sbw.career_innings_bowled_before as bowler_career_innings_before,
        sbw.career_legal_balls_bowled_before as bowler_career_legal_balls_before,
        sbw.career_runs_conceded_before as bowler_career_runs_conceded_before,
        sbw.career_wickets_before as bowler_career_wickets_before,
        sbw.rolling_10_wickets as bowler_rolling_10_wickets,
        sbw.rolling_10_runs_conceded as bowler_rolling_10_runs_conceded,
        sbw.rolling_10_legal_balls_bowled as bowler_rolling_10_legal_balls,

        -- ========= Chase context (2nd innings only) =========
        fit.first_innings_runs + 1 as target_score,
        case
            when bd.innings >= 2 and mc.max_overs is not null then
                mc.max_overs * 6
            else null
        end as total_balls_in_innings

    from base_deliveries bd
    join match_ctx mc on bd.match_id = mc.match_id
    left join espn_match em on bd.match_id = em.match_id
    left join espn_ball eb
        on bd.match_id = eb.match_id
        and bd.innings = eb.inning_number
        and bd.over_num = eb.over_number
        and bd.ball_num = eb.ball_number
    left join espn_comm ec on eb.espn_ball_id = ec.espn_ball_id
    left join espn_inn ei
        on em.espn_match_id = ei.espn_match_id
        and bd.innings = ei.inning_number
    -- Player dimension + ESPN bio (must come before joins that reference batter_pl/bowler_pl)
    left join dim_p batter_dim on bd.batter = batter_dim.player_name
    left join espn_pl batter_pl
        on batter_dim.key_cricinfo is not null
        and batter_pl.espn_player_id = try_cast(batter_dim.key_cricinfo as bigint)
    left join dim_p bowler_dim on bd.bowler = bowler_dim.player_name
    left join espn_pl bowler_pl
        on bowler_dim.key_cricinfo is not null
        and bowler_pl.espn_player_id = try_cast(bowler_dim.key_cricinfo as bigint)
    -- ESPN batting innings (batting position) — needs batter_pl.espn_player_id
    left join espn_bat_inn ebi
        on em.espn_match_id = ebi.espn_match_id
        and bd.innings = ebi.inning_number
        and batter_pl.espn_player_id = ebi.espn_player_id
    -- ESPN team players (per-match roles) — needs batter_pl/bowler_pl
    left join espn_tp batter_tp
        on em.espn_match_id = batter_tp.espn_match_id
        and batter_pl.espn_player_id = batter_tp.espn_player_id
    left join espn_tp bowler_tp
        on em.espn_match_id = bowler_tp.espn_match_id
        and bowler_pl.espn_player_id = bowler_tp.espn_player_id
    -- ESPN debut players — needs batter_pl/bowler_pl
    left join espn_debut batter_debut
        on em.espn_match_id = batter_debut.espn_match_id
        and batter_pl.espn_player_id = batter_debut.espn_player_id
    left join espn_debut bowler_debut
        on em.espn_match_id = bowler_debut.espn_match_id
        and bowler_pl.espn_player_id = bowler_debut.espn_player_id
    left join dim_v dv on mc.venue = dv.venue and mc.city = dv.city
    left join team_canonical tc_bat on bd.batting_team = tc_bat.raw_name
    left join team_canonical tc_bowl on (case when bd.batting_team = mc.team1 then mc.team2 else mc.team1 end) = tc_bowl.raw_name
    left join dim_t dt_bat on coalesce(tc_bat.canonical_name, bd.batting_team) = dt_bat.team_name
    left join dim_t dt_bowl on coalesce(tc_bowl.canonical_name, case when bd.batting_team = mc.team1 then mc.team2 else mc.team1 end) = dt_bowl.team_name
    left join weather_start ws on bd.match_id = ws.match_id
    left join snap_batter sb on bd.batter = sb.player_name and bd.match_id = sb.as_of_match_id
    left join snap_bowler sbw on bd.bowler = sbw.player_name and bd.match_id = sbw.as_of_match_id
    left join first_innings_total fit on bd.match_id = fit.match_id and bd.innings >= 2
)

-- =========================================================================
-- FINAL SELECT with derived columns
-- =========================================================================
select
    a.*,

    -- Phase classification (format-agnostic)
    case
        when max_overs = 20 then
            case
                when over_num between 0 and 5 then 'powerplay'
                when over_num between 6 and 14 then 'middle'
                when over_num between 15 and 19 then 'death'
            end
        when max_overs = 50 then
            case
                when over_num between 0 and 9 then 'powerplay'
                when over_num between 10 and 39 then 'middle'
                when over_num between 40 and 49 then 'death'
            end
        when max_overs = 100 then
            case
                when over_num between 0 and 5 then 'powerplay'
                when over_num between 6 and 11 then 'middle'
                when over_num between 12 and 16 then 'death'
            end
        else null
    end as phase,

    -- In-match running state
    {{ in_match_window('sum(total_runs)', partition_by='match_id, innings', order_by='over_num, ball_num') }} as team_score_at_ball,
    {{ in_match_window('sum(case when is_wicket then 1 else 0 end)', partition_by='match_id, innings', order_by='over_num, ball_num') }} as team_wickets_at_ball,
    {{ in_match_window('sum(case when is_legal_delivery then 1 else 0 end)', partition_by='match_id, innings', order_by='over_num, ball_num') }} as legal_balls_so_far_innings,
    {{ in_match_window('sum(batter_runs)', partition_by='match_id, innings, batter', order_by='over_num, ball_num') }} as batter_score_at_ball,
    {{ in_match_window('sum(case when is_legal_delivery then 1 else 0 end)', partition_by='match_id, innings, batter', order_by='over_num, ball_num') }} as batter_balls_faced_at_ball,
    {{ in_match_window('sum(batter_runs + extras_wides + extras_noballs)', partition_by='match_id, innings, bowler', order_by='over_num, ball_num') }} as bowler_runs_conceded_at_ball,
    {{ in_match_window('sum(case when is_legal_delivery then 1 else 0 end)', partition_by='match_id, innings, bowler', order_by='over_num, ball_num') }} as bowler_legal_balls_at_ball,
    {{ in_match_window('sum(is_bowler_wicket)', partition_by='match_id, innings, bowler', order_by='over_num, ball_num') }} as bowler_wickets_at_ball,

    -- Required run rate (2nd innings only)
    case
        when innings >= 2 and target_score is not null and total_balls_in_innings is not null then
            case
                when total_balls_in_innings - {{ in_match_window('sum(case when is_legal_delivery then 1 else 0 end)', partition_by='match_id, innings', order_by='over_num, ball_num') }} > 0
                then round(
                    (target_score - {{ in_match_window('sum(total_runs)', partition_by='match_id, innings', order_by='over_num, ball_num') }})
                    * 6.0
                    / (total_balls_in_innings - {{ in_match_window('sum(case when is_legal_delivery then 1 else 0 end)', partition_by='match_id, innings', order_by='over_num, ball_num') }}),
                    2
                )
            end
    end as required_run_rate,

    -- Balls remaining in innings (2nd innings only)
    case
        when innings >= 2 and total_balls_in_innings is not null then
            total_balls_in_innings - {{ in_match_window('sum(case when is_legal_delivery then 1 else 0 end)', partition_by='match_id, innings', order_by='over_num, ball_num') }}
    end as balls_remaining_in_innings,

    current_timestamp as _loaded_at

from assembled a
order by a.match_id, a.innings, a.over_num, a.ball_num
