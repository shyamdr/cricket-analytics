"""Open-Meteo historical weather enrichment.

Fetches hourly + daily weather for each match using venue coordinates
and match date. Stores raw API response in bronze.weather.

API: https://archive-api.open-meteo.com/v1/archive
Cost: Free for non-commercial use, no API key required.
Rate limits (free tier): 600 calls/min, 5000/hour, 10000/day.
Resolution: Hourly (~25km ERA5 grid).
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from src.config import settings
from src.database import append_to_bronze, get_read_conn, get_write_conn

logger = structlog.get_logger(__name__)

_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Persistent HTTP client — reuses TLS session across calls, avoids
# repeated SSL handshakes that cause timeout failures.
_http_client = httpx.Client(timeout=15, http2=False)

# Hourly variables to fetch — all stored in bronze, subset surfaced in gold
_HOURLY_VARS = ",".join(
    [
        # Core cricket-relevant (surfaced in gold)
        "temperature_2m",
        "relative_humidity_2m",
        "dew_point_2m",
        "apparent_temperature",
        "wet_bulb_temperature_2m",
        "precipitation",
        "weather_code",
        "pressure_msl",
        "cloud_cover",
        "cloud_cover_low",
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",
        "is_day",
        # Bronze-only (stored for completeness)
        "rain",
        "surface_pressure",
        "cloud_cover_mid",
        "cloud_cover_high",
        "vapour_pressure_deficit",
        "soil_temperature_0_to_7cm",
        "soil_moisture_0_to_7cm",
        "sunshine_duration",
        "shortwave_radiation",
    ]
)

# Daily variables to fetch
_DAILY_VARS = ",".join(
    [
        "temperature_2m_max",
        "temperature_2m_min",
        "precipitation_sum",
        "precipitation_hours",
        "sunrise",
        "sunset",
        "wind_speed_10m_max",
        "wind_direction_10m_dominant",
        "weather_code",
        # Bronze-only
        "apparent_temperature_max",
        "apparent_temperature_min",
        "rain_sum",
        "sunshine_duration",
        "daylight_duration",
        "wind_gusts_10m_max",
        "shortwave_radiation_sum",
    ]
)


def _fetch_weather(
    latitude: float,
    longitude: float,
    date: str,
    timezone: str = "Asia/Kolkata",
    max_retries: int = 3,
) -> dict[str, Any]:
    """Fetch one day of hourly + daily weather from Open-Meteo.

    Retries on timeout/connection errors with exponential backoff.

    Args:
        latitude: Venue latitude.
        longitude: Venue longitude.
        date: Match date in YYYY-MM-DD format.
        timezone: IANA timezone for the venue (default: Asia/Kolkata for IPL).
        max_retries: Number of retry attempts on transient failures.

    Returns:
        Raw API response dict.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": date,
        "end_date": date,
        "hourly": _HOURLY_VARS,
        "daily": _DAILY_VARS,
        "timezone": timezone,
    }
    for attempt in range(max_retries + 1):
        try:
            resp = _http_client.get(_ARCHIVE_URL, params=params)
            resp.raise_for_status()
            return resp.json()
        except (httpx.TimeoutException, httpx.ConnectError, OSError) as exc:
            if attempt == max_retries:
                raise
            wait = min(attempt + 1, 3)
            logger.warning(
                "weather_retry",
                attempt=attempt + 1,
                max_retries=max_retries,
                wait=wait,
                error=str(exc),
            )
            time.sleep(wait)
    # unreachable but keeps type checker happy
    msg = "max retries exceeded"
    raise RuntimeError(msg)


def _get_already_fetched() -> set[str]:
    """Return match_ids already in bronze.weather."""
    try:
        conn = get_read_conn()
        rows = conn.execute(f"SELECT match_id FROM {settings.bronze_schema}.weather").fetchall()
        conn.close()
        return {r[0] for r in rows}
    except Exception:
        return set()


