"""Centralized table references for the cricket-analytics project.

Single source of truth for all fully-qualified table names.
Import from here instead of building f-strings with settings.gold_schema
in every router/page. If a table is renamed or a schema changes,
update it here — one place, not 20 files.
"""

from src.config import settings

# Gold layer (analytics-ready)
MATCHES = f"{settings.gold_schema}.dim_matches"
PLAYERS = f"{settings.gold_schema}.dim_players"
TEAMS = f"{settings.gold_schema}.dim_teams"
VENUES = f"{settings.gold_schema}.dim_venues"
DELIVERIES = f"{settings.gold_schema}.fact_deliveries"
BATTING_INNINGS = f"{settings.gold_schema}.fact_batting_innings"
BOWLING_INNINGS = f"{settings.gold_schema}.fact_bowling_innings"
MATCH_SUMMARY = f"{settings.gold_schema}.fact_match_summary"
WEATHER = f"{settings.gold_schema}.fact_weather"

# Bronze layer (raw)
BRONZE_MATCHES = f"{settings.bronze_schema}.matches"
BRONZE_DELIVERIES = f"{settings.bronze_schema}.deliveries"
BRONZE_PEOPLE = f"{settings.bronze_schema}.people"
BRONZE_ESPN_MATCHES = f"{settings.bronze_schema}.espn_matches"
BRONZE_ESPN_PLAYERS = f"{settings.bronze_schema}.espn_players"
BRONZE_ESPN_INNINGS = f"{settings.bronze_schema}.espn_innings"
BRONZE_ESPN_BALL_DATA = f"{settings.bronze_schema}.espn_ball_data"
BRONZE_VENUE_COORDS = f"{settings.bronze_schema}.venue_coordinates"
BRONZE_WEATHER = f"{settings.bronze_schema}.weather"
