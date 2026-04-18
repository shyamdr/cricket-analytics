# dbt Models — Reference

21 models total: 12 silver (staging) + 9 gold (analytics-ready). All in `src/dbt/models/`. Schemas: `main_silver.*` and `main_gold.*` in DuckDB.

Run with `make transform` (runs `dbt seed` + `dbt run`). Test with `make dbt-test`. Docs with `make dbt-docs`.

## Silver layer (12 models, all in `src/dbt/models/silver/`)

Silver cleans types, normalizes columns, and provides a stable interface for gold. All materialized as tables with `_loaded_at` audit timestamp.

### Cricsheet silver

| Model | Grain | Notes |
|---|---|---|
| `stg_matches` | one row per match | Normalizes season: keeps raw Cricsheet season as `season_raw`, derives `season` from `EXTRACT(YEAR FROM match_date)` — format-agnostic, no hardcoded IPL cases |
| `stg_deliveries` | one row per ball | Coalesces extras to 0, derives `is_legal_delivery` (not wide or no-ball), validation flags `_is_valid_extras` and `_is_valid_total` |
| `stg_people` | one row per player in registry | From people.csv; columns: `player_id, player_name, unique_name, key_cricinfo, key_cricbuzz, key_bcci` |

### ESPN enrichment silver

All ESPN silver models are wrapped in `{% if source_exists('bronze', 'espn_*') %}`. If the bronze table doesn't exist, the model returns an empty result set with a typed NULL shape so downstream models still build. The `source_exists` macro lives in `src/dbt/macros/source_exists.sql`.

| Model | Grain | Key columns |
|---|---|---|
| `stg_espn_matches` | one row per match (joined to Cricsheet via `cricsheet_match_id`) | captain/keeper per team, is_home flags, start/end time, floodlit, espn_ground_id, ground_capacity (cleaned from strings like "60,000 approx"), venue_timezone, classification IDs |
| `stg_espn_players` | one row per player | espn_player_id, DOB, batting/bowling styles, playing_roles, country_team_id, is_overseas, image_url, headshot_image_url |
| `stg_espn_innings` | one row per innings per match | Innings-level ESPN metadata |
| `stg_espn_ball_data` | one row per ball | Spatial + shot data: wagon_x/wagon_y, pitch_line, pitch_length, shot_control, shot_type, batsman/bowler/non-striker ESPN IDs |
| `stg_espn_teams` | one row per team | espn_team_id, team_abbreviation, is_country, primary_color, image_url (logo) |
| `stg_espn_grounds` | one row per ground | espn_ground_id, ground_name, capacity, timezone, image_url |

### Other enrichment silver

| Model | Grain | Notes |
|---|---|---|
| `stg_weather_hourly` | 24 rows per match (one per hour) | Explodes bronze `hourly_json` via `unnest(generate_series(0, 23))`. Hourly temp, humidity, wind, cloud cover, precipitation, weather_code, etc. |
| `stg_weather_daily` | one row per match | Daily summary: temp_max/min, precipitation_sum, wind_max, sunrise/sunset, sunshine_duration |
| `stg_venue_coordinates` | one row per (venue, city) | Geocoded lat/lng, formatted_address, place_id from OpenStreetMap Nominatim |

## Gold layer (9 models, all in `src/dbt/models/gold/`)

Gold is analytics-ready. Dimensions prefixed `dim_`, facts prefixed `fact_`. Facts read from silver (not from other gold) with explicit `WHERE is_super_over = false`.

### Dimensions

#### `dim_matches` — one row per match
Reads `stg_matches` LEFT JOIN `stg_espn_matches`. Preserves raw Cricsheet outcome columns (`outcome_winner`, `outcome_by_runs`, `outcome_by_wickets`, `outcome_method`, `outcome_result`, `outcome_eliminator`) alongside two derived columns:

- **`match_result_type`** (enum): `normal_win`, `dls_win`, `awarded`, `tie_super_over`, `no_result`, `unknown`
- **`winning_margin`** (text): human-readable, e.g. `'5 runs'`, `'3 wickets'`, `'Mumbai Indians won via super over'`, `'no result'`

