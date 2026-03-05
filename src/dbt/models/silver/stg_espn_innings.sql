-- Staged ESPN innings-level enrichment data.
-- Contains partnerships, DRS reviews, phase breakdowns, and fielding metrics as JSON.
-- Returns empty result set if bronze.espn_innings doesn't exist yet.
{% if source_exists('bronze', 'espn_innings') %}
select
    espn_match_id,
    inning_number,
    batting_team,
    runs_saved,
    catches_dropped,
    -- JSON blobs for downstream unpacking
    batsmen_details_json,
    partnerships_json,
    drs_reviews_json,
    over_groups_json,
    -- Audit
    current_timestamp as _loaded_at

from {{ source('bronze', 'espn_innings') }}
{% else %}
select
    null::bigint as espn_match_id,
    null::integer as inning_number,
    null::varchar as batting_team,
    null::double as runs_saved,
    null::integer as catches_dropped,
    null::varchar as batsmen_details_json,
    null::varchar as partnerships_json,
    null::varchar as drs_reviews_json,
    null::varchar as over_groups_json,
    current_timestamp as _loaded_at
where false
{% endif %}
