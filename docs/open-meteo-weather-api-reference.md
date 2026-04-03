# Open-Meteo Historical Weather API — Complete Field Reference

Source: https://open-meteo.com/en/docs/historical-weather-api
API endpoint: `https://archive-api.open-meteo.com/v1/archive`
Cost: Free, no API key required
Data source: ERA5 reanalysis (ECMWF) — available from 1940 to present
Resolution: Hourly, ~25km grid

## API Request Format

```
GET https://archive-api.open-meteo.com/v1/archive
  ?latitude=12.98
  &longitude=77.60
  &start_date=2024-04-15
  &end_date=2024-04-15
  &hourly=temperature_2m,relative_humidity_2m,...
  &daily=temperature_2m_max,...
  &timezone=Asia/Kolkata
```

## Response Metadata

| Field | Example | Description |
|---|---|---|
| `latitude` | 12.970123 | Snapped latitude (nearest grid point) |
| `longitude` | 77.56364 | Snapped longitude (nearest grid point) |
| `elevation` | 930.0 | Elevation of the grid point in meters |
| `utc_offset_seconds` | 19800 | UTC offset for the requested timezone (19800 = +5:30 IST) |
| `timezone` | Asia/Kolkata | Requested timezone |
| `generationtime_ms` | 67.3 | Server processing time in milliseconds |

---

## Hourly Variables (45 total)

### Temperature & Humidity (5 variables)

| # | API param | Unit | Description | Cricket relevance |
|---|---|---|---|---|
| 1 | `temperature_2m` | °C | Air temperature measured at 2 meters above ground level. Standard meteorological measurement height. | Heat affects player fatigue, ball behavior, pitch deterioration |
| 2 | `relative_humidity_2m` | % | Relative humidity at 2 meters above ground. Percentage of moisture in the air relative to the maximum it can hold at that temperature. 100% = fully saturated. | Dew factor — high humidity in evening IPL matches causes wet outfield and slippery ball |
| 3 | `dew_point_2m` | °C | Temperature at which air becomes fully saturated and water vapor condenses into dew. When air temperature drops to or below the dew point, moisture forms on surfaces (grass, ball, outfield). | Direct dew predictor — when match-time temp approaches dew point, dew forms. Critical for 2nd innings in night matches |
| 4 | `apparent_temperature` | °C | "Feels like" temperature combining the effects of wind chill (cold+wind) and heat index (heat+humidity). More representative of what players actually experience than raw temperature. | Player comfort and fatigue indicator |
| 5 | `wet_bulb_temperature_2m` | °C | The lowest temperature achievable through evaporative cooling alone. Measured by wrapping a wet cloth around a thermometer. Accounts for both heat AND humidity simultaneously. Above 35°C is considered dangerous for humans. | Best single metric for heat stress risk. Better than temperature alone because it captures humidity impact |

### Precipitation (4 variables)

| # | API param | Unit | Description | Cricket relevance |
|---|---|---|---|---|
| 6 | `precipitation` | mm | Total precipitation in the hour, combining rain, showers, and snowfall water equivalent. | Rain delays, DLS method triggers, wet outfield |
| 7 | `rain` | mm | Rainfall only in the hour. Excludes snow and showers from convective activity. In tropical/subtropical climates like India, this is usually identical to precipitation. | Direct rain measurement |
| 8 | `snowfall` | cm | Snowfall in the hour in centimeters. | Not relevant for IPL (no snow in Indian cricket venues) |
| 9 | `snow_depth` | m | Accumulated snow depth on the ground in meters. | Not relevant for IPL |

### Weather Conditions (1 variable)

| # | API param | Unit | Description | Cricket relevance |
|---|---|---|---|---|
| 10 | `weather_code` | WMO code | Categorical weather condition using WMO standard codes. Key codes: 0=Clear sky, 1=Mainly clear, 2=Partly cloudy, 3=Overcast, 45/48=Fog, 51/53/55=Drizzle (light/moderate/dense), 61/63/65=Rain (slight/moderate/heavy), 80/81/82=Rain showers (slight/moderate/violent), 95=Thunderstorm, 96/99=Thunderstorm with hail. | Single categorical summary of conditions. Useful for grouping matches by weather type |

