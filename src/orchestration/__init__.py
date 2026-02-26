"""Dagster definitions — the entry point for the orchestration layer."""

from __future__ import annotations

from dagster import Definitions
from dagster_dbt import DbtCliResource

from src.orchestration.assets.dbt import DBT_PROJECT_DIR, dbt_analytics_assets
from src.orchestration.assets.enrichment import espn_enrichment
from src.orchestration.assets.ingestion import bronze_matches, bronze_people
from src.orchestration.jobs import (
    daily_delta_schedule,
    delta_pipeline_job,
    enrichment_job,
    full_pipeline_job,
    ingestion_job,
    transformation_job,
)

defs = Definitions(
    assets=[bronze_matches, bronze_people, dbt_analytics_assets, espn_enrichment],
    jobs=[
        full_pipeline_job,
        ingestion_job,
        transformation_job,
        enrichment_job,
        delta_pipeline_job,
    ],
    schedules=[daily_delta_schedule],
    resources={
        "dbt": DbtCliResource(
            project_dir=DBT_PROJECT_DIR,
            profiles_dir=DBT_PROJECT_DIR,
        ),
    },
)
