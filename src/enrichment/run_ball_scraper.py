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
import logging

import duckdb

from src.config import settings
from src.database import get_read_conn
from src.enrichment.ball_data_scraper import scrape_ball_data
from src.enrichment.series_resolver import SeriesResolver

logger = logging.getLogger(__name__)


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
    """Get all matches for a season — including no-result (rain-abandoned).

    Rain-abandoned matches can still have partial or full innings of ball
    data on ESPN, so we don't exclude them.
    """
    close_after = conn is None
    if conn is None:
        conn = get_read_conn()
    rows = conn.execute(
        f"""SELECT match_id, match_date, season
           FROM {settings.gold_schema}.dim_matches
           WHERE season = ?
           ORDER BY match_date""",
        [season],
    ).fetchall()
    if close_after:
        conn.close()
    return [{"match_id": r[0], "match_date": str(r[1]), "season": r[2]} for r in rows]


def _get_all_matches(
    conn: duckdb.DuckDBPyConnection | None = None,
) -> list[dict[str, str]]:
    """Get all matches across all seasons."""
    close_after = conn is None
    if conn is None:
        conn = get_read_conn()
    rows = conn.execute(
        f"""SELECT match_id, match_date, season
           FROM {settings.gold_schema}.dim_matches
           ORDER BY match_date""",
    ).fetchall()
    if close_after:
        conn.close()
    return [{"match_id": r[0], "match_date": str(r[1]), "season": r[2]} for r in rows]


def _get_matches_by_ids(
    match_ids: list[str], conn: duckdb.DuckDBPyConnection | None = None
) -> list[dict[str, str]]:
    """Get specific matches by their Cricsheet match IDs."""
    close_after = conn is None
    if conn is None:
        conn = get_read_conn()
    placeholders = ",".join(["?"] * len(match_ids))
    rows = conn.execute(
        f"""SELECT match_id, match_date, season
           FROM {settings.gold_schema}.dim_matches
           WHERE match_id IN ({placeholders})
           ORDER BY match_date""",
        match_ids,
    ).fetchall()
    if close_after:
        conn.close()
    return [{"match_id": r[0], "match_date": str(r[1]), "season": r[2]} for r in rows]


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
    from src.database import get_write_conn

    conn = get_write_conn()
    try:
        conn.execute(
            f"""CREATE TABLE IF NOT EXISTS {settings.bronze_schema}.espn_ball_scrape_status (
                cricsheet_match_id VARCHAR PRIMARY KEY,
                espn_series_id INTEGER,
                status VARCHAR NOT NULL,
                scraped_at TIMESTAMP DEFAULT current_timestamp
            )"""
        )
    finally:
        conn.close()


def _record_scrape_status(match_id: str, series_id: int, status: str) -> None:
    """Insert or update a match's scrape status."""
    from src.database import get_write_conn

    conn = get_write_conn()
    try:
        conn.execute(
            f"""INSERT OR REPLACE INTO {settings.bronze_schema}.espn_ball_scrape_status
                (cricsheet_match_id, espn_series_id, status, scraped_at)
                VALUES (?, ?, ?, current_timestamp)""",
            [match_id, series_id, status],
        )
    finally:
        conn.close()


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
            all_matches = _get_matches_by_ids(match_ids, conn)
        elif all_seasons:
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

    logger.info(
        "Ball scraper: to_scrape=%d, already_done=%d, total=%d",
        len(pending),
        len(already_scraped),
        len(all_matches),
    )

    if dry_run or not pending:
        for m in pending:
            logger.info("  would scrape: match_id=%s, date=%s", m["match_id"], m["match_date"])
        return

    resolver = SeriesResolver()
    logger.info("Starting — %d matches, %.1fs delay between matches", len(pending), delay)

    total_loaded = 0
    batches_written = 0

    def persist_batch(batch: list[dict]) -> None:
        nonlocal total_loaded, batches_written
        loaded = _load_ball_records_to_bronze(batch)
        total_loaded += loaded
        batches_written += 1
        logger.info(
            "batch %d saved | balls_in_batch=%d | total_saved=%d",
            batches_written,
            loaded,
            total_loaded,
        )

    results = scrape_ball_data(
        pending,
        resolver=resolver,
        delay_seconds=delay,
        on_batch=persist_batch,
        on_status=_record_scrape_status,
    )
    logger.info("Done — balls_scraped=%d, saved_to_db=%d", len(results), total_loaded)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-5s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Route structlog through stdlib so everything has the same format.
    # Suppresses noisy structlog key=value output from series_resolver, database, etc.
    import structlog

    structlog.configure(
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
    )
    # Silence chatty modules — only show warnings and above
    logging.getLogger("src.enrichment.series_resolver").setLevel(logging.WARNING)
    logging.getLogger("src.database").setLevel(logging.WARNING)

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
