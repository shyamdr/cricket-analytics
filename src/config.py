"""Centralized configuration for the cricket-analytics project."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, overridable via environment variables."""

    # Paths
    project_root: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = project_root / "data"
    raw_dir: Path = data_dir / "raw"
    duckdb_path: Path = data_dir / "cricket.duckdb"

    # Cricsheet source URLs
    cricsheet_matches_url: str = "https://cricsheet.org/downloads/ipl_json.zip"
    cricsheet_people_url: str = "https://cricsheet.org/register/people.csv"

    # DuckDB schemas (medallion layers)
    bronze_schema: str = "bronze"
    silver_schema: str = "silver"
    gold_schema: str = "gold"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # UI
    ui_port: int = 8501

    model_config = {"env_prefix": "CRICKET_"}


settings = Settings()
