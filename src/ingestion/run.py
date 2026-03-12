"""CLI entry point for the ingestion pipeline.

Usage:
    # Ingest using default profile (from config/datasets.yml)
    python -m src.ingestion.run

    # Ingest using a named profile
    python -m src.ingestion.run --profile minimal
    python -m src.ingestion.run --profile t20_all

    # Ingest only enabled datasets (all datasets with enabled: true)
    python -m src.ingestion.run --enabled

    # Ingest specific datasets (overrides profile/enabled)
    python -m src.ingestion.run --dataset ipl
    python -m src.ingestion.run --dataset ipl t20i bbl

    # Delta ingestion (recently added matches from Cricsheet)
    python -m src.ingestion.run --recent

    # Full refresh (drop + rebuild bronze tables)
    python -m src.ingestion.run --full-refresh

    # List available datasets and profiles
    python -m src.ingestion.run --list
"""

from __future__ import annotations

import argparse

import structlog

from src.config import (
    datasets_config,
    get_default_datasets,
    get_enabled_datasets,
    get_profile_datasets,
)
from src.ingestion.bronze_loader import load_matches_to_bronze, load_people_to_bronze
from src.ingestion.download_people import download_people
from src.ingestion.downloader import download_dataset

logger = structlog.get_logger(__name__)


def run_ingestion(
    datasets: list[str] | None = None,
    profile: str | None = None,
    enabled_only: bool = False,
    recent: bool = False,
    full_refresh: bool = False,
    skip_people: bool = False,
) -> None:
    """Run the ingestion pipeline for one or more datasets.

    Resolution order for which datasets to ingest:
      1. --recent flag → uses delta feed (recent_7)
      2. --dataset flag → explicit list
      3. --enabled flag → all datasets with enabled: true in YAML
      4. --profile flag → named profile from YAML
      5. default → default_profile from YAML (typically "standard")

    Args:
        datasets: Explicit list of dataset keys (e.g. ['ipl', 't20i']).
        profile: Named profile from config/datasets.yml.
        enabled_only: If True, ingest all datasets with enabled: true.
        recent: If True, use Cricsheet's recently_added_7 for delta.
        full_refresh: If True, drop and rebuild bronze tables.
        skip_people: If True, skip people.csv download.
    """
    if recent:
        datasets_to_ingest = ["recent_7"]
    elif datasets:
        datasets_to_ingest = datasets
    elif enabled_only:
        datasets_to_ingest = get_enabled_datasets()
    elif profile:
        datasets_to_ingest = get_profile_datasets(profile)
    else:
        datasets_to_ingest = get_default_datasets()

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


def _print_listing() -> None:
    """Print available datasets and profiles."""
    config = datasets_config

    print("Available datasets:")
    for key, ds in sorted(config.get("datasets", {}).items()):
        status = "✓" if ds.get("enabled") else "·"
        print(f"  {status} {key:16s}  {ds['name']}")

    print("\nDelta feeds:")
    for key, feed in sorted(config.get("delta_feeds", {}).items()):
        print(f"    {key:16s}  {feed['name']}")

    print("\nProfiles:")
    for name, prof in sorted(config.get("profiles", {}).items()):
        default = " (default)" if name == config.get("default_profile") else ""
        ds_list = ", ".join(prof["datasets"])
        print(f"  {name:16s}  {prof.get('description', '')}{default}")
        print(f"  {'':16s}  → [{ds_list}]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Cricsheet ingestion pipeline")
    parser.add_argument(
        "--dataset",
        nargs="+",
        help="Dataset(s) to ingest (e.g. ipl t20i bbl). Overrides profile.",
    )
    parser.add_argument(
        "--profile",
        help="Named profile from config/datasets.yml (e.g. minimal, standard, t20_all).",
    )
    parser.add_argument(
        "--enabled",
        action="store_true",
        help="Ingest all datasets with enabled: true in config/datasets.yml.",
    )
    parser.add_argument(
        "--recent",
        action="store_true",
        help="Delta mode: ingest recently added matches (last 7 days).",
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Drop and rebuild bronze tables from scratch.",
    )
    parser.add_argument(
        "--skip-people",
        action="store_true",
        help="Skip people.csv download.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_datasets",
        help="List available datasets, profiles, and exit.",
    )
    args = parser.parse_args()

    if args.list_datasets:
        _print_listing()
        return

    run_ingestion(
        datasets=args.dataset,
        profile=args.profile,
        enabled_only=args.enabled,
        recent=args.recent,
        full_refresh=args.full_refresh,
        skip_people=args.skip_people,
    )


if __name__ == "__main__":
    main()
