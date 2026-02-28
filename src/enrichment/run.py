"""CLI entry point for ESPN enrichment pipeline.

Usage:
    # Scrape a few matches for testing
    python -m src.enrichment.run --season 2024 --limit 3

    # Scrape all matches for a season
    python -m src.enrichment.run --season 2024

    # Scrape all seasons (full historical run)
    python -m src.enrichment.run --all

    # Show what would be scraped (dry run)
    python -m src.enrichment.run --season 2024 --dry-run
"""

from __future__ import annotations

import argparse

import duckdb
import structlog

from src.config import settings
from src.database import get_read_conn
from src.enrichment.bronze_loader import load_espn_to_bronze
from src.enrichment.espn_client import scrape_matches
from src.enrichment.series_resolver import SeriesResolver

logger = structlog.get_logger(__name__)


def get_matches_for_season(season: str) -> list[dict[str, str]]:
    """Query DuckDB for all matches in a given season with dates."""
    conn = get_read_conn()
    rows = conn.execute(
        """SELECT match_id, match_date, season
           FROM main_gold.dim_matches
           WHERE season = ?
           ORDER BY match_date""",
        [season],
    ).fetchall()
    conn.close()
    return [{"match_id": r[0], "match_date": str(r[1]), "season": r[2]} for r in rows]


def get_all_matches() -> list[dict[str, str]]:
    """Query DuckDB for all matches across all seasons."""
    conn = get_read_conn()
    rows = conn.execute(
        """SELECT match_id, match_date, season
           FROM main_gold.dim_matches
           ORDER BY match_date""",
    ).fetchall()
    conn.close()
    return [{"match_id": r[0], "match_date": str(r[1]), "season": r[2]} for r in rows]


def get_already_scraped() -> set[str]:
    """Get match IDs already in bronze.espn_matches."""
    conn = get_read_conn()
    try:
        rows = conn.execute(
            f"SELECT cricsheet_match_id FROM {settings.bronze_schema}.espn_matches"
        ).fetchall()
        result = {r[0] for r in rows}
    except duckdb.CatalogException:
        result = set()
    conn.close()
    return result


def run_enrichment(
    season: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    all_seasons: bool = False,
    delay: float = 4.0,
) -> None:
    """Run the ESPN enrichment pipeline."""
    # Get matches to process
    if all_seasons:
        all_matches = get_all_matches()
    elif season:
        all_matches = get_matches_for_season(season)
    else:
        return

    already_scraped = get_already_scraped()
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

    # Scrape
    results = scrape_matches(pending, resolver=resolver, delay_seconds=delay)
    loaded = load_espn_to_bronze(results)
    logger.info(
        "enrichment_complete",
        scraped=len(results),
        loaded=loaded,
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
