"""CLI entry point for the ingestion pipeline."""

import structlog

from src.ingestion.bronze_loader import load_matches_to_bronze, load_people_to_bronze
from src.ingestion.download_people import download_people
from src.ingestion.downloader import download_matches

logger = structlog.get_logger(__name__)


def run_ingestion() -> None:
    """Run the full ingestion pipeline: download + load to bronze."""
    logger.info("ingestion_started")

    # Download raw data
    matches_dir = download_matches()
    people_csv = download_people()

    # Load into DuckDB bronze layer
    match_count = load_matches_to_bronze(matches_dir)
    people_count = load_people_to_bronze(people_csv)

    logger.info(
        "ingestion_complete",
        matches_loaded=match_count,
        people_loaded=people_count,
    )


if __name__ == "__main__":
    run_ingestion()