### Atmospheric Pressure (2 variables)

| # | API param | Unit | Description | Cricket relevance |
|---|---|---|---|---|
| 11 | `pressure_msl` | hPa | Atmospheric pressure normalized to mean sea level. This adjustment removes the effect of venue elevation, making pressure values comparable across venues at different altitudes (e.g. Bangalore at 920m vs Mumbai at sea level). Standard atmosphere is ~1013 hPa. | Ball swing is believed to correlate with atmospheric pressure and humidity. Normalized pressure allows cross-venue comparison |
| 12 | `surface_pressure` | hPa | Actual atmospheric pressure at the venue's elevation, without sea-level normalization. Lower at higher-altitude venues (Bangalore ~910 hPa vs Mumbai ~1013 hPa). | Raw pressure at the ground. Lower pressure = less air resistance = ball travels further |

### Cloud Cover (4 variables)

| # | API param | Unit | Description | Cricket relevance |
|---|---|---|---|---|
| 13 | `cloud_cover` | % | Total cloud cover across all altitude levels. 0% = completely clear sky, 100% = fully overcast. Derived from low, mid, and high cloud layers. | Overcast conditions are widely believed to assist swing bowling. General indicator of playing conditions |
| 14 | `cloud_cover_low` | % | Cloud cover from clouds below ~2km altitude (stratus, stratocumulus, fog). These are the thick, grey clouds that block sunlight and create overcast conditions. | Most relevant for cricket — low clouds create the overcast "swing bowling" conditions. Thick low clouds trap moisture |
| 15 | `cloud_cover_mid` | % | Cloud cover from clouds between ~2-6km altitude (altostratus, altocumulus). Medium-thickness clouds that partially block sunlight. | Moderate impact on playing conditions |
| 16 | `cloud_cover_high` | % | Cloud cover from clouds above ~6km altitude (cirrus, cirrostratus). Thin, wispy clouds that let most sunlight through. | Minimal impact on cricket — these are thin ice-crystal clouds |

### Wind (5 variables)

| # | API param | Unit | Description | Cricket relevance |
|---|---|---|---|---|
| 17 | `wind_speed_10m` | km/h | Wind speed at 10 meters above ground. Standard meteorological measurement height. Represents sustained wind speed averaged over the hour. | Affects ball flight trajectory, boundary distances, and catch difficulty. Strong wind favors batting with the wind, challenges batting against it |
| 18 | `wind_speed_100m` | km/h | Wind speed at 100 meters above ground. Upper atmosphere wind that doesn't directly affect ground-level play. | Not directly relevant — too high above playing surface |
| 19 | `wind_direction_10m` | ° | Wind direction at 10m in compass degrees. 0°=North, 90°=East, 180°=South, 270°=West. Indicates where the wind is coming FROM (a 270° wind blows from west to east). | Bowling with/against wind matters for pace and swing. Cross-wind affects ball drift and fielding |
| 20 | `wind_direction_100m` | ° | Wind direction at 100 meters above ground. | Not directly relevant — too high above playing surface |
| 21 | `wind_gusts_10m` | km/h | Maximum instantaneous wind gust speed recorded in the hour at 10m. Gusts are brief (3-5 second) bursts of wind significantly stronger than the sustained speed. | Sudden gusts affect high catches, ball trajectory mid-flight, and can blow bails off |

### Evapotranspiration & Vapour (2 variables)

