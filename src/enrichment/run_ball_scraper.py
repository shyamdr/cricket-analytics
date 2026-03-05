"""CLI entry point for ESPN ball-by-ball data scraping.

Usage:
    # Scrape a few matches for testing
    python -m src.enrichment.run_ball_scraper --season 2024 --limit 3

    # Scrape all matches for a season
    python -m src.enrichment.run_ball_scraper --season 2024

    # Scrape all seasons (full historical run — ~20 hours)
    python -m src.enrichment.run_ball_scraper --all

    # Show what would be scraped (dry run)
    python -m src.enrichment.run_ball_scraper --season 2024 --dry-run
"""

from __future__ import annotations

import argparse

import duckdb
import structlog

from src.config import settings
from src.database import get_read_conn
from src.enrichment.ball_data_scraper import scrape_ball_data
from src.enrichment.series_resolver import SeriesResolver

logger = structlog.get_logger(__name__)


def _load_ball_records_to_bronze(records: list[dict]) -> int:
    """Load flat ball records from the commentary scraper into bronze.espn_ball_data."""
    if not records:
        return 0
    import pyarrow as pa

    from src.database import append_to_bronze, get_write_conn

    conn = get_write_conn()
    try:
        table = pa.Table.from_pylist(records)
        return append_to_bronze(
            conn, f"{settings.bronze_schema}.espn_ball_data", table, "espn_ball_id"
        )
    finally:
        conn.close()


def _get_matches_for_season(
    season: str, conn: duckdb.DuckDBPyConnection | None = None
) -> list[dict[str, str]]:
    """Query DuckDB for all completed matches in a given season.

    Excludes 'no result' matches — they have no ball data to scrape.
    """
    close_after = conn is None
    if conn is None:
        conn = get_read_conn()
    rows = conn.execute(
        f"""SELECT match_id, match_date, season
           FROM {settings.gold_schema}.dim_matches
           WHERE season = ?
             AND (outcome_result IS NULL OR outcome_result != 'no result')
           ORDER BY match_date""",
        [season],
    ).fetchall()
    if close_after:
        conn.close()
    return [{"match_id": r[0], "match_date": str(r[1]), "season": r[2]} for r in rows]


def _get_all_matches(
    conn: duckdb.DuckDBPyConnection | None = None,
) -> list[dict[str, str]]:
    """Query DuckDB for all completed matches across all seasons.

    Excludes 'no result' matches — they have no ball data to scrape.
    """
    close_after = conn is None
    if conn is None:
        conn = get_read_conn()
    rows = conn.execute(
        f"""SELECT match_id, match_date, season
           FROM {settings.gold_schema}.dim_matches
           WHERE outcome_result IS NULL OR outcome_result != 'no result'
           ORDER BY match_date""",
    ).fetchall()
    if close_after:
        conn.close()
    return [{"match_id": r[0], "match_date": str(r[1]), "season": r[2]} for r in rows]


def _get_already_scraped_match_ids(
    conn: duckdb.DuckDBPyConnection | None = None,
) -> set[str]:
    """Get match IDs that already have ball data in bronze.espn_ball_data."""
    close_after = conn is None
    if conn is None:
        conn = get_read_conn()
    try:
        rows = conn.execute(
            f"SELECT DISTINCT cricsheet_match_id FROM {settings.bronze_schema}.espn_ball_data"
        ).fetchall()
        result = {r[0] for r in rows}
    except duckdb.CatalogException:
        result = set()
    if close_after:
        conn.close()
    return result


def run_ball_scraper(
    season: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    all_seasons: bool = False,
    delay: float = 4.0,
) -> None:
    """Run the ESPN ball-by-ball scraping pipeline."""
    conn = get_read_conn()
    try:
        if all_seasons:
            all_matches = _get_all_matches(conn)
        elif season:
            all_matches = _get_matches_for_season(season, conn)
        else:
            conn.close()
            return

        already_scraped = _get_already_scraped_match_ids(conn)
    finally:
        conn.close()

    pending = [m for m in all_matches if m["match_id"] not in already_scraped]

    if limit:
        pending = pending[:limit]

    # Log plan by season
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
            "ball_scraper_plan",
            season=s,
            total_matches=total,
            already_scraped=done,
            to_scrape=total - done,
        )

    logger.info(
        "ball_scraper_summary",
        total_pending=len(pending),
        total_matches=len(all_matches),
        already_scraped=len(already_scraped),
    )

    if dry_run or not pending:
        return

    resolver = SeriesResolver()
    logger.info("series_resolver_ready", cache_size=resolver.cache_size)

    total_loaded = 0

    def persist_batch(batch: list[dict]) -> None:
        nonlocal total_loaded
        loaded = _load_ball_records_to_bronze(batch)
        total_loaded += loaded
        logger.info("ball_batch_persisted", loaded=loaded, total_loaded=total_loaded)

    results = scrape_ball_data(
        pending,
        resolver=resolver,
        delay_seconds=delay,
        on_batch=persist_batch,
    )
    logger.info(
        "ball_scraper_complete",
        total_balls=len(results),
        total_loaded=total_loaded,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="ESPN ball-by-ball data scraper")
    parser.add_argument("--season", type=str, help="Season to scrape (e.g. 2024)")
    parser.add_argument("--limit", type=int, help="Max matches to scrape")
    parser.add_argument("--all", action="store_true", help="Scrape all seasons")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without scraping")
    parser.add_argument("--delay", type=float, default=4.0, help="Seconds between matches")
    args = parser.parse_args()

    if not args.season and not args.all:
        parser.error("Specify --season or --all")

    run_ball_scraper(
        season=args.season,
        limit=args.limit,
        dry_run=args.dry_run,
        all_seasons=args.all,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()
