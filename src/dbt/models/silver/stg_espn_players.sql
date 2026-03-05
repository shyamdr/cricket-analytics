-- Staged ESPN player biographical data.
-- One row per player per match appearance (captures role changes across matches).
-- Returns empty result set if bronze.espn_players doesn't exist yet.
{% if source_exists('bronze', 'espn_players') %}
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
{% else %}
select
    null::bigint as espn_player_id,
    null::bigint as espn_match_id,
    null::varchar as player_name,
    null::varchar as player_long_name,
    null::varchar as team_name,
    null::varchar as match_role_code,
    null::boolean as is_overseas,
    null::integer as date_of_birth_year,
    null::integer as date_of_birth_month,
    null::integer as date_of_birth_day,
    null::date as date_of_birth,
    null::bigint as country_team_id,
    null::varchar as batting_styles,
    null::varchar as bowling_styles,
    null::varchar as long_batting_styles,
    null::varchar as long_bowling_styles,
    null::varchar as playing_roles,
    current_timestamp as _loaded_at
where false
{% endif %}
