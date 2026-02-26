"""CLI entry point for the ingestion pipeline.

Usage:
    # Ingest IPL (default, backward compatible)
    python -m src.ingestion.run

    # Ingest a specific dataset
    python -m src.ingestion.run --dataset ipl
    python -m src.ingestion.run --dataset t20i
    python -m src.ingestion.run --dataset bbl

    # Ingest multiple datasets
    python -m src.ingestion.run --dataset ipl t20i odi

    # Delta ingestion (recently added matches from Cricsheet)
    python -m src.ingestion.run --recent

    # Full refresh (drop + rebuild bronze tables)
    python -m src.ingestion.run --dataset ipl --full-refresh

    # List available datasets
    python -m src.ingestion.run --list
"""

from __future__ import annotations

import argparse

import structlog

from src.config import CRICSHEET_DATASETS
from src.ingestion.bronze_loader import load_matches_to_bronze, load_people_to_bronze
from src.ingestion.download_people import download_people
from src.ingestion.downloader import download_dataset

logger = structlog.get_logger(__name__)


def run_ingestion(
    datasets: list[str] | None = None,
    recent: bool = False,
    full_refresh: bool = False,
    skip_people: bool = False,
) -> None:
    """Run the ingestion pipeline for one or more datasets.

    Args:
        datasets: List of dataset keys (e.g. ['ipl', 't20i']).
                  Defaults to ['ipl'] if not specified.
        recent: If True, use Cricsheet's recently_added_7 for delta.
        full_refresh: If True, drop and rebuild bronze tables.
        skip_people: If True, skip people.csv download.
    """
    if recent:
        # Delta mode — download recently added matches (last 7 days)
        datasets_to_ingest = ["recent_7"]
    elif datasets:
        datasets_to_ingest = datasets
    else:
        datasets_to_ingest = ["ipl"]

    logger.info("ingestion_started", datasets=datasets_to_ingest, full_refresh=full_refresh)

    total_new = 0
    for ds_key in datasets_to_ingest:
        logger.info("ingesting_dataset", dataset=ds_key)
        matches_dir = download_dataset(ds_key)
        new_count = load_matches_to_bronze(matches_dir, full_refresh=full_refresh)
        total_new += new_count
        # Only full_refresh on the first dataset if multiple
        full_refresh = False

    # People registry — always refresh (it's a small CSV, ~1MB)
    if not skip_people:
        people_csv = download_people()
        load_people_to_bronze(people_csv)

    logger.info("ingestion_complete", new_matches=total_new)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cricsheet ingestion pipeline")
    parser.add_argument(
        "--dataset",
        nargs="+",
        help="Dataset(s) to ingest (e.g. ipl t20i bbl). Default: ipl",
    )
    parser.add_argument(
        "--recent",
        action="store_true",
        help="Delta mode: ingest recently added matches (last 7 days)",
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Drop and rebuild bronze tables from scratch",
    )
    parser.add_argument(
        "--skip-people",
        action="store_true",
        help="Skip people.csv download",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_datasets",
        help="List available datasets and exit",
    )
    args = parser.parse_args()

    if args.list_datasets:
        print("Available datasets:")
        for key, ds in sorted(CRICSHEET_DATASETS.items()):
            print(f"  {key:12s}  {ds['name']}")
        return

    run_ingestion(
        datasets=args.dataset,
        recent=args.recent,
        full_refresh=args.full_refresh,
        skip_people=args.skip_people,
    )


if __name__ == "__main__":
    main()
