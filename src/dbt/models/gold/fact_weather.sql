-- Weather fact table: one row per match per hour (24 rows per match).
-- Contains hourly weather conditions + daily summary on every row.
-- Join to dim_matches on match_id. Use hour_local + match start_time
-- to filter to actual match hours.
--
-- Example: get weather during a match
--   SELECT w.*
--   FROM fact_weather w
--   JOIN dim_matches m ON w.match_id = m.match_id
--   WHERE w.hour_local BETWEEN
--     EXTRACT(HOUR FROM m.start_time AT TIME ZONE m.venue_timezone)
--     AND EXTRACT(HOUR FROM m.start_time AT TIME ZONE m.venue_timezone) + 3

select
    match_id,
    match_date,
    hour_local,
    latitude,
    longitude,
    elevation,
    timezone,

    -- Hourly conditions
    temperature_2m,
    relative_humidity_2m,
    dew_point_2m,
    apparent_temperature,
    wet_bulb_temperature_2m,
    precipitation,
    weather_code,
    pressure_msl,
    cloud_cover,
    cloud_cover_low,
    wind_speed_10m,
    wind_direction_10m,
    wind_gusts_10m,
    is_day,

    -- Extended hourly
    rain,
    surface_pressure,
    cloud_cover_mid,
    cloud_cover_high,
    vapour_pressure_deficit,
    soil_temperature_0_to_7cm,
    soil_moisture_0_to_7cm,
    sunshine_duration,
    shortwave_radiation,

    -- Daily summary (same for all 24 hours of a match)
    daily_temp_max,
    daily_temp_min,
    daily_precipitation_sum,
    daily_precipitation_hours,
    daily_sunrise,
    daily_sunset,
    daily_wind_speed_max,
    daily_wind_direction_dominant,
    daily_weather_code

from {{ ref('stg_weather') }}
