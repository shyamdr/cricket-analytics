-- Staged weather data from Open-Meteo API.
-- Parses hourly JSON arrays and extracts match-time window (18:00–21:00 local).
-- Most IPL matches start at 19:30 IST; we average hours 18–21 as the match window.
-- Returns empty result set if bronze.weather doesn't exist yet.
{% if source_exists('bronze', 'weather') %}

with raw as (
    select
        match_id,
        match_date,
        latitude,
        longitude,
        elevation,
        timezone,
        utc_offset_seconds,
        -- Parse hourly JSON arrays
        json_extract(hourly_json, '$.time')                         as h_time,
        json_extract(hourly_json, '$.temperature_2m')               as h_temp,
        json_extract(hourly_json, '$.relative_humidity_2m')         as h_humidity,
        json_extract(hourly_json, '$.dew_point_2m')                 as h_dew_point,
        json_extract(hourly_json, '$.apparent_temperature')         as h_apparent_temp,
        json_extract(hourly_json, '$.wet_bulb_temperature_2m')      as h_wet_bulb_temp,
        json_extract(hourly_json, '$.precipitation')                as h_precipitation,
        json_extract(hourly_json, '$.weather_code')                 as h_weather_code,
        json_extract(hourly_json, '$.pressure_msl')                 as h_pressure_msl,
        json_extract(hourly_json, '$.cloud_cover')                  as h_cloud_cover,
        json_extract(hourly_json, '$.cloud_cover_low')              as h_cloud_cover_low,
        json_extract(hourly_json, '$.wind_speed_10m')               as h_wind_speed,
        json_extract(hourly_json, '$.wind_direction_10m')           as h_wind_direction,
        json_extract(hourly_json, '$.wind_gusts_10m')               as h_wind_gusts,
        json_extract(hourly_json, '$.is_day')                       as h_is_day,
        -- Parse daily JSON
        json_extract(daily_json, '$.temperature_2m_max[0]')         as daily_temp_max,
        json_extract(daily_json, '$.temperature_2m_min[0]')         as daily_temp_min,
        json_extract(daily_json, '$.precipitation_sum[0]')          as daily_precipitation_sum,
        json_extract(daily_json, '$.precipitation_hours[0]')        as daily_precipitation_hours,
        json_extract(daily_json, '$.sunrise[0]')                    as daily_sunrise,
        json_extract(daily_json, '$.sunset[0]')                     as daily_sunset,
        json_extract(daily_json, '$.wind_speed_10m_max[0]')         as daily_wind_speed_max,
        json_extract(daily_json, '$.wind_direction_10m_dominant[0]') as daily_wind_direction_dominant,
        json_extract(daily_json, '$.weather_code[0]')               as daily_weather_code,
        hourly_json,
        daily_json,
        _loaded_at,
        _run_id
    from {{ source('bronze', 'weather') }}
),

