-- Staged ESPN per-ball commentary data.
-- Grain: one row per ball. Contains commentary text, dismissal descriptions,
-- fielding events (dropped catches, run-out chances, stumping chances, DRS reviews),
-- and smart stats.
-- Returns empty result set if bronze.espn_ball_commentary doesn't exist yet.
{% if source_exists('bronze', 'espn_ball_commentary') %}
select
    espn_ball_id,
    cricsheet_match_id as match_id,
    espn_match_id,
    inning_number,
    over_number,
    ball_number,
    -- Commentary text
    title as ball_title,
    commentary_text,
    pre_text,
    post_text,
    batsman_stat_text,
    bowler_stat_text,
    -- Smart stats (raw JSON — 0.78% coverage, kept for preservation)
    smart_stats as smart_stat_raw_json,
    -- Dismissal text (parsed from JSON)
    try_cast(dismissal_text::json->>'short' as varchar) as espn_dismissal_text_short,
    try_cast(dismissal_text::json->>'long' as varchar) as espn_dismissal_text_long,
    try_cast(dismissal_text::json->>'commentary' as varchar) as espn_dismissal_text_commentary,
    try_cast(dismissal_text::json->>'fielderText' as varchar) as espn_dismissal_fielder_text,
    try_cast(dismissal_text::json->>'bowlerText' as varchar) as espn_dismissal_bowler_text,
    -- Fielding events (parsed from events JSON array)
    -- DROPPED_CATCH
    case when events like '%DROPPED_CATCH%' then true else false end as had_dropped_catch,
    -- Extract first dropped-catch fielder name(s)
    case
        when events like '%DROPPED_CATCH%' then (
            select string_agg(
                try_cast(f->>'name' as varchar), ', '
            )
            from (
                select unnest(
                    from_json(
                        try_cast(e->>'fielders' as varchar),
                        '["json"]'
                    )
                ) as f
                from (
                    select unnest(from_json(events, '["json"]')) as e
                ) sub
                where try_cast(e->>'type' as varchar) = 'DROPPED_CATCH'
                limit 1
            ) sub2
        )
    end as dropped_catch_fielders,
    -- DRS_REVIEW
    case when events like '%DRS_REVIEW%' then true else false end as had_drs_review,
    case
        when events like '%DRS_REVIEW%' then (
            select try_cast(e->>'isSuccessful' as boolean)
            from (select unnest(from_json(events, '["json"]')) as e) sub
            where try_cast(e->>'type' as varchar) = 'DRS_REVIEW'
            limit 1
        )
    end as drs_review_successful,
    -- RUN_OUT_CHANCE
    case when events like '%RUN_OUT_CHANCE%' then true else false end as had_run_out_chance,
    case
        when events like '%RUN_OUT_CHANCE%' then (
            select string_agg(
                try_cast(f->>'name' as varchar), ', '
            )
            from (
                select unnest(
                    from_json(
                        try_cast(e->>'fielders' as varchar),
                        '["json"]'
                    )
                ) as f
                from (
                    select unnest(from_json(events, '["json"]')) as e
                ) sub
                where try_cast(e->>'type' as varchar) = 'RUN_OUT_CHANCE'
                limit 1
            ) sub2
        )
    end as run_out_chance_fielders,
    -- STUMPING_CHANCE
    case when events like '%STUMPING_CHANCE%' then true else false end as had_stumping_chance,
    case
        when events like '%STUMPING_CHANCE%' then (
            select try_cast(f->>'name' as varchar)
            from (
                select unnest(
                    from_json(
                        try_cast(e->>'fielders' as varchar),
                        '["json"]'
                    )
                ) as f
                from (
                    select unnest(from_json(events, '["json"]')) as e
                ) sub
                where try_cast(e->>'type' as varchar) = 'STUMPING_CHANCE'
                limit 1
            ) sub2
            limit 1
        )
    end as stumping_chance_fielder,
    -- PLAYER_REPLACEMENT
    case when events like '%PLAYER_REPLACEMENT%' then true else false end as had_player_replacement,
    -- Raw JSON blobs (for deep queries)
    events as events_json,
    dismissal_text as dismissal_text_json,
    -- Over summary (parsed — only populated on last ball of each over)
    try_cast(over_summary::json->>'isMaiden' as boolean) as is_maiden_over,
    try_cast(over_summary::json->>'overRuns' as integer) as over_runs_total,
    try_cast(over_summary::json->>'overWickets' as integer) as over_wickets_total,
    try_cast(over_summary::json->>'isComplete' as boolean) as is_complete_over,
    -- Comment images (raw JSON — UI only, kept for completeness)
    comment_images as comment_images_json,
    -- Audit
    current_timestamp as _loaded_at
from {{ source('bronze', 'espn_ball_commentary') }}
{% else %}
select
    null::bigint as espn_ball_id,
    null::varchar as match_id,
    null::bigint as espn_match_id,
    null::bigint as inning_number,
    null::bigint as over_number,
    null::bigint as ball_number,
    null::varchar as ball_title,
    null::varchar as commentary_text,
    null::varchar as pre_text,
    null::varchar as post_text,
    null::varchar as batsman_stat_text,
    null::varchar as bowler_stat_text,
    null::varchar as smart_stat_raw_json,
    null::varchar as espn_dismissal_text_short,
    null::varchar as espn_dismissal_text_long,
    null::varchar as espn_dismissal_text_commentary,
    null::varchar as espn_dismissal_fielder_text,
    null::varchar as espn_dismissal_bowler_text,
    null::boolean as had_dropped_catch,
    null::varchar as dropped_catch_fielders,
    null::boolean as had_drs_review,
    null::boolean as drs_review_successful,
    null::boolean as had_run_out_chance,
    null::varchar as run_out_chance_fielders,
    null::boolean as had_stumping_chance,
    null::varchar as stumping_chance_fielder,
    null::boolean as had_player_replacement,
    null::varchar as events_json,
    null::varchar as dismissal_text_json,
    null::boolean as is_maiden_over,
    null::integer as over_runs_total,
    null::integer as over_wickets_total,
    null::boolean as is_complete_over,
    null::varchar as comment_images_json,
    current_timestamp as _loaded_at
where false
{% endif %}