def _get_pending_matches(limit: int = 0) -> list[dict[str, Any]]:
    """Get matches that have venue coordinates but no weather data yet."""
    conn = get_read_conn()
    # Check if weather table exists yet
    try:
        conn.execute(f"SELECT 1 FROM {settings.bronze_schema}.weather LIMIT 0")
        weather_join = f"LEFT JOIN {settings.bronze_schema}.weather w ON m.match_id = w.match_id"
        weather_filter = "WHERE w.match_id IS NULL"
    except Exception:
        # Table doesn't exist yet — all matches are pending
        weather_join = ""
        weather_filter = "WHERE 1=1"

    sql = f"""
        SELECT
            m.match_id,
            m.date as match_date,
            vc.latitude,
            vc.longitude,
            COALESCE(em.venue_timezone, 'Asia/Kolkata') as timezone
        FROM {settings.bronze_schema}.matches m
        JOIN {settings.bronze_schema}.venue_coordinates vc
            ON m.venue = vc.venue
            AND (m.city = vc.city OR (m.city IS NULL AND vc.city IS NULL))
        LEFT JOIN {settings.bronze_schema}.espn_matches em
            ON m.match_id = em.cricsheet_match_id
        {weather_join}
        {weather_filter}
        ORDER BY m.date
    """
    if limit > 0:
        sql += f" LIMIT {limit}"
    rows = conn.execute(sql).fetchall()
    conn.close()
    return [
        {
            "match_id": r[0],
            "match_date": r[1],
            "latitude": r[2],
            "longitude": r[3],
            "timezone": r[4],
        }
        for r in rows
    ]


def fetch_weather_for_matches(
    limit: int = 0,
    run_id: str | None = None,
    delay_seconds: float = 0.1,
) -> dict[str, int]:
    """Fetch weather for all pending matches and load into bronze.weather.

    Delta-aware — skips matches already in bronze.weather.

    Args:
        limit: Max matches to process (0 = all pending). Use for testing.
        run_id: Optional run identifier for audit columns.
        delay_seconds: Pause between API calls (default 0.1s). Free tier
            allows 600/min — 0.1s gives ~600/min max, well within limits.

    Returns:
        Dict with counts: fetched, loaded, skipped, failed.
    """
    if run_id is None:
        import uuid

        run_id = str(uuid.uuid4())

    loaded_at = datetime.now(UTC).isoformat()
    pending = _get_pending_matches(limit=limit)

    logger.info("weather_enrichment_start", pending=len(pending), limit=limit)

    if not pending:
        logger.info("no_pending_matches")
        return {"fetched": 0, "loaded": 0, "skipped": 0, "failed": 0}

    records = []
    failed = 0
    loaded_total = 0
    batch_size = 50

    for i, match in enumerate(pending):
        match_id = match["match_id"]
        try:
            data = _fetch_weather(
                latitude=match["latitude"],
                longitude=match["longitude"],
                date=match["match_date"],
                timezone=match["timezone"] or "Asia/Kolkata",
            )

            record = {
                "match_id": match_id,
                "match_date": match["match_date"],
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "elevation": data.get("elevation"),
                "timezone": data.get("timezone"),
                "utc_offset_seconds": data.get("utc_offset_seconds"),
                # Store full hourly + daily as JSON for silver to parse
                "hourly_json": json.dumps(data.get("hourly", {})),
                "daily_json": json.dumps(data.get("daily", {})),
                "_loaded_at": loaded_at,
                "_run_id": run_id,
            }
            records.append(record)

            logger.info(
                "weather_fetched",
                match_id=match_id,
                date=match["match_date"],
                progress=f"{i + 1}/{len(pending)}",
            )

            if delay_seconds > 0:
                time.sleep(delay_seconds)

        except Exception as exc:
            failed += 1
            logger.warning(
                "weather_fetch_failed",
                match_id=match_id,
                date=match["match_date"],
                progress=f"{i + 1}/{len(pending)}",
                error=str(exc),
            )

        # Persist batch to DB so progress isn't lost on failure
        if len(records) >= batch_size:
            loaded_total += _persist_batch(records, loaded_at)
            records = []

    # Persist remaining records
    if records:
        loaded_total += _persist_batch(records, loaded_at)

    logger.info(
        "weather_enrichment_complete",
        fetched=loaded_total,
        loaded=loaded_total,
        failed=failed,
        total=len(pending),
    )
    return {"fetched": loaded_total, "loaded": loaded_total, "skipped": 0, "failed": failed}


def _persist_batch(records: list[dict[str, Any]], loaded_at: str) -> int:
    """Write a batch of weather records to bronze.weather."""
    import pyarrow as pa

    table = pa.Table.from_pylist(records)
    conn = get_write_conn()
    try:
        loaded = append_to_bronze(
            conn,
            f"{settings.bronze_schema}.weather",
            table,
            "match_id",
        )
    finally:
        conn.close()
    logger.info("weather_batch_persisted", batch_size=len(records), new_rows=loaded)
    return loaded
