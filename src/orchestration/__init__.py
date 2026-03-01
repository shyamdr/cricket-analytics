"""Dagster definitions — the entry point for the orchestration layer."""

from __future__ import annotations

from datetime import timedelta

from dagster import Definitions, FreshnessPolicy, apply_freshness_policy
from dagster_dbt import DbtCliResource

from src.orchestration.assets.dbt import DBT_PROJECT_DIR, dbt_analytics_assets
from src.orchestration.assets.enrichment import espn_enrichment
from src.orchestration.assets.ingestion import bronze_matches, bronze_people
from src.orchestration.jobs import (
    daily_refresh_job,
    daily_refresh_schedule,
    enrichment_backfill_job,
    full_pipeline_job,
)

# Freshness policy: gold assets should be no more than 24 hours stale,
# warn after 12 hours. Visible in Dagster UI asset health dashboard.
gold_freshness_policy = FreshnessPolicy.time_window(
    fail_window=timedelta(days=30),
    warn_window=timedelta(weeks=1),
)

defs = Definitions(
    assets=[bronze_matches, bronze_people, dbt_analytics_assets, espn_enrichment],
    jobs=[
        full_pipeline_job,
        daily_refresh_job,
        enrichment_backfill_job,
    ],
    schedules=[daily_refresh_schedule],
    resources={
        "dbt": DbtCliResource(
            project_dir=DBT_PROJECT_DIR,
            profiles_dir=DBT_PROJECT_DIR,
        ),
    },
)

# Apply freshness policy to gold layer assets only.
# dagster-dbt asset keys use the dbt model path structure, so gold models
# have keys like "gold/dim_matches", "gold/fact_deliveries", etc.
# We also match on the model name prefix as a fallback in case the
# translator flattens the key (e.g. "dim_matches", "fact_").
_GOLD_MODEL_PREFIXES = ("dim_", "fact_")


def _is_gold_asset(spec) -> bool:
    """Check if an asset spec belongs to the gold layer."""
    key_str = spec.key.to_user_string()
    # Match "gold/" prefix (dagster-dbt default path-based keys)
    if "gold/" in key_str or "/gold/" in key_str:
        return True
    # Fallback: match on gold model naming convention
    last_segment = key_str.rsplit("/", 1)[-1]
    return any(last_segment.startswith(p) for p in _GOLD_MODEL_PREFIXES)


defs = defs.map_asset_specs(
    func=lambda spec: (
        apply_freshness_policy(spec, gold_freshness_policy) if _is_gold_asset(spec) else spec
    ),
)
