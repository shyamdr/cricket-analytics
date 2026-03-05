"""dbt assets — silver and gold layer transformations."""

from __future__ import annotations

from pathlib import Path

from dagster_dbt import (
    DagsterDbtTranslator,
    DagsterDbtTranslatorSettings,
    DbtCliResource,
    DbtProject,
    dbt_assets,
)

DBT_PROJECT_DIR = Path(__file__).resolve().parent.parent.parent / "dbt"

dbt_project = DbtProject(project_dir=DBT_PROJECT_DIR)

# Always re-parse in dev to pick up sources.yml / schema.yml changes.
# prepare_if_dev() only creates the manifest if missing — it won't
# detect changes to source meta (e.g. asset_key mappings), which can
# cause stale circular-dependency errors in Dagster.
_manifest = dbt_project.manifest_path
if _manifest.exists():
    _manifest.unlink()
dbt_project.prepare_if_dev()


dagster_dbt_translator = DagsterDbtTranslator(
    settings=DagsterDbtTranslatorSettings(enable_duplicate_source_asset_keys=True),
)


@dbt_assets(
    manifest=dbt_project.manifest_path,
    project=dbt_project,
    dagster_dbt_translator=dagster_dbt_translator,
)
def dbt_analytics_assets(context, dbt: DbtCliResource):
    """Run all dbt models (silver + gold) as Dagster assets."""
    yield from dbt.cli(["build"], context=context).stream()