| # | API param | Unit | Description | Cricket relevance |
|---|---|---|---|---|
| 22 | `et0_fao_evapotranspiration` | mm | FAO-56 reference evapotranspiration. Rate at which water evaporates from a standardized grass surface. Depends on temperature, humidity, wind, and solar radiation. Agricultural/irrigation metric. | Marginal — could indicate how quickly a wet outfield dries after rain |
| 23 | `vapour_pressure_deficit` | kPa | Difference between the amount of moisture the air can hold (at current temperature) and the amount it actually holds. Higher VPD = drier air, lower VPD = more humid/closer to saturation. 0 = fully saturated. | Alternative humidity metric. Low VPD (near 0) means air is nearly saturated — dew likely |

### Soil (8 variables)

| # | API param | Unit | Description | Cricket relevance |
|---|---|---|---|---|
| 24 | `soil_temperature_0_to_7cm` | °C | Temperature of the top 7cm of soil. Affected by solar radiation, air temperature, and moisture. | Could relate to pitch behavior — hot dry soil vs cool moist soil |
| 25 | `soil_temperature_7_to_28cm` | °C | Soil temperature at 7-28cm depth. More stable than surface, less affected by hourly weather changes. | Marginal relevance |
| 26 | `soil_temperature_28_to_100cm` | °C | Soil temperature at 28-100cm depth. Very stable, changes slowly over days/weeks. | Not relevant for cricket |
| 27 | `soil_temperature_100_to_255cm` | °C | Soil temperature at 1-2.5 meter depth. Essentially constant over short periods. | Not relevant for cricket |
| 28 | `soil_moisture_0_to_7cm` | m³/m³ | Volumetric water content of the top 7cm of soil. Expressed as cubic meters of water per cubic meter of soil. 0.0 = bone dry, ~0.4 = saturated. | Could indicate outfield/pitch moisture. Wet soil = slower outfield, more seam movement |
| 29 | `soil_moisture_7_to_28cm` | m³/m³ | Soil moisture at 7-28cm depth. | Marginal — sub-surface moisture |
| 30 | `soil_moisture_28_to_100cm` | m³/m³ | Soil moisture at 28-100cm depth. | Not relevant for cricket |
| 31 | `soil_moisture_100_to_255cm` | m³/m³ | Soil moisture at 1-2.5 meter depth. | Not relevant for cricket |

### Solar & Daylight (2 variables)

| # | API param | Unit | Description | Cricket relevance |
|---|---|---|---|---|
| 32 | `is_day` | 0/1 | Binary flag: 1 if the sun is above the horizon, 0 if below. Based on solar position calculation for the exact lat/lng. | Useful for confirming day vs night portions of day-night matches |
| 33 | `sunshine_duration` | seconds | Number of seconds of direct sunshine in the hour (0-3600). Sunshine is defined as direct solar irradiance exceeding 120 W/m². Cloudy hours have low values even during daytime. | Indicates how overcast conditions were during play |

### Solar Radiation — Hourly Averages (6 variables)

| # | API param | Unit | Description | Cricket relevance |
|---|---|---|---|---|
| 34 | `shortwave_radiation` | W/m² | Total incoming solar radiation averaged over the hour. Sum of direct beam + diffuse (scattered) radiation. 0 at night, peaks ~800-1000 W/m² at noon in clear tropical conditions. | General solar intensity indicator. Low values during daytime = overcast |
| 35 | `direct_radiation` | W/m² | Direct beam solar radiation hitting a horizontal surface, averaged over the hour. This is sunlight that arrives in a straight line from the sun without being scattered by clouds or atmosphere. | High direct radiation = clear skies, harsh sun. Low = cloudy/overcast |
| 36 | `diffuse_radiation` | W/m² | Solar radiation scattered by clouds, aerosols, and atmosphere before reaching the ground, averaged over the hour. On overcast days, most radiation is diffuse. | High diffuse + low direct = overcast conditions (swing bowling weather) |
| 37 | `direct_normal_irradiance` | W/m² | Direct solar radiation measured perpendicular to the sun's rays (not on a horizontal surface), averaged over the hour. Always higher than direct_radiation because it's not reduced by the sun's angle. | Solar panel metric, not directly useful for cricket |
| 38 | `global_tilted_irradiance` | W/m² | Total solar radiation on a surface tilted at a fixed angle (default: latitude angle), averaged over the hour. Optimized for solar panel installations. | Solar panel metric, not relevant for cricket |
| 39 | `terrestrial_radiation` | W/m² | Longwave (infrared) radiation emitted upward by the Earth's surface, averaged over the hour. Depends on surface temperature. Not solar radiation — this is heat radiating from the ground. | Not relevant for cricket |