-- Extract match-time window: hours 18–21 (indices 18–21 in the 0-indexed hourly array)
-- This covers 18:00–21:59 local time, which spans most IPL match start times (19:30 IST)
match_window as (
    select
        match_id,
        match_date,
        latitude,
        longitude,
        elevation,
        timezone,
        utc_offset_seconds,
        -- Average temperature metrics over match window
        round(
            (cast(json_extract(h_temp, '$[18]') as double) +
             cast(json_extract(h_temp, '$[19]') as double) +
             cast(json_extract(h_temp, '$[20]') as double) +
             cast(json_extract(h_temp, '$[21]') as double)) / 4.0, 1
        ) as temperature_2m,
        round(
            (cast(json_extract(h_humidity, '$[18]') as double) +
             cast(json_extract(h_humidity, '$[19]') as double) +
             cast(json_extract(h_humidity, '$[20]') as double) +
             cast(json_extract(h_humidity, '$[21]') as double)) / 4.0, 1
        ) as relative_humidity_2m,
        round(
            (cast(json_extract(h_dew_point, '$[18]') as double) +
             cast(json_extract(h_dew_point, '$[19]') as double) +
             cast(json_extract(h_dew_point, '$[20]') as double) +
             cast(json_extract(h_dew_point, '$[21]') as double)) / 4.0, 1
        ) as dew_point_2m,
        round(
            (cast(json_extract(h_apparent_temp, '$[18]') as double) +
             cast(json_extract(h_apparent_temp, '$[19]') as double) +
             cast(json_extract(h_apparent_temp, '$[20]') as double) +
             cast(json_extract(h_apparent_temp, '$[21]') as double)) / 4.0, 1
        ) as apparent_temperature,
        round(
            (cast(json_extract(h_wet_bulb_temp, '$[18]') as double) +
             cast(json_extract(h_wet_bulb_temp, '$[19]') as double) +
             cast(json_extract(h_wet_bulb_temp, '$[20]') as double) +
             cast(json_extract(h_wet_bulb_temp, '$[21]') as double)) / 4.0, 1
        ) as wet_bulb_temperature_2m,
        -- Sum precipitation over match window
        round(
            cast(json_extract(h_precipitation, '$[18]') as double) +
            cast(json_extract(h_precipitation, '$[19]') as double) +
            cast(json_extract(h_precipitation, '$[20]') as double) +
            cast(json_extract(h_precipitation, '$[21]') as double), 2
        ) as precipitation_match_window,
        -- Most common weather code in window (use hour 20 = 20:00 as representative)
        cast(json_extract(h_weather_code, '$[20]') as integer) as weather_code,
        round(
            (cast(json_extract(h_pressure_msl, '$[18]') as double) +
             cast(json_extract(h_pressure_msl, '$[19]') as double) +
             cast(json_extract(h_pressure_msl, '$[20]') as double) +
             cast(json_extract(h_pressure_msl, '$[21]') as double)) / 4.0, 1
        ) as pressure_msl,
        round(
            (cast(json_extract(h_cloud_cover, '$[18]') as double) +
             cast(json_extract(h_cloud_cover, '$[19]') as double) +
             cast(json_extract(h_cloud_cover, '$[20]') as double) +
             cast(json_extract(h_cloud_cover, '$[21]') as double)) / 4.0, 1
        ) as cloud_cover,
        round(
            (cast(json_extract(h_cloud_cover_low, '$[18]') as double) +
             cast(json_extract(h_cloud_cover_low, '$[19]') as double) +
             cast(json_extract(h_cloud_cover_low, '$[20]') as double) +
             cast(json_extract(h_cloud_cover_low, '$[21]') as double)) / 4.0, 1
        ) as cloud_cover_low,
        round(
            (cast(json_extract(h_wind_speed, '$[18]') as double) +
             cast(json_extract(h_wind_speed, '$[19]') as double) +
             cast(json_extract(h_wind_speed, '$[20]') as double) +
             cast(json_extract(h_wind_speed, '$[21]') as double)) / 4.0, 1
        ) as wind_speed_10m,
        -- Wind direction: use hour 20 as representative (circular average is complex)
        cast(json_extract(h_wind_direction, '$[20]') as integer) as wind_direction_10m,
        round(
            (cast(json_extract(h_wind_gusts, '$[18]') as double) +
             cast(json_extract(h_wind_gusts, '$[19]') as double) +
             cast(json_extract(h_wind_gusts, '$[20]') as double) +
             cast(json_extract(h_wind_gusts, '$[21]') as double)) / 4.0, 1
        ) as wind_gusts_10m,
        -- is_day at 20:00 (most matches are in progress at this hour)
        cast(json_extract(h_is_day, '$[20]') as integer) as is_day,
        -- Daily summary fields
        cast(daily_temp_max as double) as daily_temp_max,
        cast(daily_temp_min as double) as daily_temp_min,
        cast(daily_precipitation_sum as double) as daily_precipitation_sum,
        cast(daily_precipitation_hours as double) as daily_precipitation_hours,
        replace(cast(daily_sunrise as varchar), '"', '') as sunrise,
        replace(cast(daily_sunset as varchar), '"', '') as sunset,
        cast(daily_wind_speed_max as double) as daily_wind_speed_max,
        cast(daily_wind_direction_dominant as integer) as daily_wind_direction_dominant,
        cast(daily_weather_code as integer) as daily_weather_code,
        -- Keep raw JSON for debugging
        hourly_json,
        daily_json,
        cast(_loaded_at as timestamp) as _loaded_at,
        _run_id
    from raw
)

select * from match_window

{% else %}
-- Source table does not exist yet — return empty with correct schema
select
    null::varchar   as match_id,
    null::varchar   as match_date,
    null::double    as latitude,
    null::double    as longitude,
    null::double    as elevation,
    null::varchar   as timezone,
    null::integer   as utc_offset_seconds,
    null::double    as temperature_2m,
    null::double    as relative_humidity_2m,
    null::double    as dew_point_2m,
    null::double    as apparent_temperature,
    null::double    as wet_bulb_temperature_2m,
    null::double    as precipitation_match_window,
    null::integer   as weather_code,
    null::double    as pressure_msl,
    null::double    as cloud_cover,
    null::double    as cloud_cover_low,
    null::double    as wind_speed_10m,
    null::integer   as wind_direction_10m,
    null::double    as wind_gusts_10m,
    null::integer   as is_day,
    null::double    as daily_temp_max,
    null::double    as daily_temp_min,
    null::double    as daily_precipitation_sum,
    null::double    as daily_precipitation_hours,
    null::varchar   as sunrise,
    null::varchar   as sunset,
    null::double    as daily_wind_speed_max,
    null::integer   as daily_wind_direction_dominant,
    null::integer   as daily_weather_code,
    null::varchar   as hourly_json,
    null::varchar   as daily_json,
    null::timestamp as _loaded_at,
    null::varchar   as _run_id
where false
{% endif %}
