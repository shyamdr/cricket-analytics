# OBT Field Catalog

Complete inventory of every field in every bronze and silver table, with the decision for each: whether it is in `fact_deliveries_enriched` (OBT), and why. Generated from live database inspection on 2026-04-25.

## Source-of-truth policy (decided 2026-04-25)

Neither Cricsheet nor ESPN is a strict superset of the other. Rule per field:

- **Ball events (runs, extras, wickets, is_legal_delivery, fielder names, wicket kind):** Cricsheet is primary. Canonical curation, 100% coverage.
- **Ball-level spatial/shot data (wagon, pitch, shot_type, shot_control):** ESPN. Only source.
- **Ball timestamp (datetime of delivery):** ESPN. Only source. ~37% coverage today — NULL otherwise.
- **Match metadata (captains, keeper, floodlit, MVP impact, ground details, tournament points):** ESPN is primary. Richer.
- **DRS reviews:** Both. Cricsheet gives `review_by/umpire/batter/decision/type/umpires_call`. ESPN adds `review_side`, `is_umpire_call`, `remaining_count`, `original_decision`, `drs_decision`, decimal `overs_actual`. Complementary.
- **Impact-player replacements:** Both. Cricsheet gives `reason` string (e.g. "impact_player") and per-ball context. ESPN adds `player_in_id`, `player_out_id`, `replacement_type` numeric code, `over` decimal.
- **Player biodata (DOB, styles, roles, is_overseas):** ESPN. Only source.
- **Dropped catches, run-out chances, stumping chances:** ESPN (commentary events). Only source.
- **Ball-level impact flags (is_four, is_six, is_wicket, extras breakdown):** Cricsheet is primary. ESPN's duplicate version skipped.

Coverage reality-check (verified 2026-04-25):
- Cricsheet balls: 283,678
- ESPN ball_data: 283,244 (1 match missing)
- Rows joinable on `(match_id, innings, over_num, ball_num)`: 260,315 — 92% clean alignment. Ball-level ESPN data joined via LEFT JOIN with match+innings+over+ball. Unmatched 8% keeps Cricsheet fields, NULL ESPN fields.

## Key / legend

- **In silver?** — is this column exposed in the silver layer today?
- **Plan for OBT** — one of:
  - `add` — will be added in this iteration
  - `already in` — present in OBT today
  - `skip (reason)` — deliberately not in OBT, with the reason
- **Status** — `done` | `todo` | `N/A`

---

## bronze.matches (39 cols) — Cricsheet match-level

| Column | In silver? | Plan for OBT | Reason (if skipped) |
|---|---|---|---|
| match_id | yes | already in | — |
| data_version | yes | skip | audit-only, not analytical |
| meta_created | no (add) | add as `match_record_created_at` | useful audit per ball |
| meta_revision | no (add) | add as `match_record_revision` | tells us if Cricsheet corrected the file |
| season (raw) | yes (as `season_raw`) | skip | canonical derived `season` covers it |
| date | yes (as `match_date`) | already in | — |
| city | yes | already in | — |
| venue | yes | already in | — |
| team1 | yes | already in | — |
| team2 | yes | already in | — |
| team_type | no (add) | add | "club" vs "international" — major analytical signal |
| match_type | yes | already in | — |
| match_type_number | no (add) | add | official career counter (e.g. "Test #2567") |
| gender | yes | already in | — |
| overs | yes (as `max_overs`) | already in | — |
| balls_per_over | yes | skip | always 6 in practice; keep in silver for data-quality |
| toss_winner | yes | already in | — |
| toss_decision | yes | already in | — |
| toss_uncontested | no (add) | add | rare but real analytical fact |
| outcome_winner | yes | already in | — |
| outcome_by_runs | yes | already in | — |
| outcome_by_wickets | yes | already in | — |
| outcome_method | yes | already in | — |
| outcome_result | yes | already in | — |
| outcome_eliminator | yes | already in | — |
| player_of_match | yes | already in | — |
| event_name | yes | already in | — |
| event_match_number | yes | already in | — |
| event_stage | yes | already in | — |
| event_group | no (add) | add | group-stage label (e.g. "Group A") |
| officials_json | no (extract) | add as `umpire_1`, `umpire_2`, `tv_umpire`, `reserve_umpire`, `match_referee` | enables umpire-tendency analytics per ball |
| supersubs_json | no | skip | **verified 0 non-empty rows across all matches** — nothing to extract |
| missing_json | no | skip | **verified 0 non-empty rows across all matches** — nothing to extract |
| players_team1_json | yes (passed) | skip | wrong grain (match-level list of 11) |
| players_team2_json | yes (passed) | skip | wrong grain |
| registry_json | yes (passed) | skip | used by `dim_players` to resolve identifiers; not per-ball |
| _loaded_at | yes | skip | audit |
| _source_file | — | skip | audit |
| _run_id | — | skip | audit |