### Solar Radiation — Instantaneous Values (6 variables)

These are the same radiation measurements as above, but captured as instantaneous snapshots at the END of each hour rather than hourly averages.

| # | API param | Unit | Description | Cricket relevance |
|---|---|---|---|---|
| 40 | `shortwave_radiation_instant` | W/m² | Instantaneous total solar radiation at the end of the hour. | Same as #34 but point-in-time instead of average |
| 41 | `direct_radiation_instant` | W/m² | Instantaneous direct beam radiation at end of hour. | Same as #35 but point-in-time |
| 42 | `diffuse_radiation_instant` | W/m² | Instantaneous diffuse radiation at end of hour. | Same as #36 but point-in-time |
| 43 | `direct_normal_irradiance_instant` | W/m² | Instantaneous direct normal irradiance at end of hour. | Same as #37 but point-in-time |
| 44 | `global_tilted_irradiance_instant` | W/m² | Instantaneous tilted surface radiation at end of hour. | Same as #38 but point-in-time |
| 45 | `terrestrial_radiation_instant` | W/m² | Instantaneous terrestrial (longwave) radiation at end of hour. | Same as #39 but point-in-time |

---

## Daily Variables (18 total)

### Temperature (4 variables)

| # | API param | Unit | Description | Cricket relevance |
|---|---|---|---|---|
| 1 | `temperature_2m_max` | °C | Maximum air temperature of the day at 2m height. | Day's peak heat — affects pitch conditions and player fatigue |
| 2 | `temperature_2m_min` | °C | Minimum air temperature of the day at 2m height. Usually occurs around dawn. | Night cooling — large max-min gap indicates dry conditions |
| 3 | `apparent_temperature_max` | °C | Maximum "feels like" temperature of the day. | Peak heat stress for the day |
| 4 | `apparent_temperature_min` | °C | Minimum "feels like" temperature of the day. | Coolest conditions (usually pre-dawn) |

### Precipitation (4 variables)

| # | API param | Unit | Description | Cricket relevance |
|---|---|---|---|---|
| 5 | `precipitation_sum` | mm | Total precipitation for the entire day (rain + snow + showers). | Total rain on match day — indicates if play was likely affected |
| 6 | `rain_sum` | mm | Total rainfall for the day (excludes snow). | Same as above for tropical venues |
| 7 | `snowfall_sum` | cm | Total snowfall for the day. | Not relevant for IPL |
| 8 | `precipitation_hours` | hours | Number of hours during the day that had measurable precipitation (>0.1mm). | Indicates how spread out the rain was — 1 hour of heavy rain vs 6 hours of drizzle |

### Solar & Daylight (4 variables)

| # | API param | Unit | Description | Cricket relevance |
|---|---|---|---|---|
| 9 | `sunrise` | ISO 8601 | Exact sunrise time for the venue location on that date. | Context for day-night matches — when natural light starts |
| 10 | `sunset` | ISO 8601 | Exact sunset time for the venue location on that date. | When floodlights become necessary. Dew typically starts forming around/after sunset |
| 11 | `sunshine_duration` | seconds | Total seconds of direct sunshine for the entire day. Clear day ~40,000s, fully overcast ~0s. | How sunny vs overcast the match day was overall |
| 12 | `daylight_duration` | seconds | Total seconds from sunrise to sunset. Varies by latitude and season. ~43,000-46,000s for Indian venues. | Length of natural daylight available |

### Wind (3 variables)

