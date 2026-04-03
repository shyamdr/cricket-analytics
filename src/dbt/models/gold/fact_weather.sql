-- Weather fact table: one row per match per hour (24 rows per match).
-- Combines hourly conditions from stg_weather_hourly with daily summary
-- from stg_weather_daily into a single denormalized table.
--
-- Join to dim_matches on match_id. Use hour_local + match start_time
-- to filter to actual match hours.
select
    h.match_id,
    h.match_date,
    h.hour_local,
    h.latitude,
    h.longitude,
    h.elevation,
    h.timezone,

    -- Hourly conditions
    h.temperature_2m,
    h.relative_humidity_2m,
    h.dew_point_2m,
    h.apparent_temperature,
    h.wet_bulb_temperature_2m,
    h.precipitation,
    h.weather_code,
    h.pressure_msl,
    h.cloud_cover,
    h.cloud_cover_low,
    h.wind_speed_10m,
    h.wind_direction_10m,
    h.wind_gusts_10m,
    h.is_day,

    -- Extended hourly
    h.rain,
    h.surface_pressure,
    h.cloud_cover_mid,
    h.cloud_cover_high,
    h.vapour_pressure_deficit,
    h.soil_temperature_0_to_7cm,
    h.soil_moisture_0_to_7cm,
    h.sunshine_duration as hourly_sunshine_duration,
    h.shortwave_radiation,

    -- Daily summary (same for all 24 hours of a match)
    d.temp_max as daily_temp_max,
    d.temp_min as daily_temp_min,
    d.apparent_temp_max as daily_apparent_temp_max,
    d.apparent_temp_min as daily_apparent_temp_min,
    d.precipitation_sum as daily_precipitation_sum,
    d.precipitation_hours as daily_precipitation_hours,
    d.rain_sum as daily_rain_sum,
    d.sunrise as daily_sunrise,
    d.sunset as daily_sunset,
    d.sunshine_duration as daily_sunshine_duration,
    d.daylight_duration as daily_daylight_duration,
    d.wind_speed_max as daily_wind_speed_max,
    d.wind_gusts_max as daily_wind_gusts_max,
    d.wind_direction_dominant as daily_wind_direction_dominant,
    d.shortwave_radiation_sum as daily_shortwave_radiation_sum,
    d.weather_code as daily_weather_code

from {{ ref('stg_weather_hourly') }} h
left join {{ ref('stg_weather_daily') }} d on h.match_id = d.match_id