---

## bronze.deliveries (33 cols) — Cricsheet ball-level

| Column | In silver? | Plan for OBT | Reason (if skipped) |
|---|---|---|---|
| match_id | yes | already in | — |
| innings | yes | already in | — |
| batting_team | yes | already in | — |
| is_super_over | yes | already in (filter) | excluded from OBT |
| over_num | yes | already in | — |
| ball_num | yes | already in | — |
| batter | yes | already in | — |
| bowler | yes | already in | — |
| non_striker | yes | already in | — |
| batter_runs | yes | already in | — |
| extras_runs | yes | already in | — |
| total_runs | yes | already in | — |
| non_boundary | no (add) | add | flag for non-boundary 4/6 (all-run) |
| extras_wides | yes | already in | — |
| extras_noballs | yes | already in | — |
| extras_byes | yes | already in | — |
| extras_legbyes | yes | already in | — |
| extras_penalty | yes | already in | — |
| is_wicket | yes | already in | — |
| wicket_player_out | yes | already in | — |
| wicket_kind | yes | already in | — |
| wicket_fielder1 | yes | already in | — |
| wicket_fielder2 | yes | already in | — |
| review_by | no (add) | add | which team called DRS |
| review_umpire | no (add) | add | umpire who made the original call |
| review_batter | no (add) | add | batter involved |
| review_decision | no (add) | add | upheld / struck down / umpires call |
| review_type | no (add) | add | lbw / caught / etc. |
| review_umpires_call | no (add) | add | the "umpire's call" bit |
| replacements_json | no (extract) | add as `replacement_player_in`, `replacement_player_out`, `replacement_team`, `replacement_reason` | Cricsheet per-ball impact-player events |
| _loaded_at | yes | skip | audit |
| _source_file | — | skip | audit |
| _run_id | — | skip | audit |

---

## bronze.people (22 cols) — Cricsheet player registry

Used only to populate `dim_players`. None flow directly to OBT; OBT picks up player attributes via `dim_players` + `stg_espn_players` joins.

| Column | In silver? | Plan for OBT | Reason |
|---|---|---|---|
| identifier | yes (as `player_id`) | via dim_players | — |
| name | yes (as `player_name`) | via dim_players | — |
| unique_name | yes | skip | stays in dim_players |
| key_bcci | yes | skip | cross-reference; stays in dim_players |
| key_bcci_2 | no (add to stg_people) | skip | same |
| key_bigbash | no (add to stg_people) | skip | same |
| key_cricbuzz | yes | skip | same |
| key_cricheroes | no (add) | skip | same |
| key_crichq | no (add) | skip | same |
| key_cricinfo | yes | via dim_players | used to join ESPN player bio |
| key_cricinfo_2 | no (add) | skip | secondary ESPN ID (rare duplicates) |
| key_cricinfo_3 | no (add) | skip | tertiary ESPN ID |
| key_cricingif | no (add) | skip | cross-reference |
| key_cricketarchive | no (add) | skip | cross-reference |
| key_cricketarchive_2 | no (add) | skip | cross-reference |
| key_cricketworld | no (add) | skip | cross-reference |
| key_nvplay | no (add) | skip | cross-reference |
| key_nvplay_2 | no (add) | skip | cross-reference |
| key_opta | no (add) | skip | cross-reference |
| key_opta_2 | no (add) | skip | cross-reference |
| key_pulse | no (add) | skip | cross-reference |
| key_pulse_2 | no (add) | skip | cross-reference |

