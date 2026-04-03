-- Staged hourly weather data from Open-Meteo API.
-- Explodes hourly JSON into 24 rows per match (one per hour of the day).
-- Hourly variables only — daily summary is in stg_weather_daily.
{% if source_exists('bronze', 'weather') %}

with hours as (
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
        _loaded_at,
        _run_id
    from {{ source('bronze', 'weather') }}
)

select
    r.match_id,
    r.match_date,
    h.hour_idx as hour_local,
    r.latitude,
    r.longitude,
    r.elevation,
    r.timezone,
    r.utc_offset_seconds,

    -- Core cricket-relevant
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

    -- Extended (stored for completeness)
    cast(json_extract(r.hourly_json, '$.' || 'rain[' || h.hour_idx || ']') as double) as rain,
    cast(json_extract(r.hourly_json, '$.' || 'surface_pressure[' || h.hour_idx || ']') as double) as surface_pressure,
    cast(json_extract(r.hourly_json, '$.' || 'cloud_cover_mid[' || h.hour_idx || ']') as double) as cloud_cover_mid,
    cast(json_extract(r.hourly_json, '$.' || 'cloud_cover_high[' || h.hour_idx || ']') as double) as cloud_cover_high,
    cast(json_extract(r.hourly_json, '$.' || 'vapour_pressure_deficit[' || h.hour_idx || ']') as double) as vapour_pressure_deficit,
    cast(json_extract(r.hourly_json, '$.' || 'soil_temperature_0_to_7cm[' || h.hour_idx || ']') as double) as soil_temperature_0_to_7cm,
    cast(json_extract(r.hourly_json, '$.' || 'soil_moisture_0_to_7cm[' || h.hour_idx || ']') as double) as soil_moisture_0_to_7cm,
    cast(json_extract(r.hourly_json, '$.' || 'sunshine_duration[' || h.hour_idx || ']') as double) as sunshine_duration,
    cast(json_extract(r.hourly_json, '$.' || 'shortwave_radiation[' || h.hour_idx || ']') as double) as shortwave_radiation,

    cast(r._loaded_at as timestamp) as _loaded_at,
    r._run_id

from raw r
cross join hours h

{% else %}
select
    null::varchar as match_id, null::varchar as match_date, null::integer as hour_local,
    null::double as latitude, null::double as longitude, null::double as elevation,
    null::varchar as timezone, null::integer as utc_offset_seconds,
    null::double as temperature_2m, null::double as relative_humidity_2m,
    null::double as dew_point_2m, null::double as apparent_temperature,
    null::double as wet_bulb_temperature_2m, null::double as precipitation,
    null::integer as weather_code, null::double as pressure_msl,
    null::double as cloud_cover, null::double as cloud_cover_low,
    null::double as wind_speed_10m, null::integer as wind_direction_10m,
    null::double as wind_gusts_10m, null::integer as is_day,
    null::double as rain, null::double as surface_pressure,
    null::double as cloud_cover_mid, null::double as cloud_cover_high,
    null::double as vapour_pressure_deficit, null::double as soil_temperature_0_to_7cm,
    null::double as soil_moisture_0_to_7cm, null::double as sunshine_duration,
    null::double as shortwave_radiation,
    null::timestamp as _loaded_at, null::varchar as _run_id
where false
{% endif %}
