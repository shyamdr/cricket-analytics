"""Centralized configuration for the cricket-analytics project.

Dataset configuration is loaded from config/datasets.yml — the single
source of truth for what data gets ingested and enriched.

The CRICSHEET_DATASETS dict is computed from the YAML at import time,
maintaining backward compatibility with all existing consumers.
"""

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import field_validator
from pydantic_settings import BaseSettings

# ---------------------------------------------------------------------------
# Dataset configuration — loaded from config/datasets.yml
# ---------------------------------------------------------------------------

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
_DATASETS_YAML = _CONFIG_DIR / "datasets.yml"


def _load_datasets_config() -> dict[str, Any]:
    """Load and return the full datasets.yml config."""
    with open(_DATASETS_YAML) as f:
        return yaml.safe_load(f)


def _build_cricsheet_datasets(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Build the CRICSHEET_DATASETS lookup from the YAML config.

    Returns a dict mapping dataset keys to {"url": ..., "name": ...}
    for backward compatibility with downloader.py and other consumers.
    Includes both regular datasets and delta feeds.
    """
    result: dict[str, dict[str, str]] = {}

    for key, ds in config.get("datasets", {}).items():
        result[key] = {"url": ds["url"], "name": ds["name"]}

    for key, feed in config.get("delta_feeds", {}).items():
        result[key] = {"url": feed["url"], "name": feed["name"]}

    return result


def get_enabled_datasets(config: dict[str, Any] | None = None) -> list[str]:
    """Return list of dataset keys where enabled=true in the YAML."""
    if config is None:
        config = _load_datasets_config()
    return [
        key
        for key, ds in config.get("datasets", {}).items()
        if ds.get("enabled", False)
    ]


def get_profile_datasets(profile_name: str, config: dict[str, Any] | None = None) -> list[str]:
    """Return dataset keys for a named profile.

    Raises ValueError if the profile doesn't exist.
    """
    if config is None:
        config = _load_datasets_config()
    profiles = config.get("profiles", {})
    if profile_name not in profiles:
        available = ", ".join(sorted(profiles.keys()))
        raise ValueError(f"Unknown profile '{profile_name}'. Available: {available}")
    return profiles[profile_name]["datasets"]


def get_default_datasets(config: dict[str, Any] | None = None) -> list[str]:
    """Return dataset keys for the default profile defined in the YAML."""
    if config is None:
        config = _load_datasets_config()
    default_profile = config.get("default_profile", "standard")
    return get_profile_datasets(default_profile, config)


def get_dataset_config(dataset_key: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the full config dict for a single dataset.

    Raises KeyError if the dataset doesn't exist.
    """
    if config is None:
        config = _load_datasets_config()
    datasets = config.get("datasets", {})
    if dataset_key not in datasets:
        available = ", ".join(sorted(datasets.keys()))
        raise KeyError(f"Unknown dataset '{dataset_key}'. Available: {available}")
    return datasets[dataset_key]


# Load config at import time — fail fast if YAML is missing/broken
datasets_config = _load_datasets_config()
CRICSHEET_DATASETS = _build_cricsheet_datasets(datasets_config)


# ---------------------------------------------------------------------------
# Application settings
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    """Application settings, overridable via environment variables."""

    # Paths
    project_root: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = project_root / "data"
    raw_dir: Path = data_dir / "raw"
    duckdb_path: Path = data_dir / "cricket.duckdb"

    # Cricsheet source URLs (kept for backward compat — prefer datasets.yml)
    cricsheet_matches_url: str = "https://cricsheet.org/downloads/ipl_json.zip"
    cricsheet_people_url: str = "https://cricsheet.org/register/people.csv"

    # DuckDB schemas (medallion layers)
    # Bronze is created by Python ingestion; silver/gold are created by dbt
    # which prefixes with the DuckDB database name ("main_").
    bronze_schema: str = "bronze"
    silver_schema: str = "main_silver"
    gold_schema: str = "main_gold"

    @field_validator("bronze_schema", "silver_schema", "gold_schema")
    @classmethod
    def validate_schema_name(cls, v: str) -> str:
        """Reject schema names that aren't valid SQL identifiers.

        Prevents SQL injection via CRICKET_GOLD_SCHEMA env var etc.
        Schema names are interpolated into f-strings throughout the
        codebase, so they must be safe identifiers.
        """
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            raise ValueError(f"Invalid schema name: {v!r}")
        return v

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # UI
    ui_port: int = 8501

    # Enrichment
    enrichment_batch_size: int = 50

    model_config = {"env_prefix": "CRICKET_"}


settings = Settings()
