-- Staged ESPN player biographical data.
-- One row per player per match appearance (captures role changes across matches).
-- For a deduplicated player dimension, see gold layer.
select
    espn_player_id,
    espn_match_id,
    player_name,
    player_long_name,
    team_name,
    match_role_code,
    is_overseas,
    -- Biographical
    date_of_birth_year,
    date_of_birth_month,
    date_of_birth_day,
    case
        when date_of_birth_year is not null
            and date_of_birth_month is not null
            and date_of_birth_day is not null
        then make_date(date_of_birth_year, date_of_birth_month, date_of_birth_day)
        else null
    end as date_of_birth,
    country_team_id,
    -- Styles (JSON arrays stored as strings)
    batting_styles,
    bowling_styles,
    long_batting_styles,
    long_bowling_styles,
    playing_roles,
    -- Audit
    current_timestamp as _loaded_at

from {{ source('bronze', 'espn_players') }}
