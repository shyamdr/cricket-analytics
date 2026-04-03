-- Staged weather data from Open-Meteo API.
-- Explodes hourly JSON into 24 rows per match (one per hour of the day).
-- Daily summary fields are repeated on every row for single-table convenience.
-- Returns empty result set if bronze.weather doesn't exist yet.
{% if source_exists('bronze', 'weather') %}

with hours as (
    -- Generate 24 hour indices (0-23)
    select unnest(generate_series(0, 23)) as hour_idx
),

raw as (
    select
        match_id,
        match_date,
        latitude,
        longitude,
        elevation,
        timezone,
        utc_offset_seconds,
        hourly_json,
        daily_json,
        _loaded_at,
        _run_id
    from {{ source('bronze', 'weather') }}
),

exploded as (
    select
        r.match_id,
        r.match_date,
        r.latitude,
        r.longitude,
        r.elevation,
        r.timezone,
        r.utc_offset_seconds,
        h.hour_idx as hour_local,

        -- Hourly variables (core cricket-relevant)
        cast(json_extract(r.hourly_json, '$.' || 'temperature_2m[' || h.hour_idx || ']') as double) as temperature_2m,
        cast(json_extract(r.hourly_json, '$.' || 'relative_humidity_2m[' || h.hour_idx || ']') as double) as relative_humidity_2m,
        cast(json_extract(r.hourly_json, '$.' || 'dew_point_2m[' || h.hour_idx || ']') as double) as dew_point_2m,
        cast(json_extract(r.hourly_json, '$.' || 'apparent_temperature[' || h.hour_idx || ']') as double) as apparent_temperature,
        cast(json_extract(r.hourly_json, '$.' || 'wet_bulb_temperature_2m[' || h.hour_idx || ']') as double) as wet_bulb_temperature_2m,
        cast(json_extract(r.hourly_json, '$.' || 'precipitation[' || h.hour_idx || ']') as double) as precipitation,
        cast(json_extract(r.hourly_json, '$.' || 'weather_code[' || h.hour_idx || ']') as integer) as weather_code,
        cast(json_extract(r.hourly_json, '$.' || 'pressure_msl[' || h.hour_idx || ']') as double) as pressure_msl,
        cast(json_extract(r.hourly_json, '$.' || 'cloud_cover[' || h.hour_idx || ']') as double) as cloud_cover,
        cast(json_extract(r.hourly_json, '$.' || 'cloud_cover_low[' || h.hour_idx || ']') as double) as cloud_cover_low,
        cast(json_extract(r.hourly_json, '$.' || 'wind_speed_10m[' || h.hour_idx || ']') as double) as wind_speed_10m,
        cast(json_extract(r.hourly_json, '$.' || 'wind_direction_10m[' || h.hour_idx || ']') as integer) as wind_direction_10m,
        cast(json_extract(r.hourly_json, '$.' || 'wind_gusts_10m[' || h.hour_idx || ']') as double) as wind_gusts_10m,
        cast(json_extract(r.hourly_json, '$.' || 'is_day[' || h.hour_idx || ']') as integer) as is_day,

        -- Hourly variables (bronze-only, stored for completeness)
        cast(json_extract(r.hourly_json, '$.' || 'rain[' || h.hour_idx || ']') as double) as rain,
        cast(json_extract(r.hourly_json, '$.' || 'surface_pressure[' || h.hour_idx || ']') as double) as surface_pressure,
        cast(json_extract(r.hourly_json, '$.' || 'cloud_cover_mid[' || h.hour_idx || ']') as double) as cloud_cover_mid,
        cast(json_extract(r.hourly_json, '$.' || 'cloud_cover_high[' || h.hour_idx || ']') as double) as cloud_cover_high,
        cast(json_extract(r.hourly_json, '$.' || 'vapour_pressure_deficit[' || h.hour_idx || ']') as double) as vapour_pressure_deficit,
        cast(json_extract(r.hourly_json, '$.' || 'soil_temperature_0_to_7cm[' || h.hour_idx || ']') as double) as soil_temperature_0_to_7cm,
        cast(json_extract(r.hourly_json, '$.' || 'soil_moisture_0_to_7cm[' || h.hour_idx || ']') as double) as soil_moisture_0_to_7cm,
        cast(json_extract(r.hourly_json, '$.' || 'sunshine_duration[' || h.hour_idx || ']') as double) as sunshine_duration,
        cast(json_extract(r.hourly_json, '$.' || 'shortwave_radiation[' || h.hour_idx || ']') as double) as shortwave_radiation,

        -- Daily summary (repeated on every row — same value for all 24 hours of a match)
        cast(json_extract(r.daily_json, '$.temperature_2m_max[0]') as double) as daily_temp_max,
        cast(json_extract(r.daily_json, '$.temperature_2m_min[0]') as double) as daily_temp_min,
        cast(json_extract(r.daily_json, '$.precipitation_sum[0]') as double) as daily_precipitation_sum,
        cast(json_extract(r.daily_json, '$.precipitation_hours[0]') as double) as daily_precipitation_hours,
        replace(cast(json_extract(r.daily_json, '$.sunrise[0]') as varchar), '"', '') as daily_sunrise,
        replace(cast(json_extract(r.daily_json, '$.sunset[0]') as varchar), '"', '') as daily_sunset,
        cast(json_extract(r.daily_json, '$.wind_speed_10m_max[0]') as double) as daily_wind_speed_max,
        cast(json_extract(r.daily_json, '$.wind_direction_10m_dominant[0]') as integer) as daily_wind_direction_dominant,
        cast(json_extract(r.daily_json, '$.weather_code[0]') as integer) as daily_weather_code,

        -- Audit
        cast(r._loaded_at as timestamp) as _loaded_at,
        r._run_id

    from raw r
    cross join hours h
)

select * from exploded

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
    null::integer   as hour_local,
    null::double    as temperature_2m,
    null::double    as relative_humidity_2m,
    null::double    as dew_point_2m,
    null::double    as apparent_temperature,
    null::double    as wet_bulb_temperature_2m,
    null::double    as precipitation,
    null::integer   as weather_code,
    null::double    as pressure_msl,
    null::double    as cloud_cover,
    null::double    as cloud_cover_low,
    null::double    as wind_speed_10m,
    null::integer   as wind_direction_10m,
    null::double    as wind_gusts_10m,
    null::integer   as is_day,
    null::double    as rain,
    null::double    as surface_pressure,
    null::double    as cloud_cover_mid,
    null::double    as cloud_cover_high,
    null::double    as vapour_pressure_deficit,
    null::double    as soil_temperature_0_to_7cm,
    null::double    as soil_moisture_0_to_7cm,
    null::double    as sunshine_duration,
    null::double    as shortwave_radiation,
    null::double    as daily_temp_max,
    null::double    as daily_temp_min,
    null::double    as daily_precipitation_sum,
    null::double    as daily_precipitation_hours,
    null::varchar   as daily_sunrise,
    null::varchar   as daily_sunset,
    null::double    as daily_wind_speed_max,
    null::integer   as daily_wind_direction_dominant,
    null::integer   as daily_weather_code,
    null::timestamp as _loaded_at,
    null::varchar   as _run_id
where false
{% endif %}
