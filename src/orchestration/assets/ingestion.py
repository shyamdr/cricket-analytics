"""Bronze layer assets — download from Cricsheet and load into DuckDB."""

from dagster import AssetExecutionContext, MaterializeResult, MetadataValue, asset

from src.ingestion.bronze_loader import load_matches_to_bronze, load_people_to_bronze
from src.ingestion.download_people import download_people
from src.ingestion.downloader import download_matches


@asset(
    group_name="bronze",
    compute_kind="python",
    description="Download IPL match JSONs from Cricsheet and load into DuckDB bronze.matches + bronze.deliveries.",
)
def bronze_matches(context: AssetExecutionContext) -> MaterializeResult:
    """Download match data and load into bronze layer."""
    context.log.info("Downloading match data from Cricsheet...")
    matches_dir = download_matches()

    context.log.info("Loading matches into DuckDB bronze layer...")
    match_count = load_matches_to_bronze(matches_dir)

    return MaterializeResult(
        metadata={
            "matches_loaded": MetadataValue.int(match_count),
            "source": MetadataValue.url("https://cricsheet.org/downloads/ipl_json.zip"),
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
