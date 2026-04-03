"""dbt assets — silver and gold layer transformations."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from dagster_dbt import (
    DagsterDbtTranslator,
    DagsterDbtTranslatorSettings,
    DbtCliResource,
    DbtProject,
    dbt_assets,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

DBT_PROJECT_DIR = Path(__file__).resolve().parent.parent.parent / "dbt"

dbt_project = DbtProject(project_dir=DBT_PROJECT_DIR)

# prepare_if_dev() creates the manifest if missing.
# We don't delete it proactively — if sources.yml changes cause stale
# asset key issues, run `make transform` to regenerate the manifest.
dbt_project.prepare_if_dev()


class CricketDbtTranslator(DagsterDbtTranslator):
    """Custom translator to assign dbt models to medallion layer groups."""

    def __init__(self) -> None:
        super().__init__(
            settings=DagsterDbtTranslatorSettings(enable_duplicate_source_asset_keys=True),
        )

    def get_group_name(self, dbt_resource_props: Mapping[str, Any]) -> str | None:
        fqn = dbt_resource_props.get("fqn", [])
        # fqn looks like ["cricket_analytics", "silver", "stg_matches"]
        # or ["cricket_analytics", "gold", "dim_venues"]
        for part in fqn:
            if part in ("silver", "gold"):
                return part
        return "default"


dagster_dbt_translator = CricketDbtTranslator()


@dbt_assets(
    manifest=dbt_project.manifest_path,
    project=dbt_project,
    dagster_dbt_translator=dagster_dbt_translator,
)
def dbt_analytics_assets(context, dbt: DbtCliResource):
    """Run all dbt models (silver + gold) as Dagster assets."""
    yield from dbt.cli(["build"], context=context).stream()
