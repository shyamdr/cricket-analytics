"""Dagster job definitions for the cricket-analytics pipeline."""

from __future__ import annotations

from dagster import AssetSelection, define_asset_job

# Full pipeline: ingest bronze, then run dbt (silver + gold)
full_pipeline_job = define_asset_job(
    name="full_pipeline",
    selection=AssetSelection.all(),
    description="Run the complete pipeline: download from Cricsheet → bronze → silver → gold.",
)

# Ingestion only: just the bronze layer
ingestion_job = define_asset_job(
    name="ingestion_only",
    selection=AssetSelection.groups("bronze"),
    description="Download from Cricsheet and load into DuckDB bronze layer only.",
)

# Transformation only: just dbt (silver + gold)
transformation_job = define_asset_job(
    name="transformation_only",
    selection=AssetSelection.all() - AssetSelection.groups("bronze"),
    description="Run dbt transformations only (bronze → silver → gold).",
)
