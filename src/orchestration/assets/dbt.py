"""dbt assets — silver and gold layer transformations."""

from __future__ import annotations

from pathlib import Path

from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

DBT_PROJECT_DIR = Path(__file__).resolve().parent.parent.parent / "dbt"

dbt_project = DbtProject(project_dir=DBT_PROJECT_DIR)
dbt_project.prepare_if_dev()


@dbt_assets(
    manifest=dbt_project.manifest_path,
    project=dbt_project,
)
def dbt_analytics_assets(context, dbt: DbtCliResource):
    """Run all dbt models (silver + gold) as Dagster assets."""
    yield from dbt.cli(["build"], context=context).stream()
