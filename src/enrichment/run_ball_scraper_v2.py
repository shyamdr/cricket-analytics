"""CLI entry point for ESPN ball-by-ball data scraping (v2 — two-load approach).

Uses ball_data_scraper_v2 which loads each innings in a separate page session,
fixing the innings switch bug where v1 loses inning 1 data on ~5% of matches.

Usage:
    # Scrape specific matches by ID (for fixing partial data)
    python -m src.enrichment.run_ball_scraper_v2 --matches 1473443,1473467

    # Scrape a full season
    python -m src.enrichment.run_ball_scraper_v2 --season 2025

    # Dry run
    python -m src.enrichment.run_ball_scraper_v2 --season 2024 --dry-run

    # Limit matches
    python -m src.enrichment.run_ball_scraper_v2 --season 2024 --limit 5
"""

from __future__ import annotations

import argparse

import duckdb
import structlog

from src.config import settings
from src.database import get_read_conn
from src.enrichment.ball_data_scraper_v2 import scrape_ball_data_v2
from src.enrichment.series_resolver import SeriesResolver

logger = structlog.get_logger(__name__)


def _load_ball_records_to_bronze(records: list[dict]) -> int:
    """Load flat ball records into bronze.espn_ball_data."""
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
    """Get match IDs that already have ball data in bronze."""
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


def _delete_ball_data_for_matches(match_ids: list[str]) -> int:
    """Delete existing ball data for specific matches (for re-scraping)."""
    from src.database import get_write_conn

    conn = get_write_conn()
    try:
        placeholders = ",".join(["?"] * len(match_ids))
        (before,) = conn.execute(
            f"SELECT COUNT(*) FROM {settings.bronze_schema}.espn_ball_data "
            f"WHERE cricsheet_match_id IN ({placeholders})",
            match_ids,
        ).fetchone()
        conn.execute(
            f"DELETE FROM {settings.bronze_schema}.espn_ball_data "
            f"WHERE cricsheet_match_id IN ({placeholders})",
            match_ids,
        )
        return before
    finally:
        conn.close()


def run_ball_scraper_v2(
    season: str | None = None,
    match_ids: list[str] | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    delay: float = 4.0,
) -> None:
    """Run the v2 ball scraping pipeline."""
    conn = get_read_conn()
    try:
        if match_ids:
            all_matches = _get_matches_by_ids(match_ids, conn)
            # For explicit match IDs, delete existing data and re-scrape
            already_scraped = set()
        elif season:
            all_matches = _get_matches_for_season(season, conn)
            already_scraped = _get_already_scraped_match_ids(conn)
        else:
            conn.close()
            return
    finally:
        conn.close()

    pending = [m for m in all_matches if m["match_id"] not in already_scraped]

    if limit:
        pending = pending[:limit]

    logger.info(
        "ball_scraper_v2_plan",
        total_matches=len(all_matches),
        already_scraped=len(already_scraped),
        pending=len(pending),
    )

    if match_ids:
        # Delete existing data for explicit re-scrape targets
        ids_to_delete = [m["match_id"] for m in pending]
        if ids_to_delete and not dry_run:
            deleted = _delete_ball_data_for_matches(ids_to_delete)
            logger.info("deleted_existing_ball_data", rows=deleted, matches=ids_to_delete)

    if dry_run or not pending:
        for m in pending:
            logger.info("would_scrape", match_id=m["match_id"], date=m["match_date"])
        return

    resolver = SeriesResolver()
    logger.info("series_resolver_ready", cache_size=resolver.cache_size)

    total_loaded = 0

    def persist_batch(batch: list[dict]) -> None:
        nonlocal total_loaded
        loaded = _load_ball_records_to_bronze(batch)
        total_loaded += loaded
        logger.info("ball_batch_persisted", loaded=loaded, total_loaded=total_loaded)

    results = scrape_ball_data_v2(
        pending,
        resolver=resolver,
        delay_seconds=delay,
        on_batch=persist_batch,
    )
    logger.info(
        "ball_scraper_v2_complete",
        total_balls=len(results),
        total_loaded=total_loaded,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="ESPN ball-by-ball scraper v2")
    parser.add_argument("--season", type=str, help="Season to scrape (e.g. 2024)")
    parser.add_argument("--matches", type=str, help="Comma-separated match IDs to re-scrape")
    parser.add_argument("--limit", type=int, help="Max matches to scrape")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without scraping")
    parser.add_argument("--delay", type=float, default=4.0, help="Seconds between matches")
    args = parser.parse_args()

    if not args.season and not args.matches:
        parser.error("Specify --season or --matches")

    match_ids = args.matches.split(",") if args.matches else None

    run_ball_scraper_v2(
        season=args.season,
        match_ids=match_ids,
        limit=args.limit,
        dry_run=args.dry_run,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()
