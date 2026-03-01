"""Dagster job definitions for the cricket-analytics pipeline."""

from __future__ import annotations

from dagster import AssetSelection, RunConfig, ScheduleDefinition, define_asset_job

from src.orchestration.assets.ingestion import IngestionConfig

# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

# Full pipeline: ingest bronze → dbt (silver + gold) → enrichment
full_pipeline_job = define_asset_job(
    name="full_pipeline",
    selection=AssetSelection.all(),
    description="Run the complete pipeline: download from Cricsheet → bronze → silver → gold → enrichment.",
)

# Daily refresh: ingest recent matches → dbt auto-runs downstream → enrichment auto-runs downstream
daily_refresh_job = define_asset_job(
    name="daily_refresh",
    selection=AssetSelection.all(),
    description=(
        "Delta pipeline: ingest recent matches from Cricsheet, "
        "run dbt (silver + gold), then enrich new matches via ESPN."
    ),
    config=RunConfig(
        ops={
            "bronze_matches": IngestionConfig(datasets=["recent_7"], full_refresh=False),
        }
    ),
)

# Enrichment backfill: manually scrape historical seasons
enrichment_backfill_job = define_asset_job(
    name="enrichment_backfill",
    selection=AssetSelection.groups("enrichment"),
    description="Scrape ESPN match data for historical seasons (manual backfill).",
)

# ---------------------------------------------------------------------------
# Schedules
# ---------------------------------------------------------------------------

# Daily at 06:00 UTC — pick up new matches from Cricsheet (recent_7)
daily_refresh_schedule = ScheduleDefinition(
    job=daily_refresh_job,
    cron_schedule="0 6 * * *",
    name="daily_refresh",
    description="Daily at 06:00 UTC — ingest recent Cricsheet matches, transform, enrich.",
)