---

## bronze.espn_matches (63 cols) — ESPN match-level

| Column | In silver? | Plan for OBT | Reason (if skipped) |
|---|---|---|---|
| espn_match_id | yes | already in | — |
| espn_series_id | yes | skip | match-level metadata; stays in dim_matches |
| floodlit | yes | already in | — |
| start_date | no (add to silver) | skip | duplicate of match_date |
| start_time | yes | already in (from dim_matches) | — |
| end_time | yes | already in | — |
| hours_info | yes | already in | — |
| season | no (add to silver as `season_espn`) | skip | we derive canonical season |
| title | no (add to silver) | skip | UI string |
| slug | no (add to silver) | skip | URL helper |
| status_text | no (add to silver) | skip | UI string |
| international_class_id | yes | already in | — |
| sub_class_id | yes | already in | — |
| espn_ground_id | yes | already in | — |
| ground_capacity | yes | already in | — |
| venue_timezone | yes | already in | — |
| team1_name | yes | already in (as team1) | — |
| team1_long_name | no (add to silver) | add | full team name |
| team1_espn_id | yes | skip | on dim_teams |
| team1_captain | yes | already in | — |
| team1_keeper | yes | already in | — |
| team1_is_home | yes | already in | — |
| team1_points | yes | add as `team1_points_before_match` | tournament standings going in |
| team1_primary_color | yes | skip | UI; on dim_teams |
| team2_name | yes | already in (as team2) | — |
| team2_long_name | no (add to silver) | add | full team name |
| team2_espn_id | yes | skip | on dim_teams |
| team2_captain | yes | already in | — |
| team2_keeper | yes | already in | — |
| team2_is_home | yes | already in | — |
| team2_points | yes | add as `team2_points_before_match` | tournament standings |
| team2_primary_color | yes | skip | UI; on dim_teams |
| team1_logo_url | no (add to silver) | skip | UI — served by images endpoint |
| team2_logo_url | no (add to silver) | skip | UI |
| venue_image_url | no (add to silver) | skip | UI |
| replacement_players_json | yes (passed) | extract into new silver model `stg_espn_replacements`; **ALSO join to OBT** on `(match_id, inning, over_decimal)` to add fields Cricsheet lacks: `replacement_player_in_espn_id`, `replacement_player_out_espn_id`, `replacement_type_code` (ESPN numeric), `replacement_over_decimal`. Cricsheet fields (replacement_player_in name, replacement_player_out name, replacement_team, replacement_reason) are also added — complementary. | |
| debut_players_json | yes (passed) | extract into new silver model `stg_espn_debut_players`; flag in OBT: `batter_is_debut_this_match`, `bowler_is_debut_this_match` | |
| teams_enrichment_json | yes (passed) | extract into new silver model `stg_espn_team_players`; flag in OBT: `batter_is_captain_this_match`, `batter_is_keeper_this_match`, `bowler_is_captain_this_match` | |
| cricsheet_match_id | yes (as join key) | — | — |
| mvp_player_id | no (add to silver) | add as `match_mvp_player_id` | ESPN smart-MVP |
| mvp_player_name | no (add) | add as `match_mvp_player_name` | — |
| mvp_team_id | no (add) | skip | redundant with team name |
| mvp_team_name | no (add) | add as `match_mvp_team_name` | — |
| mvp_batted_type | no (add) | skip | redundant with MVP runs > 0 |
| mvp_runs | no (add) | add as `match_mvp_runs` | — |
| mvp_balls_faced | no (add) | add as `match_mvp_balls_faced` | — |
| mvp_smart_runs | no (add) | add as `match_mvp_smart_runs` | ESPN's context-adjusted runs |
| mvp_bowled_type | no (add) | skip | redundant |
| mvp_wickets | no (add) | add as `match_mvp_wickets` | — |
| mvp_conceded | no (add) | add as `match_mvp_conceded` | — |
| mvp_smart_wickets | no (add) | add as `match_mvp_smart_wickets` | ESPN's context-adjusted wickets |
| mvp_fielded_type | no (add) | skip | redundant |
| mvp_batting_impact | no (add) | add as `match_mvp_batting_impact` | headline ESPN impact score |
| mvp_bowling_impact | no (add) | add as `match_mvp_bowling_impact` | — |
| mvp_total_impact | no (add) | add as `match_mvp_total_impact` | headline |
| player_of_match_json | no (add to silver) | skip | detail breakdown; queryable on demand from silver |
| ground_name | no (add to silver) | already in via dim_venues | — |
| ground_long_name | no (add to silver) | add via dim_venues | — |
| ground_country_name | no (add to silver) | add via dim_venues | country of venue |
| ground_country_abbreviation | no (add to silver) | add via dim_venues | — |
| ground_image_url | no (add to silver) | skip | UI |
| team1_abbreviation | no (add to silver) | add | 3-letter code (CSK, MI) |
| team2_abbreviation | no (add to silver) | add | 3-letter code |

