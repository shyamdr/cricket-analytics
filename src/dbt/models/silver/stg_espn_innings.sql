-- Staged ESPN innings-level enrichment data.
-- Contains partnerships, DRS reviews, phase breakdowns, and fielding metrics as JSON.
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
