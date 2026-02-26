"""ESPN enrichment asset — scrapes match metadata from ESPNcricinfo.

Runs after bronze ingestion + dbt transformation (needs dim_matches).
Discovers series_ids dynamically, scrapes captain/keeper/roles/floodlit/
start_time, and loads into bronze.espn_matches.
"""

from dagster import AssetExecutionContext, Config, MaterializeResult, MetadataValue, asset

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
    deps=["bronze_matches"],
    description=(
        "Scrape ESPN match data (captain, keeper, player roles, floodlit, "
        "start time) and load into bronze.espn_matches. Delta-aware — "
        "skips already-scraped matches."
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
                "loaded": MetadataValue.int(0),
                "already_scraped": MetadataValue.int(len(already_scraped)),
            }
        )

    # Scrape
    resolver = SeriesResolver()
    context.log.info(f"Series resolver ready, {resolver.cache_size} seasons cached")

    results = scrape_matches(pending, resolver=resolver, delay_seconds=config.delay)
    loaded = load_espn_to_bronze(results)

    context.log.info(f"Enrichment complete: {len(results)} scraped, {loaded} loaded")

    return MaterializeResult(
        metadata={
            "scraped": MetadataValue.int(len(results)),
            "loaded": MetadataValue.int(loaded),
            "already_scraped": MetadataValue.int(len(already_scraped)),
            "total_matches": MetadataValue.int(len(all_matches)),
        }
    )