ESPN enrichment columns: `team1_captain`, `team1_keeper`, `team2_captain`, `team2_keeper`, `team1_is_home`, `team2_is_home`, `floodlit`, `start_time`, `end_time`, `hours_info`, `venue_timezone`, `espn_match_id`, `espn_ground_id`, `ground_capacity`, `international_class_id`, `sub_class_id`, `replacement_players_json`, `teams_enrichment_json`.

#### `dim_players` — one row per `player_id`
Builds from `lateral (select key, value from json_each(m.registry_json::json))` across all matches. Dedupes by `player_id` using the most frequently used name. LEFT JOIN `stg_people` (for cross-reference IDs) and `stg_espn_players` (via `key_cricinfo = espn_player_id`).

Key columns: `player_id, player_name, unique_name, key_cricinfo, key_cricbuzz, key_bcci, espn_player_id, date_of_birth, batting_styles, bowling_styles, playing_roles, country_team_id, is_overseas, image_url, headshot_image_url`.

Image URLs are CMS paths — prepend `https://img1.hscicdn.com/image/upload/f_auto` at display time.

#### `dim_teams` — one row per team name (including renames)
Union of `team1` and `team2` from `stg_matches`. LEFT JOINs three sources:

- `team_name_mappings` seed — provides `current_franchise_name` (e.g. "Delhi Daredevils" → "Delhi Capitals"). Empty string = defunct franchise. Not in seed = active, never renamed.
- `team_brand_colors` seed — curated brand colors (ESPN colors are unreliable). Provides `primary_color`, `brand_color_alt`, and `espn_team_id` fallback.
- `stg_espn_teams` — official ESPN data: `espn_team_id`, `team_abbreviation`, `is_country`, `logo_url`.

Temporal columns: `first_match_date`, `last_match_date`, `total_matches` — derived from actual match data (gives SCD Type 2 semantics without explicit valid_from/valid_to).

#### `dim_venues` — one row per (venue, city)
LEFT JOINs `venue_name_mappings` seed for `canonical_venue`/`canonical_city` (alias → canonical). LEFT JOIN `stg_venue_coordinates` for lat/lng. LEFT JOIN `stg_espn_matches` (for ground_id) then `stg_espn_grounds` (for image). ESPN ground_id resolved via "most common per venue" row_number trick.

### Facts

All facts share: grain columns + `season` + `match_date` denormalized, plus measure columns.

#### `fact_deliveries` — one row per legal ball (ball-level grain)
- Grain: `(match_id, innings, over_num, ball_num)`
- **Incremental materialization** via `materialized='incremental'` with `match_id NOT IN (select distinct match_id from {{ this }})` filter. Full refresh builds complete table; subsequent runs only process new matches.
- Excludes super overs (`WHERE d.is_super_over = false`).
- Derived column **`phase`** (format-agnostic): `'powerplay'`, `'middle'`, `'death'`, or `NULL` for Tests. Thresholds depend on `max_overs` (20 → T20 rules, 50 → ODI rules, 100 → The Hundred rules).
- Columns: all `stg_deliveries` columns + `season`, `match_date`, `phase`.

#### `fact_batting_innings` — per-batter-per-match
- Grain: `(match_id, innings, batting_team, batter)`
- Measures: `balls_faced` (legal only), `runs_scored`, `fours`, `sixes`, `dot_balls`, `strike_rate` (runs × 100 / balls), `is_out`, `dismissal_kind`, `dismissed_by`.