---

## bronze.espn_players (26 cols) — ESPN player biodata

All 26 already in `stg_espn_players`. Reached via `dim_players` join (on `key_cricinfo = espn_player_id`).

| Column | Plan for OBT | Reason (if skipped) |
|---|---|---|
| espn_player_id | add as `batter_espn_id`, `bowler_espn_id` | — |
| player_name | skip | already have batter/bowler name from Cricsheet |
| player_long_name | skip | on dim_players |
| mobile_name | skip | name variant — on dim_players |
| index_name | skip | name variant |
| batting_name | skip | name variant |
| fielding_name | skip | name variant |
| slug | skip | URL helper |
| gender | skip | already on match |
| is_overseas | add as `batter_is_overseas`, `bowler_is_overseas` | IPL/CPL overseas-quota analytics |
| date_of_birth_year/month/day | skip | derive DOB instead |
| date_of_birth | derive `batter_age_at_match`, `bowler_age_at_match` | core context |
| date_of_death_* | skip | not analytical |
| country_team_id | add as `batter_country_team_id`, `bowler_country_team_id` | represented country |
| batting_styles | add as `batter_handedness` (rhb/lhb) | core |
| bowling_styles | add as `bowler_type` (pace/spin/medium), `bowler_handedness` | core |
| long_batting_styles | skip | UI version of batting_styles |
| long_bowling_styles | skip | UI version |
| playing_roles | add as `batter_role`, `bowler_role` | core |
| player_role_type_ids | skip | redundant with `playing_roles` text |
| image_url | skip | UI |
| headshot_image_url | skip | UI |
| downloaded_at | skip | audit |

---

## bronze.espn_innings (10 cols) — ESPN innings-level

| Column | In silver? | Plan for OBT | Reason |
|---|---|---|---|
| espn_match_id | yes | join key only | — |
| inning_number | yes | join key only | — |
| batting_team | yes | skip | redundant with OBT's batting_team |
| runs_saved | yes | add denormalized as `innings_runs_saved` | fielding value |
| catches_dropped | yes | add denormalized as `innings_catches_dropped` | fielding pressure |
| batsmen_details_json | yes (passed) | extract into new silver model `stg_espn_batting_innings`; join to OBT: `batter_batting_position` (1–11), `batter_batted_type` (yes/no/did_not_bat), `batter_minutes_at_crease`, `batter_espn_dismissal_short` | |
| partnerships_json | yes (passed) | extract into new silver model `stg_espn_partnerships`; **NOT in OBT** — wrong grain (one row per partnership) | |
| drs_reviews_json | yes (passed) | extract into new silver model `stg_espn_drs_reviews`; **ALSO join to OBT** on `(match_id, inning_number, overs_actual)` to add fields Cricsheet lacks: `drs_review_side`, `drs_is_umpire_call`, `drs_remaining_count`, `drs_original_decision`, `drs_decision`. Cricsheet fields (review_by/umpire/batter/decision/type/umpires_call) are still added — complementary. | |
| over_groups_json | yes (passed) | extract into new silver model `stg_espn_phase_summary`; **NOT in OBT** — aggregated summary, wrong grain. Low priority (only 5 non-empty across all matches) | |