| # | API param | Unit | Description | Cricket relevance |
|---|---|---|---|---|
| 13 | `wind_speed_10m_max` | km/h | Maximum sustained wind speed recorded during the day at 10m height. | Windiest conditions of the day |
| 14 | `wind_gusts_10m_max` | km/h | Maximum wind gust recorded during the day at 10m height. | Strongest gust — indicates if extreme wind events occurred |
| 15 | `wind_direction_10m_dominant` | ° | The most frequent wind direction during the day in compass degrees. | Overall wind pattern for the day |

### Other Daily (3 variables)

| # | API param | Unit | Description | Cricket relevance |
|---|---|---|---|---|
| 16 | `shortwave_radiation_sum` | MJ/m² | Total solar energy received at the surface for the entire day in megajoules per square meter. | Overall solar energy — low values = overcast day |
| 17 | `et0_fao_evapotranspiration` | mm | Daily reference evapotranspiration. Total water that would evaporate from a standard grass surface over the day. | How quickly wet surfaces dry — relevant after rain delays |
| 18 | `weather_code` | WMO code | The most significant (severe) weather condition that occurred during the day. Uses same WMO codes as hourly. | Single summary of the day's worst weather |

---

## Data Resolution

| Resolution | API endpoint | Available from | Points/day |
|---|---|---|---|
| Hourly | `archive-api.open-meteo.com/v1/archive` | 1940 (all IPL seasons) | 24 |

Model selection: `best_match` (default — no `&models=` parameter needed).
The API automatically selects the best available reanalysis source for each variable and location.
For Indian venues this blends ERA5 (~25km) and ERA5-Land (~9km) — higher resolution where available,
falling back to coarser data for variables only available in ERA5.
Other possible sources the API may use include IFS HRES, CERRA, etc. depending on region and variable.
We don't need to choose — `best_match` handles it.

No sub-hourly resolution exists on any free weather API for Indian locations.
The Historical Forecast API offers `minutely_15` but for India it's just interpolated from hourly data (native 15-min only available in Central Europe and North America).

---

## Field Selection for Cricket Analytics

> **Status: PENDING REVIEW**
>
> Recommendations marked below. Awaiting user verification.
> - ✅ INCLUDE — pull from API and store in bronze, surface relevant fields in gold
> - ⚠️ BRONZE ONLY — pull and store for completeness, don't surface in gold
> - ❌ SKIP — don't request from API

### Hourly Variables — Recommendations

