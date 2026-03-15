"""Enrichment Dagster assets — ESPN scrapers and venue geocoding.

Assets:
1. espn_match_enrichment — scorecard scraper (captains, keepers, player bios, venue details)
2. espn_ball_enrichment — ball-by-ball spatial scraper (wagon wheel, pitch map, shot type, win prob)
3. venue_coordinates — Google Maps geocoding for venue lat/lng

ESPN assets run after bronze ingestion + dbt transformation (need dim_matches).
Ball data runs after match enrichment (needs series IDs in bronze.espn_series).
Venue coordinates run after dbt (need dim_venues), independent of ESPN.
"""

from dagster import AssetExecutionContext, AssetKey, Config, MaterializeResult, MetadataValue, asset

from src.enrichment.bronze_loader import load_espn_to_bronze
from src.enrichment.match_scraper import scrape_matches
from src.enrichment.run_match_scraper import (
    get_all_matches,
    get_already_scraped,
    get_matches_for_season,
)
from src.enrichment.series_resolver import SeriesResolver


class MatchEnrichmentConfig(Config):
    """Configuration for the espn_match_enrichment asset."""

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
def espn_match_enrichment(
    context: AssetExecutionContext, config: MatchEnrichmentConfig
) -> MaterializeResult:
    """Scrape ESPN scorecard data for matches not yet enriched."""
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


class BallEnrichmentConfig(Config):
    """Configuration for the espn_ball_enrichment asset."""

    season: str = ""
    all_seasons: bool = False
    limit: int = 0
    delay: float = 4.0