---

## bronze.espn_ball_data (35 cols) — ESPN per-ball spatial/shot

All 35 in `stg_espn_ball_data`. Join to OBT on `(cricsheet_match_id, inning_number, over_number, ball_number)`.

| Column | Plan for OBT | Reason (if skipped) |
|---|---|---|
| cricsheet_match_id | join key | — |
| espn_match_id | join key | — |
| espn_ball_id | add | for join to ball commentary |
| inning_number | skip | redundant with Cricsheet `innings` |
| over_number | skip | redundant |
| ball_number | skip | redundant |
| overs_actual | add as `overs_actual_espn` | real over decimal (e.g. 15.2 = over 15 ball 2) |
| overs_unique | skip | reconciliation artifact |
| batsman_player_id | add as `espn_batsman_id` | ESPN IDs for joins |
| bowler_player_id | add as `espn_bowler_id` | — |
| non_striker_player_id | add as `espn_non_striker_id` | — |
| batsman_runs | skip | redundant with Cricsheet |
| total_runs | skip | redundant |
| total_inning_runs | skip | we compute via `in_match_window` |
| total_inning_wickets | skip | we compute via `in_match_window` |
| is_four | skip | redundant |
| is_six | skip | redundant |
| is_wicket | skip | redundant |
| dismissal_type | add as `espn_dismissal_type_code` | numeric code supplementing Cricsheet `wicket_kind` |
| out_player_id | add as `espn_out_player_id` | — |
| wides | skip | redundant with Cricsheet |
| noballs | skip | redundant |
| byes | skip | redundant |
| legbyes | skip | redundant |
| penalties | skip | redundant |
| wagon_x | add | wagon wheel coordinate |
| wagon_y | add | wagon wheel coordinate |
| wagon_zone | add | wagon wheel zone |
| pitch_line | add | bowling pitch map |
| pitch_length | add | bowling pitch map |
| shot_type | add | shot selection |
| shot_control | add | batting quality index |
| timestamp | add as `ball_timestamp` (ISO-8601) | real-time delivery datetime — ESPN-only field, ~37% coverage |
| predicted_score | skip | **belongs in Shape 4 `model_predicted_score`** (model output) |
| win_probability | skip | **belongs in Shape 4 `model_win_probability_timeline`** (model output) |

---

## bronze.espn_ball_commentary (17 cols) — ESPN per-ball commentary

**New silver model needed:** `stg_espn_ball_commentary`. Join to OBT on `espn_ball_id`.

| Column | Plan for OBT | Reason (if skipped) |
|---|---|---|
| espn_ball_id | join key | — |
| cricsheet_match_id | join key | — |
| espn_match_id | skip | already have |
| inning_number | skip | redundant |
| over_number | skip | redundant |
| ball_number | skip | redundant |
| title | add as `ball_title` | e.g. "Bumrah to Kohli" |
| commentary_text | add | main commentary sentence |
| pre_text | add | reader comments before ball |
| post_text | add | after-ball comments |
| smart_stats (JSON) | add **single column** `smart_stat_raw_json` (keep raw, rare — only 0.78% of balls) | flattening into 20 mostly-null columns rejected; we can compute any context-stat from fact_deliveries ourselves if needed |
| batsman_stat_text | add | per-ball batter stat text |
| bowler_stat_text | add | per-ball bowler stat text |
| dismissal_text (JSON) | add flat: `espn_dismissal_text_short`, `espn_dismissal_text_long`, `espn_dismissal_text_commentary`, `espn_dismissal_fielder_text`, `espn_dismissal_bowler_text` | rich dismissal descriptions |
| events (JSON) | add flags + details: `had_dropped_catch`, `dropped_catch_fielders`, `had_drs_review`, `drs_review_successful`, `had_run_out_chance`, `run_out_chance_fielders`, `had_stumping_chance`, `stumping_chance_fielder`, `had_player_replacement`. Keep full `events_json` too | **huge find** — dropped catches, run-out chances, stumping chances per ball |
| comment_images (JSON) | skip | UI only |
| over_summary (JSON) | add for last ball of each over: `is_maiden_over`, `over_runs_total`, `over_wickets_total`, `is_complete_over` | end-of-over summary fields worth denormalizing |

