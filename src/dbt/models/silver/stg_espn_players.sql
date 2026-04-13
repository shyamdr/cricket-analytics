
-- Staged ESPN player biographical data.
-- One row per player (dimension table). Keyed by espn_player_id.
-- Returns empty result set if bronze.espn_players doesn't exist yet.
{% if source_exists('bronze', 'espn_players') %}
select
    espn_player_id,
    player_name,
    player_long_name,
    mobile_name,
    index_name,
    batting_name,
    fielding_name,
    slug,
    gender,
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
    date_of_death_year,
    date_of_death_month,
    date_of_death_day,
    country_team_id,
    -- Styles (JSON arrays stored as strings)
    batting_styles,
    bowling_styles,
    long_batting_styles,
    long_bowling_styles,
    playing_roles,
    player_role_type_ids,
    -- Images
    image_url,
    headshot_image_url,
    -- Audit
    current_timestamp as _loaded_at

from {{ source('bronze', 'espn_players') }}
{% else %}
select
    null::bigint as espn_player_id,
    null::varchar as player_name,
    null::varchar as player_long_name,
    null::varchar as mobile_name,
    null::varchar as index_name,
    null::varchar as batting_name,
    null::varchar as fielding_name,
    null::varchar as slug,
    null::varchar as gender,
    null::boolean as is_overseas,
    null::integer as date_of_birth_year,
    null::integer as date_of_birth_month,
    null::integer as date_of_birth_day,
    null::date as date_of_birth,
    null::integer as date_of_death_year,
    null::integer as date_of_death_month,
    null::integer as date_of_death_day,
    null::bigint as country_team_id,
    null::varchar as batting_styles,
    null::varchar as bowling_styles,
    null::varchar as long_batting_styles,
    null::varchar as long_bowling_styles,
    null::varchar as playing_roles,
    null::varchar as player_role_type_ids,
    null::varchar as image_url,
    null::varchar as headshot_image_url,
    current_timestamp as _loaded_at
where false
{% endif %}