| # | API param | Include? | Reason |
|---|---|---|---|
| 1 | `temperature_2m` | ✅ INCLUDE | Core metric. Heat affects player fatigue, pitch behavior, ball swing. Essential for any weather analysis |
| 2 | `relative_humidity_2m` | ✅ INCLUDE | Core dew factor metric. High humidity in evening matches = wet outfield, slippery ball. Key for 2nd innings analysis |
| 3 | `dew_point_2m` | ✅ INCLUDE | Most direct dew predictor. When air temp drops to dew point, moisture forms. Critical for IPL night matches |
| 4 | `apparent_temperature` | ✅ INCLUDE | "Feels like" temp captures wind+humidity effect. Better than raw temp for player fatigue analysis |
| 5 | `wet_bulb_temperature_2m` | ✅ INCLUDE | Best single heat stress metric. Combines temp+humidity. Relevant for player performance in extreme heat |
| 6 | `precipitation` | ✅ INCLUDE | Rain detection. Directly correlates with rain delays, DLS triggers, wet outfield |
| 7 | `rain` | ⚠️ BRONZE ONLY | Redundant with precipitation for Indian venues (no snow). Keep in bronze for completeness |
| 8 | `snowfall` | ❌ SKIP | Zero relevance — no IPL venue gets snow |
| 9 | `snow_depth` | ❌ SKIP | Zero relevance — no IPL venue has snow |
| 10 | `weather_code` | ✅ INCLUDE | Categorical weather summary. Useful for grouping matches (clear/cloudy/rain/thunderstorm) |
| 11 | `pressure_msl` | ✅ INCLUDE | Normalized pressure for cross-venue comparison. Ball swing correlates with atmospheric conditions |
| 12 | `surface_pressure` | ⚠️ BRONZE ONLY | Raw pressure at venue elevation. Less useful than MSL for comparison, but store for completeness |
| 13 | `cloud_cover` | ✅ INCLUDE | Overcast conditions assist swing bowling. Key for bowling analysis |
| 14 | `cloud_cover_low` | ✅ INCLUDE | Low clouds are the ones that create overcast swing conditions. More specific than total cloud cover |
| 15 | `cloud_cover_mid` | ⚠️ BRONZE ONLY | Moderate relevance. Mid-level clouds have some impact but less than low clouds |
| 16 | `cloud_cover_high` | ⚠️ BRONZE ONLY | Minimal impact — thin cirrus clouds don't affect playing conditions much |
| 17 | `wind_speed_10m` | ✅ INCLUDE | Affects ball flight, boundary distances, catch difficulty. Core wind metric |
| 18 | `wind_speed_100m` | ❌ SKIP | 100m above ground — irrelevant for ground-level cricket |
| 19 | `wind_direction_10m` | ✅ INCLUDE | Bowling with/against wind matters. Cross-wind affects drift and fielding |
| 20 | `wind_direction_100m` | ❌ SKIP | 100m above ground — irrelevant |
| 21 | `wind_gusts_10m` | ✅ INCLUDE | Sudden gusts affect high catches, ball trajectory. Complements sustained wind speed |
| 22 | `et0_fao_evapotranspiration` | ❌ SKIP | Agricultural metric. Not useful for cricket analysis |
| 23 | `vapour_pressure_deficit` | ⚠️ BRONZE ONLY | Alternative humidity metric. We already have humidity + dew point which are more intuitive |
| 24 | `soil_temperature_0_to_7cm` | ⚠️ BRONZE ONLY | Could relate to pitch behavior but this is ERA5 grid-level data, not pitch-specific. Store just in case |
| 25 | `soil_temperature_7_to_28cm` | ❌ SKIP | Too deep, too coarse resolution to be useful |
| 26 | `soil_temperature_28_to_100cm` | ❌ SKIP | Not relevant |
| 27 | `soil_temperature_100_to_255cm` | ❌ SKIP | Not relevant |
| 28 | `soil_moisture_0_to_7cm` | ⚠️ BRONZE ONLY | Could indicate general ground moisture (wet outfield). ERA5 resolution is coarse but directionally useful |
| 29 | `soil_moisture_7_to_28cm` | ❌ SKIP | Too deep to be relevant |
| 30 | `soil_moisture_28_to_100cm` | ❌ SKIP | Not relevant |
| 31 | `soil_moisture_100_to_255cm` | ❌ SKIP | Not relevant |
| 32 | `is_day` | ✅ INCLUDE | Confirms day/night status at each hour. Useful for day-night match analysis |
| 33 | `sunshine_duration` | ⚠️ BRONZE ONLY | Redundant with cloud cover for our purposes. Store for completeness |
| 34 | `shortwave_radiation` | ⚠️ BRONZE ONLY | General solar intensity. Could indicate overcast conditions but cloud_cover is more intuitive |
| 35 | `direct_radiation` | ❌ SKIP | Solar panel metric. No cricket use case |
| 36 | `diffuse_radiation` | ❌ SKIP | Solar panel metric. No cricket use case |
| 37 | `direct_normal_irradiance` | ❌ SKIP | Solar panel metric |
| 38 | `global_tilted_irradiance` | ❌ SKIP | Solar panel metric |
| 39 | `terrestrial_radiation` | ❌ SKIP | Earth's heat radiation. No cricket use case |
| 40 | `shortwave_radiation_instant` | ❌ SKIP | Instantaneous version of #34. Same reasoning |
| 41 | `direct_radiation_instant` | ❌ SKIP | Solar panel metric |
| 42 | `diffuse_radiation_instant` | ❌ SKIP | Solar panel metric |
| 43 | `direct_normal_irradiance_instant` | ❌ SKIP | Solar panel metric |
| 44 | `global_tilted_irradiance_instant` | ❌ SKIP | Solar panel metric |
| 45 | `terrestrial_radiation_instant` | ❌ SKIP | Solar panel metric |