---

## bronze.espn_teams (12 cols) — ESPN team reference

All in `stg_espn_teams`. Consumed by `dim_teams`. No direct OBT join.

| Column | Plan | Reason |
|---|---|---|
| espn_team_id | via dim_teams | — |
| team_name, team_long_name, team_abbreviation, team_unofficial_name, team_slug | via dim_teams | — |
| is_country | via dim_teams | — |
| primary_color, image_url, country_name, country_abbreviation, downloaded_at | via dim_teams | skip OBT — UI + reference |

---

## bronze.espn_grounds (13 cols) — ESPN ground reference

All in `stg_espn_grounds`. Consumed by `dim_venues`. Extra fields flow into OBT via `dim_venues` join.

| Column | Plan for OBT | Reason (if skipped) |
|---|---|---|
| espn_ground_id | already in | — |
| ground_name | skip | redundant with venue |
| ground_long_name | add via dim_venues | full ground name |
| ground_small_name | skip | UI |
| ground_slug | skip | URL helper |
| town_name | skip | redundant with city |
| town_area | add via dim_venues | neighborhood/area (can differ from city) |
| timezone | already in (as venue_timezone) | — |
| country_name | add via dim_venues | country where venue is located |
| country_abbreviation | add via dim_venues | — |
| capacity | already in (ground_capacity) | — |
| image_url | skip | UI |
| downloaded_at | skip | audit |

---

## bronze.espn_series (6 cols) — ESPN series reference

**Not in silver today.** Add new model `stg_espn_series`. No direct OBT join (match-level; stays in `dim_matches`).

| Column | Plan | Reason |
|---|---|---|
| series_id | add to silver | — |
| series_name | add to silver | — |
| season | add to silver | — |
| series_slug | add to silver | — |
| discovered_from | add to silver | audit |
| created_at | add to silver | audit |

---

## bronze.venue_coordinates (7 cols)

All in `stg_venue_coordinates` → flow to OBT via `dim_venues`.

| Column | Plan for OBT | Reason (if skipped) |
|---|---|---|
| venue | join key | — |
| city | join key | — |
| latitude | already in (as `venue_latitude`) | — |
| longitude | already in (as `venue_longitude`) | — |
| formatted_address | add | full geocoded address |
| place_id | skip | Google reference ID — not analytical |
| geocode_status | skip | silver-level audit |

---

## bronze.weather (11 cols)

Join from `fact_weather` (which combines `stg_weather_hourly` + `stg_weather_daily`). Match-start-hour snapshot into OBT.

| Column | Plan for OBT | Reason |
|---|---|---|
| match_id | join key | — |
| match_date | join key | — |
| latitude, longitude, elevation | already in (from dim_venues) | — |
| timezone | already in (as venue_timezone) | — |
| utc_offset_seconds | skip | not needed per-ball |
| hourly_json | use via stg_weather_hourly | — |
| daily_json | use via stg_weather_daily | — |
| _loaded_at, _run_id | skip | audit |

Weather columns joined onto OBT from match-start hour:
- `weather_temp_c`, `weather_humidity_pct`, `weather_dew_point_c`, `weather_apparent_temp_c`
- `weather_precipitation_mm`, `weather_weather_code`, `weather_description`
- `weather_wind_speed_kmh`, `weather_wind_direction_deg`, `weather_wind_gusts_kmh`
- `weather_cloud_cover_pct`, `weather_is_day`
- Daily: `daily_temp_max_c`, `daily_temp_min_c`, `daily_wind_gusts_max_kmh`, `daily_precipitation_sum_mm`

