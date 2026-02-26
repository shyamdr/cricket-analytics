"""Dagster job definitions for the cricket-analytics pipeline."""

from __future__ import annotations

from dagster import AssetSelection, ScheduleDefinition, define_asset_job

# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

# Full pipeline: ingest bronze → dbt (silver + gold)
full_pipeline_job = define_asset_job(
    name="full_pipeline",
    selection=AssetSelection.all(),
    description="Run the complete pipeline: download from Cricsheet → bronze → silver → gold → enrichment.",
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
    selection=AssetSelection.groups("bronze", "enrichment").downstream()
    - AssetSelection.groups("bronze", "enrichment"),
    description="Run dbt transformations only (bronze → silver → gold).",
)

# Enrichment only: ESPN scraping
enrichment_job = define_asset_job(
    name="enrichment_only",
    selection=AssetSelection.groups("enrichment"),
    description="Scrape ESPN match data (captain, keeper, roles, floodlit, start time).",
)

# Delta ingestion: recent matches + dbt rebuild
delta_pipeline_job = define_asset_job(
    name="delta_pipeline",
    selection=AssetSelection.groups("bronze") | AssetSelection.groups("enrichment").upstream(),
    description=(
        "Delta pipeline: ingest recent matches from Cricsheet, "
        "run dbt, then enrich new matches via ESPN."
    ),
    config={
        "ops": {
            "bronze_matches": {
                "config": {
                    "datasets": ["recent_7"],
                    "full_refresh": False,
                }
            }
        }
    },
)

# ---------------------------------------------------------------------------
# Schedules
# ---------------------------------------------------------------------------

# Daily delta: pick up new matches from Cricsheet (recent_7) at 6 AM UTC
daily_delta_schedule = ScheduleDefinition(
    job=delta_pipeline_job,
    cron_schedule="0 6 * * *",
    name="daily_delta_ingestion",
    description="Daily at 06:00 UTC — ingest recent Cricsheet matches, transform, enrich.",
)
