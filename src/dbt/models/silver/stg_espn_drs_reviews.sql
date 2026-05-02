-- Staged ESPN DRS reviews per innings.
-- Grain: one row per (espn_match_id, inning_number, review_number).
-- Extracted from stg_espn_innings.drs_reviews_json.
-- Returns empty result set if bronze.espn_innings doesn't exist yet.
{% if source_exists('bronze', 'espn_innings') %}
with innings as (
    select
        espn_match_id,
        inning_number,
        drs_reviews_json
    from {{ source('bronze', 'espn_innings') }}
    where drs_reviews_json is not null
      and drs_reviews_json != '[]'
),

unnested as (
    select
        i.espn_match_id,
        i.inning_number,
        unnest(from_json(i.drs_reviews_json, '["json"]')) as review
    from innings i
)

select
    espn_match_id,
    inning_number,
    row_number() over (
        partition by espn_match_id, inning_number
        order by try_cast(review->>'overs_actual' as double)
    ) as review_number,
    try_cast(review->>'review_side' as varchar) as review_side,
    try_cast(review->>'is_umpire_call' as boolean) as is_umpire_call,
    try_cast(review->>'remaining_count' as integer) as remaining_count,
    try_cast(review->>'original_decision' as varchar) as original_decision,
    try_cast(review->>'drs_decision' as varchar) as drs_decision,
    try_cast(review->>'overs_actual' as double) as overs_actual,
    current_timestamp as _loaded_at
from unnested
{% else %}
select
    null::bigint as espn_match_id,
    null::bigint as inning_number,
    null::bigint as review_number,
    null::varchar as review_side,
    null::boolean as is_umpire_call,
    null::integer as remaining_count,
    null::varchar as original_decision,
    null::varchar as drs_decision,
    null::double as overs_actual,
    current_timestamp as _loaded_at
where false
{% endif %}