---

## Derived / computed in OBT (not from any single bronze field)

| Column | Source | Reason |
|---|---|---|
| phase | max_overs + over_num | format-agnostic powerplay/middle/death (already in) |
| team_score_at_ball, team_wickets_at_ball, legal_balls_so_far_innings | `in_match_window` | already in |
| batter_score_at_ball, batter_balls_faced_at_ball | `in_match_window` | already in |
| bowler_runs_conceded_at_ball, bowler_legal_balls_at_ball, bowler_wickets_at_ball | `in_match_window` | already in |
| batter_career_* (from snapshot) | snapshot_player_career join | already in |
| bowler_career_* (from snapshot) | snapshot_player_career join | already in |
| required_run_rate | target_score + balls_remaining | **add** — 2nd-innings chase pressure |
| target_score | 1st innings total + 1 | **add** |
| balls_remaining_in_innings | max_overs × 6 − legal_balls_so_far_innings | **add** |
| is_day_night | floodlit + start_time hour | **add** — derived |
| batter_age_at_match | match_date − batter DOB | **add** |
| bowler_age_at_match | match_date − bowler DOB | **add** |

---

## New silver models needed

1. **`stg_espn_ball_commentary`** — all 17 cols from bronze, with `dismissal_text` and `events` JSON parsed into flag/text fields. Kept as JSON too for deep queries.
2. **`stg_espn_batting_innings`** — extracted from `batsmen_details_json`. Grain: `(espn_match_id, inning_number, espn_player_id)`.
3. **`stg_espn_partnerships`** — extracted from `partnerships_json`. Grain: `(espn_match_id, inning_number, partnership_number)`. Not joined to OBT.
4. **`stg_espn_drs_reviews`** — extracted from `drs_reviews_json`. Grain: `(espn_match_id, inning_number, review_number)`. Also joined to OBT at ball grain via `(match_id, innings, overs_actual)` — fields Cricsheet lacks are denormalized onto OBT (review_side, is_umpire_call, remaining_count, original_decision, drs_decision).
5. **`stg_espn_phase_summary`** — extracted from `over_groups_json`. Grain: `(espn_match_id, inning_number, phase_type)`. Low-priority (5 non-empty rows).
6. **`stg_espn_team_players`** — extracted from `teams_enrichment_json`. Grain: `(espn_match_id, espn_team_id, espn_player_id)`. Per-player per-match with role_code, is_captain, is_keeper.
7. **`stg_espn_debut_players`** — extracted from `debut_players_json`. Grain: `(espn_match_id, espn_player_id)`.
8. **`stg_espn_series`** — from `bronze.espn_series`. Grain: `series_id`.
9. **`stg_espn_replacements`** — extracted from `replacement_players_json`. Grain: `(espn_match_id, inning, over_decimal, player_in_id)`. Also joined to OBT at ball grain — ESPN fields (player_in_id, player_out_id, replacement_type code, over_decimal) denormalized onto OBT.

---

## Silver models updated

| Model | What's added |
|---|---|
| `stg_matches` | team_type, match_type_number, toss_uncontested, event_group, meta_created, meta_revision, officials parsed into umpire_1/2/tv/reserve/match_referee |
| `stg_deliveries` | non_boundary, review_by, review_umpire, review_batter, review_decision, review_type, review_umpires_call, replacements_json parsed into replacement_player_in/out/team/reason |
| `stg_espn_matches` | start_date, season_espn, title, slug, status_text, team1_long_name, team2_long_name, team1_abbreviation, team2_abbreviation, team1_logo_url, team2_logo_url, venue_image_url, all 14 MVP cols, player_of_match_json, ground_name, ground_long_name, ground_country_name, ground_country_abbreviation, ground_image_url |
| `stg_espn_ball_data` | add `ball_timestamp` (from bronze `timestamp`) — ISO-8601 datetime per ball, ~37% coverage |
| `stg_people` | all missing cross-reference IDs (key_cricinfo_2/3, key_bcci_2, key_bigbash, key_cricheroes, key_crichq, key_cricingif, key_cricketarchive/_2, key_cricketworld, key_nvplay/_2, key_opta/_2, key_pulse/_2) |
| `dim_venues` | ground_long_name, ground_country_name, ground_country_abbreviation, town_area, formatted_address |

