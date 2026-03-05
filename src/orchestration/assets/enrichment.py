"""ESPN enrichment assets — scrapes match metadata and ball-by-ball data from ESPNcricinfo.

Two assets:
1. espn_enrichment — scorecard scraper (captains, keepers, player bios, venue details)
2. espn_ball_data — ball-by-ball spatial scraper (wagon wheel, pitch map, shot type, win prob)

Both run after bronze ingestion + dbt transformation (need dim_matches).
Ball data runs after scorecard enrichment (needs series IDs in bronze.espn_series).
"""

from dagster import AssetExecutionContext, AssetKey, Config, MaterializeResult, MetadataValue, asset

from src.enrichment.bronze_loader import load_espn_to_bronze
from src.enrichment.espn_client import scrape_matches
from src.enrichment.run import get_all_matches, get_already_scraped, get_matches_for_season
from src.enrichment.series_resolver import SeriesResolver


class EnrichmentConfig(Config):
    """Configuration for the espn_enrichment asset."""

    season: str = ""
    all_seasons: bool = False
    limit: int = 0
    delay: float = 4.0


@asset(
    group_name="enrichment",
    compute_kind="python",
    deps=[AssetKey(["gold", "dim_matches"])],
    description=(
        "Scrape ESPN match data (captain, keeper, player roles, floodlit, "
        "start time, venue details, player bios, per-ball spatial data) "
        "and load into bronze ESPN tables. Delta-aware — skips already-scraped matches."
    ),
)
def espn_enrichment(context: AssetExecutionContext, config: EnrichmentConfig) -> MaterializeResult:
    """Scrape ESPN data for matches not yet enriched."""
    # Get matches to process
    if config.all_seasons:
        all_matches = get_all_matches()
    elif config.season:
        all_matches = get_matches_for_season(config.season)
    else:
        # Default: all matches
        all_matches = get_all_matches()

    already_scraped = get_already_scraped()
    pending = [m for m in all_matches if m["match_id"] not in already_scraped]

    if config.limit > 0:
        pending = pending[: config.limit]

    context.log.info(
        f"Enrichment: {len(pending)} pending, {len(already_scraped)} already scraped, "
        f"{len(all_matches)} total matches"
    )

    if not pending:
        return MaterializeResult(
            metadata={
                "scraped": MetadataValue.int(0),
                "loaded_matches": MetadataValue.int(0),
                "already_scraped": MetadataValue.int(len(already_scraped)),
            }
        )

    # Scrape with batch persistence — writes to DuckDB every 25 matches
    # so progress isn't lost if the job fails midway
    resolver = SeriesResolver()
    context.log.info(f"Series resolver ready, {resolver.cache_size} seasons cached")

    total_counts: dict[str, int] = {"matches": 0, "players": 0, "innings": 0, "balls": 0}

    def persist_batch(batch: list[dict]) -> None:
        counts = load_espn_to_bronze(batch)
        for k, v in counts.items():
            total_counts[k] = total_counts.get(k, 0) + v
        context.log.info(
            f"Batch persisted: {counts['matches']} matches, "
            f"{counts['players']} players, {counts['balls']} balls "
            f"(totals: {total_counts})"
        )

    results = scrape_matches(
        pending,
        resolver=resolver,
        delay_seconds=config.delay,
        on_batch=persist_batch,
    )

    context.log.info(
        f"Enrichment complete: {len(results)} scraped, "
        f"{total_counts['matches']} matches, {total_counts['players']} players, "
        f"{total_counts['balls']} balls loaded"
    )

    return MaterializeResult(
        metadata={
            "scraped": MetadataValue.int(len(results)),
            "loaded_matches": MetadataValue.int(total_counts["matches"]),
            "loaded_players": MetadataValue.int(total_counts["players"]),
            "loaded_innings": MetadataValue.int(total_counts["innings"]),
            "loaded_balls": MetadataValue.int(total_counts["balls"]),
            "already_scraped": MetadataValue.int(len(already_scraped)),
            "total_matches": MetadataValue.int(len(all_matches)),
        }
    )


class BallDataConfig(Config):
    """Configuration for the espn_ball_data asset."""

    season: str = ""
    all_seasons: bool = False
    limit: int = 0
    delay: float = 4.0


@asset(
    group_name="enrichment",
    compute_kind="python",
    deps=[AssetKey("espn_enrichment"), AssetKey(["gold", "dim_matches"])],
    description=(
        "Scrape ESPN ball-by-ball spatial data (wagon wheel, pitch map, shot type, "
        "shot control, win probability) from commentary pages. Delta-aware — "
        "skips already-scraped matches. Persists every 10 matches."
    ),
)
def espn_ball_data(context: AssetExecutionContext, config: BallDataConfig) -> MaterializeResult:
    """Scrape ESPN ball-by-ball data for matches not yet scraped."""
    from src.enrichment.ball_data_scraper import scrape_ball_data
    from src.enrichment.run_ball_scraper import (
        _ensure_status_table,
        _get_all_matches,
        _get_already_scraped_match_ids,
        _get_matches_for_season,
        _load_ball_records_to_bronze,
        _record_scrape_status,
    )

    _ensure_status_table()

    if config.all_seasons:
        all_matches = _get_all_matches()
    elif config.season:
        all_matches = _get_matches_for_season(config.season)
    else:
        all_matches = _get_all_matches()

    already_scraped = _get_already_scraped_match_ids()
    pending = [m for m in all_matches if m["match_id"] not in already_scraped]

    if config.limit > 0:
        pending = pending[: config.limit]

    context.log.info(
        f"Ball data: {len(pending)} pending, {len(already_scraped)} already scraped, "
        f"{len(all_matches)} total matches"
    )

    if not pending:
        return MaterializeResult(
            metadata={
                "scraped_matches": MetadataValue.int(0),
                "loaded_balls": MetadataValue.int(0),
                "already_scraped": MetadataValue.int(len(already_scraped)),
            }
        )

    resolver = SeriesResolver()
    total_loaded = 0
    batches_written = 0

    def persist_batch(batch: list[dict]) -> None:
        nonlocal total_loaded, batches_written
        loaded = _load_ball_records_to_bronze(batch)
        total_loaded += loaded
        batches_written += 1
        context.log.info(f"Batch {batches_written}: {loaded} balls saved (total: {total_loaded})")

    results = scrape_ball_data(
        pending,
        resolver=resolver,
        delay_seconds=config.delay,
        on_batch=persist_batch,
        on_status=_record_scrape_status,
        batch_size=10,
    )

    context.log.info(f"Ball data complete: {len(results)} balls from {len(pending)} matches")

    return MaterializeResult(
        metadata={
            "scraped_balls": MetadataValue.int(len(results)),
            "loaded_balls": MetadataValue.int(total_loaded),
            "batches_written": MetadataValue.int(batches_written),
            "already_scraped": MetadataValue.int(len(already_scraped)),
            "total_matches": MetadataValue.int(len(all_matches)),
        }
    )
