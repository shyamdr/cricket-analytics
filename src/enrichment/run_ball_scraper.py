"""CLI entry point for ESPN ball-by-ball data scraping.

Usage:
    # Scrape a few matches for testing
    python -m src.enrichment.run_ball_scraper --season 2024 --limit 3

    # Scrape all matches for a season (skips already-scraped)
    python -m src.enrichment.run_ball_scraper --season 2024

    # Scrape specific matches (skips already-scraped)
    python -m src.enrichment.run_ball_scraper --matches 1473469,1473443

    # Scrape all seasons (full historical run)
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
from src.enrichment.ball_scraper import scrape_ball_data
from src.enrichment.queries import get_all_matches, get_matches_by_ids, get_matches_for_season
from src.enrichment.series_resolver import SeriesResolver

logger = structlog.get_logger(__name__)


def _load_ball_records_to_bronze(records: list[dict]) -> int:
    """Load flat ball records from the commentary scraper into bronze.espn_ball_data."""
    if not records:
        return 0
    import pyarrow as pa

    from src.database import append_to_bronze, write_conn

    with write_conn() as conn:
        table = pa.Table.from_pylist(records)
        return append_to_bronze(
            conn, f"{settings.bronze_schema}.espn_ball_data", table, "espn_ball_id"
        )


def _get_already_scraped_match_ids(
    conn: duckdb.DuckDBPyConnection | None = None,
) -> set[str]:
    """Get match IDs that have been scraped or marked as no_commentary."""
    close_after = conn is None
    if conn is None:
        conn = get_read_conn()
    try:
        # Check status table first (tracks success, no_commentary, failed)
        rows = conn.execute(
            f"SELECT cricsheet_match_id FROM {settings.bronze_schema}.espn_ball_scrape_status "
            f"WHERE status IN ('success', 'no_commentary')"
        ).fetchall()
        result = {r[0] for r in rows}
    except duckdb.CatalogException:
        # Table doesn't exist yet — fall back to ball data table
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


def _ensure_status_table() -> None:
    """Create the ball scrape status tracking table if it doesn't exist."""
    from src.database import write_conn

    with write_conn() as conn:
        conn.execute(
            f"""CREATE TABLE IF NOT EXISTS {settings.bronze_schema}.espn_ball_scrape_status (
                cricsheet_match_id VARCHAR PRIMARY KEY,
                espn_series_id INTEGER,
                status VARCHAR NOT NULL,
                scraped_at TIMESTAMP DEFAULT current_timestamp
            )"""
        )


def _record_scrape_status(match_id: str, series_id: int, status: str) -> None:
    """Insert or update a match's scrape status."""
    from src.database import write_conn

    with write_conn() as conn:
        conn.execute(
            f"""INSERT OR REPLACE INTO {settings.bronze_schema}.espn_ball_scrape_status
                (cricsheet_match_id, espn_series_id, status, scraped_at)
                VALUES (?, ?, ?, current_timestamp)""",
            [match_id, series_id, status],
        )


def run_ball_scraper(
    season: str | None = None,
    match_ids: list[str] | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    all_seasons: bool = False,
    delay: float = 4.0,
) -> None:
    """Run the ESPN ball-by-ball scraping pipeline."""
    _ensure_status_table()

    conn = get_read_conn()
    try:
        if match_ids:
            all_matches = get_matches_by_ids(match_ids, conn)
        elif all_seasons:
            all_matches = get_all_matches(conn)
        elif season:
            all_matches = get_matches_for_season(season, conn)
        else:
            conn.close()
            return
        already_scraped = _get_already_scraped_match_ids(conn)
    finally:
        conn.close()

    pending = [m for m in all_matches if m["match_id"] not in already_scraped]

    if limit:
        pending = pending[:limit]

    logger.info(
        "ball_scraper_plan",
        to_scrape=len(pending),
        already_done=len(already_scraped),
        total=len(all_matches),
    )

    if dry_run or not pending:
        for m in pending:
            logger.info("would_scrape", match_id=m["match_id"], date=m["match_date"])
        return

    resolver = SeriesResolver()
    logger.info("ball_scraper_starting", matches=len(pending), delay=delay)

    total_loaded = 0
    batches_written = 0

    def persist_batch(batch: list[dict]) -> None:
        nonlocal total_loaded, batches_written
        loaded = _load_ball_records_to_bronze(batch)
        total_loaded += loaded
        batches_written += 1
        logger.info(
            "batch_saved",
            batch=batches_written,
            balls_in_batch=loaded,
            total_saved=total_loaded,
        )

    results = scrape_ball_data(
        pending,
        resolver=resolver,
        delay_seconds=delay,
        on_batch=persist_batch,
        on_status=_record_scrape_status,
    )
    logger.info("ball_scraper_complete", balls_scraped=len(results), saved_to_db=total_loaded)


def main() -> None:
    parser = argparse.ArgumentParser(description="ESPN ball-by-ball data scraper")
    parser.add_argument("--season", type=str, help="Season to scrape (e.g. 2024)")
    parser.add_argument("--matches", type=str, help="Comma-separated match IDs to re-scrape")
    parser.add_argument("--limit", type=int, help="Max matches to scrape")
    parser.add_argument("--all", action="store_true", help="Scrape all seasons")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without scraping")
    parser.add_argument("--delay", type=float, default=4.0, help="Seconds between matches")
    args = parser.parse_args()

    if not args.season and not args.all and not args.matches:
        parser.error("Specify --season, --matches, or --all")

    match_ids = args.matches.split(",") if args.matches else None

    run_ball_scraper(
        season=args.season,
        match_ids=match_ids,
        limit=args.limit,
        dry_run=args.dry_run,
        all_seasons=args.all,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()
