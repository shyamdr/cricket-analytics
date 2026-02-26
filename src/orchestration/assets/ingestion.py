"""Bronze layer assets — download from Cricsheet and load into DuckDB.

Supports multi-dataset ingestion and delta loading. The dataset(s) to
ingest are configured via Dagster run config.
"""

from dagster import AssetExecutionContext, Config, MaterializeResult, MetadataValue, asset

from src.config import CRICSHEET_DATASETS
from src.ingestion.bronze_loader import load_matches_to_bronze, load_people_to_bronze
from src.ingestion.download_people import download_people
from src.ingestion.downloader import download_dataset


class IngestionConfig(Config):
    """Configuration for the bronze_matches asset."""

    datasets: list[str] = ["ipl"]
    full_refresh: bool = False


@asset(
    group_name="bronze",
    compute_kind="python",
    description=(
        "Download match JSONs from Cricsheet and load into DuckDB bronze layer. "
        "Supports multiple datasets (ipl, t20i, odi, bbl, etc.) and delta loading."
    ),
)
def bronze_matches(context: AssetExecutionContext, config: IngestionConfig) -> MaterializeResult:
    """Download match data and load into bronze layer (delta-aware)."""
    total_new = 0
    datasets_summary: dict[str, int] = {}
    is_first = True

    for ds_key in config.datasets:
        ds_info = CRICSHEET_DATASETS.get(ds_key, {})
        context.log.info(f"Ingesting dataset: {ds_key} ({ds_info.get('name', ds_key)})")

        matches_dir = download_dataset(ds_key)

        # Only full_refresh on the first dataset
        refresh = config.full_refresh and is_first
        new_count = load_matches_to_bronze(matches_dir, full_refresh=refresh)
        is_first = False

        total_new += new_count
        datasets_summary[ds_key] = new_count
        context.log.info(f"  {ds_key}: {new_count} new matches loaded")

    return MaterializeResult(
        metadata={
            "new_matches_loaded": MetadataValue.int(total_new),
            "datasets": MetadataValue.json(datasets_summary),
        }
    )


@asset(
    group_name="bronze",
    compute_kind="python",
    description="Download people registry CSV from Cricsheet and load into DuckDB bronze.people.",
)
def bronze_people(context: AssetExecutionContext) -> MaterializeResult:
    """Download people data and load into bronze layer."""
    context.log.info("Downloading people registry from Cricsheet...")
    people_csv = download_people()

    context.log.info("Loading people into DuckDB bronze layer...")
    people_count = load_people_to_bronze(people_csv)

    return MaterializeResult(
        metadata={
            "people_loaded": MetadataValue.int(people_count),
            "source": MetadataValue.url("https://cricsheet.org/register/people.csv"),
        }
    )
