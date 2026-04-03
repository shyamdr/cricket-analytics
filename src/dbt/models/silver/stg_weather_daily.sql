-- Staged daily weather summary from Open-Meteo API.
-- One row per match. Daily aggregate variables only.
-- Hourly detail is in stg_weather_hourly.
{% if source_exists('bronze', 'weather') %}

select
    match_id,
    match_date,
    latitude,
    longitude,
    elevation,
    timezone,
    utc_offset_seconds,

    cast(json_extract(daily_json, '$.temperature_2m_max[0]') as double) as temp_max,
    cast(json_extract(daily_json, '$.temperature_2m_min[0]') as double) as temp_min,
    cast(json_extract(daily_json, '$.apparent_temperature_max[0]') as double) as apparent_temp_max,
    cast(json_extract(daily_json, '$.apparent_temperature_min[0]') as double) as apparent_temp_min,
    cast(json_extract(daily_json, '$.precipitation_sum[0]') as double) as precipitation_sum,
    cast(json_extract(daily_json, '$.precipitation_hours[0]') as double) as precipitation_hours,
    cast(json_extract(daily_json, '$.rain_sum[0]') as double) as rain_sum,
    replace(cast(json_extract(daily_json, '$.sunrise[0]') as varchar), '"', '') as sunrise,
    replace(cast(json_extract(daily_json, '$.sunset[0]') as varchar), '"', '') as sunset,
    cast(json_extract(daily_json, '$.sunshine_duration[0]') as double) as sunshine_duration,
    cast(json_extract(daily_json, '$.daylight_duration[0]') as double) as daylight_duration,
    cast(json_extract(daily_json, '$.wind_speed_10m_max[0]') as double) as wind_speed_max,
    cast(json_extract(daily_json, '$.wind_gusts_10m_max[0]') as double) as wind_gusts_max,
    cast(json_extract(daily_json, '$.wind_direction_10m_dominant[0]') as integer) as wind_direction_dominant,
    cast(json_extract(daily_json, '$.shortwave_radiation_sum[0]') as double) as shortwave_radiation_sum,
    cast(json_extract(daily_json, '$.weather_code[0]') as integer) as weather_code,

    cast(_loaded_at as timestamp) as _loaded_at,
    _run_id

from {{ source('bronze', 'weather') }}

{% else %}
select
    null::varchar as match_id, null::varchar as match_date,
    null::double as latitude, null::double as longitude, null::double as elevation,
    null::varchar as timezone, null::integer as utc_offset_seconds,
    null::double as temp_max, null::double as temp_min,
    null::double as apparent_temp_max, null::double as apparent_temp_min,
    null::double as precipitation_sum, null::double as precipitation_hours,
    null::double as rain_sum,
    null::varchar as sunrise, null::varchar as sunset,
    null::double as sunshine_duration, null::double as daylight_duration,
    null::double as wind_speed_max, null::double as wind_gusts_max,
    null::integer as wind_direction_dominant, null::double as shortwave_radiation_sum,
    null::integer as weather_code,
    null::timestamp as _loaded_at, null::varchar as _run_id
where false
{% endif %}