@asset(
    group_name="enrichment",
    compute_kind="python",
    deps=[AssetKey("espn_match_enrichment"), AssetKey(["gold", "dim_matches"])],
    description=(
        "Scrape ESPN ball-by-ball spatial data (wagon wheel, pitch map, shot type, "
        "shot control, win probability) from commentary pages. Delta-aware — "
        "skips already-scraped matches. Persists every 10 matches."
    ),
)
def espn_ball_enrichment(
    context: AssetExecutionContext, config: BallEnrichmentConfig
) -> MaterializeResult:
    """Scrape ESPN ball-by-ball data for matches not yet scraped."""
    from src.enrichment.ball_scraper import scrape_ball_data
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
    scrape_count = 0

    def persist_batch(batch: list[dict]) -> None:
        nonlocal total_loaded, batches_written
        loaded = _load_ball_records_to_bronze(batch)
        total_loaded += loaded
        batches_written += 1
        context.log.info(f"Batch {batches_written}: {loaded} balls saved (total: {total_loaded})")

    def track_status(
        match_id: str, series_id: int, status: str, details: dict | None = None
    ) -> None:
        nonlocal scrape_count
        scrape_count += 1
        details = details or {}
        date = details.get("date", "?")
        if status == "success":
            total_balls = details.get("total_balls", 0)
            innings = details.get("innings", {})
            inn_str = " + ".join(f"inn{k}={v}" for k, v in sorted(innings.items()))
            context.log.info(
                f"[{scrape_count}/{len(pending)}] match={match_id} | {date} | "
                f"total_balls={total_balls} | {inn_str}"
            )
        elif status == "no_commentary":
            context.log.info(
                f"[{scrape_count}/{len(pending)}] match={match_id} | {date} | no commentary (404)"
            )
        else:
            error = details.get("error", "unknown")
            context.log.warning(
                f"[{scrape_count}/{len(pending)}] match={match_id} | {date} | FAILED: {error}"
            )
        _record_scrape_status(match_id, series_id, status)

    results = scrape_ball_data(
        pending,
        resolver=resolver,
        delay_seconds=config.delay,
        on_batch=persist_batch,
        on_status=track_status,
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


@asset(
    group_name="enrichment",
    compute_kind="python",
    deps=[AssetKey(["bronze_matches"])],
    description=(
        "Geocode venue coordinates (lat/lng) via Google Maps Geocoding API. "
        "One API call per unique venue. Delta-aware — skips already-geocoded venues. "
        "Results stored in bronze.venue_coordinates."
    ),
)
def geocode_venue_coordinates(context: AssetExecutionContext) -> MaterializeResult:
    """Geocode all (venue, city) combos not yet in bronze.venue_coordinates.

    For each new venue:
    1. Geocode via Google Maps (two search patterns with fallback)
    2. Compare coordinates against existing venues using ~400m bounding box
    3. If within box of existing venue → alias (same ground, different name/city)
       → add to venue_name_mappings seed CSV, still store coordinates
    4. If outside all boxes → genuinely new venue → store coordinates
    """
    import csv
    from pathlib import Path

    import duckdb

    from src.config import settings
    from src.database import get_read_conn, get_write_conn
    from src.enrichment.geocoder import detect_alias, geocode_venues

    # Get all (venue, city) combos from bronze matches (not gold — avoids circular dep)
    conn = get_read_conn()
    try:
        all_venues = conn.execute(
            f"SELECT DISTINCT venue, city FROM {settings.bronze_schema}.matches "
            f"WHERE venue IS NOT NULL"
        ).fetchall()
        all_venue_dicts = [{"venue": r[0], "city": r[1]} for r in all_venues]

        # Get already-geocoded (venue, city) pairs + their coordinates
        try:
            already_rows = conn.execute(
                f"SELECT venue, city, latitude, longitude "
                f"FROM {settings.bronze_schema}.venue_coordinates"
            ).fetchall()
            already_set = {(r[0], r[1]) for r in already_rows}
            existing_venues = [
                {"venue": r[0], "city": r[1], "latitude": r[2], "longitude": r[3]}
                for r in already_rows
            ]
        except duckdb.CatalogException:
            already_set = set()
            existing_venues = []
    finally:
        conn.close()

    pending = [v for v in all_venue_dicts if (v["venue"], v["city"]) not in already_set]

    context.log.info(
        f"Geocoding: {len(pending)} pending, {len(already_set)} already done, "
        f"{len(all_venue_dicts)} total venue+city combos"
    )

    if not pending:
        return MaterializeResult(
            metadata={
                "geocoded": MetadataValue.int(0),
                "aliases_found": MetadataValue.int(0),
                "already_done": MetadataValue.int(len(already_set)),
                "total_venues": MetadataValue.int(len(all_venue_dicts)),
            }
        )

    results = geocode_venues(pending)

    # Load existing seed CSV mappings (if any)
    seed_path = Path(settings.project_root) / "src" / "dbt" / "seeds" / "venue_name_mappings.csv"
    existing_mappings: list[dict[str, str]] = []
    if seed_path.exists():
        with open(seed_path) as f:
            reader = csv.DictReader(f)
            existing_mappings = list(reader)

    # Track new aliases and new venues
    new_venues: list[dict] = []
    new_aliases: list[dict[str, str]] = []

    for r in results:
        if r["geocode_status"] != "ok" or r["latitude"] is None:
            # Failed geocode — store as-is so we don't retry every run
            new_venues.append(r)
            continue

        # Check bounding box against all existing venues
        match = detect_alias(r["venue"], r["city"], r["latitude"], r["longitude"], existing_venues)

        if match:
            # Alias detected — same ground, different name/city
            context.log.info(
                f"Alias: ({r['venue']}, {r['city']}) -> ({match['venue']}, {match['city']})"
            )
            new_aliases.append(
                {
                    "venue_name": r["venue"],
                    "city_name": r["city"],
                    "canonical_venue": match["venue"],
                    "canonical_city": match["city"],
                }
            )
        else:
            # Genuinely new venue — add to existing list so subsequent
            # items in this batch can detect aliases against it
            existing_venues.append(
                {
                    "venue": r["venue"],
                    "city": r["city"],
                    "latitude": r["latitude"],
                    "longitude": r["longitude"],
                }
            )

        # Always store coordinates (alias or not) so we don't re-geocode
        new_venues.append(r)

    # Write all geocoded results to bronze
    wconn = get_write_conn()
    try:
        wconn.execute(f"""
            CREATE TABLE IF NOT EXISTS {settings.bronze_schema}.venue_coordinates (
                venue VARCHAR NOT NULL,
                city VARCHAR,
                latitude DOUBLE,
                longitude DOUBLE,
                formatted_address VARCHAR,
                place_id VARCHAR,
                geocode_status VARCHAR
            )
        """)
        for r in new_venues:
            # Upsert: delete existing row for this (venue, city) combo, then insert
            if r["city"] is None:
                wconn.execute(
                    f"DELETE FROM {settings.bronze_schema}.venue_coordinates "
                    f"WHERE venue = ? AND city IS NULL",
                    [r["venue"]],
                )
            else:
                wconn.execute(
                    f"DELETE FROM {settings.bronze_schema}.venue_coordinates "
                    f"WHERE venue = ? AND city = ?",
                    [r["venue"], r["city"]],
                )
            wconn.execute(
                f"""INSERT INTO {settings.bronze_schema}.venue_coordinates
                    (venue, city, latitude, longitude, formatted_address, place_id,
                     geocode_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    r["venue"],
                    r["city"],
                    r["latitude"],
                    r["longitude"],
                    r["formatted_address"],
                    r["place_id"],
                    r["geocode_status"],
                ],
            )
    finally:
        wconn.close()

    # Write venue_name_mappings seed CSV if new aliases found
    if new_aliases:
        all_mappings = existing_mappings + new_aliases
        with open(seed_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "venue_name",
                    "city_name",
                    "canonical_venue",
                    "canonical_city",
                ],
            )
            writer.writeheader()
            writer.writerows(all_mappings)
        context.log.info(
            f"Updated venue_name_mappings.csv: {len(new_aliases)} new aliases, "
            f"{len(all_mappings)} total"
        )

    ok_count = sum(1 for r in results if r["geocode_status"] == "ok")
    context.log.info(
        f"Geocoding complete: {ok_count}/{len(results)} resolved, "
        f"{len(new_aliases)} aliases detected"
    )

    return MaterializeResult(
        metadata={
            "geocoded": MetadataValue.int(ok_count),
            "failed": MetadataValue.int(len(results) - ok_count),
            "aliases_found": MetadataValue.int(len(new_aliases)),
            "already_done": MetadataValue.int(len(already_set)),
            "total_venues": MetadataValue.int(len(all_venue_dicts)),
        }
    )
