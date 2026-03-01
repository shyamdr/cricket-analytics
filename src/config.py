"""Centralized configuration for the cricket-analytics project."""

from pathlib import Path

from pydantic_settings import BaseSettings

# Cricsheet dataset registry — maps dataset keys to download URLs.
# All follow the pattern: https://cricsheet.org/downloads/{slug}_json.zip
CRICSHEET_DATASETS: dict[str, dict[str, str]] = {
    # Club T20 leagues
    "ipl": {
        "url": "https://cricsheet.org/downloads/ipl_json.zip",
        "name": "Indian Premier League",
    },
    "bbl": {
        "url": "https://cricsheet.org/downloads/bbl_json.zip",
        "name": "Big Bash League",
    },
    "psl": {
        "url": "https://cricsheet.org/downloads/psl_json.zip",
        "name": "Pakistan Super League",
    },
    "cpl": {
        "url": "https://cricsheet.org/downloads/cpl_json.zip",
        "name": "Caribbean Premier League",
    },
    "lpl": {
        "url": "https://cricsheet.org/downloads/lpl_json.zip",
        "name": "Lanka Premier League",
    },
    "sa20": {
        "url": "https://cricsheet.org/downloads/sa20_json.zip",
        "name": "SA20",
    },
    "ilt20": {
        "url": "https://cricsheet.org/downloads/ilt20_json.zip",
        "name": "International League T20",
    },
    "bpl": {
        "url": "https://cricsheet.org/downloads/bpl_json.zip",
        "name": "Bangladesh Premier League",
    },
    # International formats
    "t20i": {
        "url": "https://cricsheet.org/downloads/t20s_male_json.zip",
        "name": "T20 Internationals (Men)",
    },
    "odi": {
        "url": "https://cricsheet.org/downloads/odis_male_json.zip",
        "name": "ODI (Men)",
    },
    "test": {
        "url": "https://cricsheet.org/downloads/tests_male_json.zip",
        "name": "Test Matches (Men)",
    },
    # Delta / recent
    "recent_7": {
        "url": "https://cricsheet.org/downloads/recently_added_7_json.zip",
        "name": "Recently Added (7 days)",
    },
    "recent_30": {
        "url": "https://cricsheet.org/downloads/recently_added_30_json.zip",
        "name": "Recently Added (30 days)",
    },
}


class Settings(BaseSettings):
    """Application settings, overridable via environment variables."""

    # Paths
    project_root: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = project_root / "data"
    raw_dir: Path = data_dir / "raw"
    duckdb_path: Path = data_dir / "cricket.duckdb"

    # Cricsheet source URLs (kept for backward compat)
    cricsheet_matches_url: str = "https://cricsheet.org/downloads/ipl_json.zip"
    cricsheet_people_url: str = "https://cricsheet.org/register/people.csv"

    # DuckDB schemas (medallion layers)
    # Bronze is created by Python ingestion; silver/gold are created by dbt
    # which prefixes with the DuckDB database name ("main_").
    bronze_schema: str = "bronze"
    silver_schema: str = "main_silver"
    gold_schema: str = "main_gold"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # UI
    ui_port: int = 8501

    model_config = {"env_prefix": "CRICKET_"}


settings = Settings()