#### `fact_bowling_innings` — per-bowler-per-match
- Grain: `(match_id, innings, batting_team, bowler)`
- `runs_conceded = batter_runs + extras_wides + extras_noballs` — byes, legbyes, penalties NOT charged to bowler.
- `wickets` excludes run outs, retired hurt, retired out, obstructing the field (not the bowler's wicket).
- Other measures: `legal_balls`, `overs_bowled` (X.Y format where Y is 0-5 balls), `dot_balls`, `wides`, `noballs`, `fours_conceded`, `sixes_conceded`, `economy_rate`.

#### `fact_match_summary` — team-level per innings
- Grain: `(match_id, innings, batting_team)`
- Measures: `total_runs`, `total_wickets`, `legal_balls`, `total_extras`, `total_fours`, `total_sixes`, `total_dot_balls`, `run_rate`, `overs_played` (max over_num + 1).

#### `fact_weather` — one row per match per hour (24 rows per match)
- Grain: `(match_id, hour_local)`
- LEFT JOIN `stg_weather_daily` on `match_id` — daily summary repeated for all 24 hours.
- Uses `weather_description` macro (in `src/dbt/macros/weather_description.sql`) to translate hourly + daily `weather_code` to text.
- Hourly: `temperature_2m, relative_humidity_2m, dew_point_2m, apparent_temperature, precipitation, weather_code, weather_description, pressure_msl, cloud_cover*, wind_speed_10m, wind_direction_10m, wind_gusts_10m, is_day, rain, surface_pressure, vapour_pressure_deficit, soil_*`, etc.
- Daily (denormalized): `daily_temp_max/min, daily_apparent_temp_max/min, daily_precipitation_sum, daily_wind_speed_max, daily_sunrise, daily_sunset, daily_sunshine_duration, daily_weather_code, daily_weather_description`, etc.

## Seeds (5, in `src/dbt/seeds/`)

| Seed | Used by | Purpose |
|---|---|---|
| `team_name_mappings.csv` | `dim_teams` | Franchise renames (Delhi Daredevils → Delhi Capitals). Add a row to record a new rename, no SQL change needed |
| `team_brand_colors.csv` | `dim_teams` | Curated brand colors + ESPN ID fallback (ESPN colors are unreliable) |
| `venue_name_mappings.csv` | `dim_venues` | Venue alias → canonical name and city |
| `espn_squads.csv` | — not referenced by any model | Backup data from the halted auction pipeline; kept for historical reference |
| `espn_squads_backup_2008_to_2013.csv` | — not referenced | Full 2008-2013 auction/contract data (1456 player-seasons) |

## Macros (`src/dbt/macros/`)

- **`source_exists.sql`** — `{% if source_exists('bronze', 'espn_matches') %}` gate for all 6 ESPN silver models and 3 weather/geocoding silver models. Returns empty-shape SELECT (with typed NULL columns) if bronze table hasn't been created by enrichment yet. Lets dbt build even when ESPN/weather enrichment hasn't run.
- **`weather_description.sql`** — `{{ weather_description('column') }}` maps WMO weather codes to text. Used in `fact_weather` for both hourly and daily columns.

## Tests (59 total)

### Generic tests (53) — defined in `schema.yml` files
- Silver: `unique` + `not_null` on grain columns, `relationships` on FK joins
- Gold: `unique` composite keys on each fact table (e.g. `match_id + innings + batter`), `not_null` on all grain and measure columns, `accepted_values` where applicable

### Singular SQL tests (6) — in `src/dbt/tests/`
- `assert_completed_matches_have_two_teams.sql`
- `assert_every_match_has_deliveries.sql`
- `assert_no_negative_batting_stats.sql`
- `assert_no_negative_bowling_stats.sql`
- `assert_runs_equal_batter_plus_extras.sql`
- `assert_valid_match_summary_stats.sql`

All format-agnostic — no hardcoded IPL assumptions (e.g. no "max 6 runs per ball" or "20 overs max" checks).

## Import pattern (Python consumers)

Do not build f-strings with `settings.gold_schema`. Import from `src/tables.py`:

```python
from src.tables import MATCHES, PLAYERS, BATTING_INNINGS, BOWLING_INNINGS, MATCH_SUMMARY, VENUES, TEAMS, DELIVERIES, WEATHER
# and for bronze (enrichment code only):
from src.tables import BRONZE_MATCHES, BRONZE_ESPN_MATCHES, BRONZE_WEATHER, ...
```

Rename a schema or table → update `src/tables.py` once, everyone gets it.

## What's NOT here

- No `staging`/`marts` dbt convention — we use `silver`/`gold` from the medallion pattern instead
- No snapshot tables — SCD tracking done via derived `first_match_date`/`last_match_date` in `dim_teams`
- No surrogate keys (intentional — see progress.md architecture review decision). Natural keys (`match_id`, `player_id`, `player_name`, `team_name`) are stable and human-readable
- No sources for future ML feature tables — Phase 3 not started