---

## Summary — everything NOT in OBT and why

### Wrong grain (goes into own silver model or stays as reference)
- `partnerships_json` → `stg_espn_partnerships` (one row per partnership)
- `over_groups_json` → `stg_espn_phase_summary` (one row per phase)
- `drs_reviews_json` → `stg_espn_drs_reviews` (one row per review). ESPN DRS fields that Cricsheet lacks ARE joined to OBT at ball grain — the silver model is additionally kept for the review-level analytics.
- `teams_enrichment_json` → `stg_espn_team_players` (per-player per-match roles)
- `debut_players_json` → `stg_espn_debut_players`
- `players_team1_json`, `players_team2_json`, `registry_json` — match-level rosters
- `replacement_players_json` (ESPN) → `stg_espn_replacements` (one row per replacement event). ESPN fields that Cricsheet lacks ARE joined to OBT at ball grain.
- `player_of_match_json` — kept as JSON in silver for on-demand queries
- Series metadata (`bronze.espn_series`) — match-level reference

### UI-only / display-only
- All `*_logo_url`, `*_image_url`, `headshot_image_url`, `venue_image_url`, `ground_image_url`
- Team primary colors (on dim_teams)
- `title`, `slug`, `status_text` URL/UI helpers
- `comment_images` JSON (commentary photos)
- Player name variants (`mobile_name`, `index_name`, `batting_name`, `fielding_name`, `player_long_name`, `slug`)
- `long_batting_styles`, `long_bowling_styles` (UI versions of short codes)

### Redundant (already captured from a better source)
- ESPN `batsman_runs`, `total_runs`, `is_four`, `is_six`, `is_wicket`, `wides`, `noballs`, `byes`, `legbyes`, `penalties` — Cricsheet is source of truth
- ESPN `inning_number`, `over_number`, `ball_number` — same grain as Cricsheet
- ESPN `overs_unique` — reconciliation artifact
- ESPN `start_date` — duplicate of match_date
- ESPN `season` — we derive canonical season
- `player_role_type_ids` — redundant with `playing_roles` text
- `date_of_birth_year/month/day` — derive `date_of_birth` instead
- ESPN `gender` on players — already on match
- ESPN `batting_team` on innings — already in OBT
- `balls_per_over` — always 6

### Model outputs (Shape 4 — not OBT)
- ESPN `predicted_score` → `model_predicted_score`
- ESPN `win_probability` → `model_win_probability_timeline`

### Empty across full dataset
- `supersubs_json` — 0 non-empty rows across all matches
- `missing_json` — 0 non-empty rows

### Audit-only
- `_loaded_at`, `_source_file`, `_run_id`, `_is_valid_extras`, `_is_valid_total`, `downloaded_at`, `data_version`

### Chose not to flatten
- `smart_stats` — 0.78% coverage (2,219 of 283,803 balls). Contextual historical aggregates (e.g. "batter's SR in death overs") that we can derive ourselves from fact_deliveries. Kept as single `smart_stat_raw_json` column for preservation. Not flattened because heavy NULL fan-out and recomputable.

---

## Status

| Item | Status |
|---|---|
| Full catalog documented (this file) | done |
| Silver model updates (stg_matches, stg_deliveries, stg_espn_matches, stg_people, dim_venues) | todo |
| New silver models (8 listed above) | todo |
| OBT rewrite with expanded columns (~170–180 final count) | todo |
| schema.yml documentation for new models and OBT | todo |
| Run `make transform` → `make dbt-test` → `make test` | todo |
