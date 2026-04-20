"""CLI entry point for ESPN match-level enrichment (scorecard scraper).

Usage:
    # Scrape a few matches for testing
    python -m src.enrichment.run_match_scraper --season 2024 --limit 3

    # Scrape all matches for a season
    python -m src.enrichment.run_match_scraper --season 2024

    # Scrape all seasons (full historical run)
    python -m src.enrichment.run_match_scraper --all

    # Show what would be scraped (dry run)
    python -m src.enrichment.run_match_scraper --season 2024 --dry-run
"""

from __future__ import annotations

import argparse

import duckdb
import structlog

from src.config import settings
from src.database import get_read_conn
from src.enrichment.bronze_loader import load_espn_to_bronze
from src.enrichment.match_scraper import scrape_matches
from src.enrichment.queries import get_all_matches, get_matches_for_season
from src.enrichment.series_resolver import SeriesResolver

logger = structlog.get_logger(__name__)


def get_already_scraped(conn: duckdb.DuckDBPyConnection | None = None) -> set[str]:
    """Get match IDs already in bronze.espn_matches."""
    close_after = conn is None
    if conn is None:
        conn = get_read_conn()
    try:
        rows = conn.execute(
            f"SELECT cricsheet_match_id FROM {settings.bronze_schema}.espn_matches"
        ).fetchall()
        result = {r[0] for r in rows}
    except duckdb.CatalogException:
        result = set()
    if close_after:
        conn.close()
    return result


def run_enrichment(
    season: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    all_seasons: bool = False,
    delay: float = 4.0,
    refresh: bool = False,
) -> None:
    """Run the ESPN enrichment pipeline.

    Args:
        season: Single season to scrape (e.g. '2024').
        limit: Max matches to scrape.
        dry_run: Show plan without scraping.
        all_seasons: Scrape all seasons.
        delay: Seconds between requests.
        refresh: If True, re-scrape matches already in bronze and replace
            their rows (use to backfill new columns on existing matches).
            Default False — skip matches already scraped.
    """
    # Single connection for all read queries
    conn = get_read_conn()
    try:
        # Get matches to process
        if all_seasons:
            all_matches = get_all_matches(conn)
        elif season:
            all_matches = get_matches_for_season(season, conn)
        else:
            conn.close()
            return

        already_scraped = get_already_scraped(conn)
    finally:
        conn.close()

    if refresh:
        pending = list(all_matches)
    else:
        pending = [m for m in all_matches if m["match_id"] not in already_scraped]

    if limit:
        pending = pending[:limit]

    # Group by season for logging
    by_season: dict[str, int] = {}
    for m in all_matches:
        by_season[m["season"]] = by_season.get(m["season"], 0) + 1

    scraped_by_season: dict[str, int] = {}
    for m in all_matches:
        if m["match_id"] in already_scraped:
            scraped_by_season[m["season"]] = scraped_by_season.get(m["season"], 0) + 1

    for s in sorted(by_season.keys()):
        total = by_season[s]
        done = scraped_by_season.get(s, 0)
        logger.info(
            "enrichment_plan",
            season=s,
            total_matches=total,
            already_scraped=done,
            to_scrape=total - done,
        )

    logger.info(
        "enrichment_summary",
        total_pending=len(pending),
        total_matches=len(all_matches),
        already_scraped=len(already_scraped),
    )

    if dry_run or not pending:
        return

    # Initialize resolver once — it loads the DB cache + IPL seed
    resolver = SeriesResolver()
    logger.info("series_resolver_ready", cache_size=resolver.cache_size)

    # Scrape with batch persistence — writes to DuckDB every 25 matches
    # so progress isn't lost if the job fails midway
    total_counts: dict[str, int] = {"matches": 0, "players": 0, "innings": 0, "balls": 0}

    def persist_batch(batch: list[dict]) -> None:
        counts = load_espn_to_bronze(batch, refresh=refresh)
        for k, v in counts.items():
            total_counts[k] = total_counts.get(k, 0) + v
        logger.info("batch_persisted", **total_counts)

    results = scrape_matches(
        pending,
        resolver=resolver,
        delay_seconds=delay,
        on_batch=persist_batch,
    )
    logger.info(
        "enrichment_complete",
        scraped=len(results),
        **total_counts,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="ESPN enrichment pipeline")
    parser.add_argument("--season", type=str, help="IPL season to scrape (e.g. 2024)")
    parser.add_argument("--limit", type=int, help="Max matches to scrape")
    parser.add_argument("--all", action="store_true", help="Scrape all seasons")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without scraping")
    parser.add_argument("--delay", type=float, default=4.0, help="Seconds between requests")
    args = parser.parse_args()

    if not args.season and not args.all:
        parser.error("Specify --season or --all")

    run_enrichment(
        season=args.season,
        limit=args.limit,
        dry_run=args.dry_run,
        all_seasons=args.all,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()