**Summary: 13 INCLUDE, 9 BRONZE ONLY, 23 SKIP**

### Daily Variables — Recommendations

| # | API param | Include? | Reason |
|---|---|---|---|
| 1 | `temperature_2m_max` | ✅ INCLUDE | Day's peak heat. Useful for match-day summary |
| 2 | `temperature_2m_min` | ✅ INCLUDE | Night low. Large max-min gap = dry conditions |
| 3 | `apparent_temperature_max` | ⚠️ BRONZE ONLY | We have hourly apparent_temperature which is more useful at match time |
| 4 | `apparent_temperature_min` | ⚠️ BRONZE ONLY | Same reasoning |
| 5 | `precipitation_sum` | ✅ INCLUDE | Total rain on match day. Key summary metric |
| 6 | `rain_sum` | ⚠️ BRONZE ONLY | Redundant with precipitation_sum for Indian venues |
| 7 | `snowfall_sum` | ❌ SKIP | No snow at IPL venues |
| 8 | `precipitation_hours` | ✅ INCLUDE | How many hours it rained — distinguishes heavy burst vs all-day drizzle |
| 9 | `sunrise` | ✅ INCLUDE | Dew typically forms around sunset. Sunrise/sunset frame the day-night transition |
| 10 | `sunset` | ✅ INCLUDE | Critical for dew analysis — dew onset correlates with sunset timing |
| 11 | `sunshine_duration` | ⚠️ BRONZE ONLY | Redundant with cloud cover data |
| 12 | `daylight_duration` | ⚠️ BRONZE ONLY | Derivable from sunrise/sunset |
| 13 | `wind_speed_10m_max` | ✅ INCLUDE | Windiest moment of the day — useful for match-day summary |
| 14 | `wind_gusts_10m_max` | ⚠️ BRONZE ONLY | We have hourly gusts which are more useful at match time |
| 15 | `wind_direction_10m_dominant` | ✅ INCLUDE | Overall wind pattern for the day |
| 16 | `shortwave_radiation_sum` | ❌ SKIP | Solar energy metric, not useful for cricket |
| 17 | `et0_fao_evapotranspiration` | ❌ SKIP | Agricultural metric |
| 18 | `weather_code` | ✅ INCLUDE | Single summary of the day's most significant weather |

**Summary: 9 INCLUDE, 6 BRONZE ONLY, 3 SKIP**

---

## WMO Weather Code Reference

| Code | Description |
|---|---|
| 0 | Clear sky |
| 1 | Mainly clear |
| 2 | Partly cloudy |
| 3 | Overcast |
| 45 | Fog |
| 48 | Depositing rime fog |
| 51 | Light drizzle |
| 53 | Moderate drizzle |
| 55 | Dense drizzle |
| 56 | Light freezing drizzle |
| 57 | Dense freezing drizzle |
| 61 | Slight rain |
| 63 | Moderate rain |
| 65 | Heavy rain |
| 66 | Light freezing rain |
| 67 | Heavy freezing rain |
| 71 | Slight snowfall |
| 73 | Moderate snowfall |
| 75 | Heavy snowfall |
| 77 | Snow grains |
| 80 | Slight rain showers |
| 81 | Moderate rain showers |
| 82 | Violent rain showers |
| 85 | Slight snow showers |
| 86 | Heavy snow showers |
| 95 | Thunderstorm (slight/moderate) |
| 96 | Thunderstorm with slight hail |
| 99 | Thunderstorm with heavy hail |
