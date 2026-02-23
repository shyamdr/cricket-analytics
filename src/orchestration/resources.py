"""Shared Dagster resources for the cricket-analytics pipeline."""

from __future__ import annotations

from dagster import ConfigurableResource

from src.config import settings


class CricketAnalyticsConfig(ConfigurableResource):
    """Central configuration resource exposing project settings to assets."""

    duckdb_path: str = str(settings.duckdb_path)
    raw_dir: str = str(settings.raw_dir)
    dbt_project_dir: str = str(settings.project_root / "src" / "dbt")
    dbt_profiles_dir: str = str(settings.project_root / "src" / "dbt")
