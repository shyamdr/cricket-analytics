"""Dynamic ESPN series_id resolver.

Discovers the ESPN series_id for any cricket match by probing ESPN
directly. No hardcoded seeds — everything is discovered and cached
in DuckDB for future runs.

Architecture:
- bronze.espn_series: one row per series (IPL 2024, BBL 2023, etc.)
  with series_id, name, season, format, competition metadata.
- Resolution: for any match without a known series_id, probe ONE match
  from that season on ESPN, extract series metadata from __NEXT_DATA__,
  store it, and apply to all matches in that season.

Discovery only happens once per series. After that, it's a DuckDB lookup.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import duckdb
import structlog
from playwright.async_api import async_playwright

from src.config import settings
from src.database import get_read_conn, get_write_conn
from src.utils import async_retry, run_async

logger = structlog.get_logger(__name__)


def _ensure_series_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create bronze.espn_series if it doesn't exist."""
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {settings.bronze_schema}")
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {settings.bronze_schema}.espn_series (
            series_id       BIGINT PRIMARY KEY,
            series_name     VARCHAR,
            season          VARCHAR,
            series_slug     VARCHAR,
            discovered_from VARCHAR,
            created_at      TIMESTAMP DEFAULT current_timestamp
        )
    """)


@async_retry(max_attempts=3, base_delay=5.0, exceptions=(Exception,))
async def _discover_series_from_match(match_id: str, browser: Any) -> dict[str, Any] | None:
    """Probe a single ESPN match page to discover its series metadata.

    ESPN's old-style URL /ci/engine/match/{match_id}.html redirects to the
    canonical match page. We extract full series info from __NEXT_DATA__.

    Works for any competition (IPL, ODIs, Tests, BBL, PSL, etc.) as long
    as the match_id exists on ESPN.

    Args:
        match_id: Cricsheet/ESPN match ID.
        browser: Playwright browser instance.

    Returns:
        Dict with series metadata, or None if discovery failed.
    """
    url = f"https://www.espncricinfo.com/ci/engine/match/{match_id}.html"

    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/16.0 Safari/605.1.15"
        ),
    )
    page = await context.new_page()

    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        if response and response.status == 404:
            logger.warning("espn_match_not_found", match_id=match_id)
            return None

        content = await page.content()
    finally:
        await context.close()

    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        content,
        re.DOTALL,
    )
    if not match:
        logger.warning("no_next_data_on_match_page", match_id=match_id)
        return None

    next_data = json.loads(match.group(1))

    try:
        app_data = next_data["props"]["appPageProps"]["data"]
        data = app_data.get("data", app_data)
        series = data["match"]["series"]
        season = data["match"].get("season", "")

        return {
            "series_id": int(series["objectId"]),
            "series_name": series.get("name", ""),
            "season": str(season),
            "series_slug": series.get("slug", ""),
            "discovered_from": str(match_id),
        }
    except (KeyError, TypeError, ValueError):
        logger.warning("could_not_extract_series_info", match_id=match_id)
        return None


class SeriesResolver:
    """Resolves ESPN series_id for Cricsheet match_ids.

    Resolution order:
    1. In-memory cache (loaded from bronze.espn_series on init)
    2. Dynamic discovery — probe one ESPN match page per unknown season,
       extract series metadata, persist to bronze.espn_series, apply to
       all matches in that season.

    Usage:
        resolver = SeriesResolver()
        # Bulk resolve with shared browser
        mapping = await resolver.resolve_batch_async(matches, browser)
        # Single match (synchronous)
        series_id = resolver.resolve(match_id="335982")
    """

    def __init__(self) -> None:
        # season (str) → series_id (int)
        self._season_cache: dict[str, int] = {}
        # match_id (str) → series_id (int) — for direct lookups
        self._match_cache: dict[str, int] = {}
        self._load_from_db()

    def _load_from_db(self) -> None:
        """Load previously discovered series from bronze.espn_series."""
        try:
            conn = get_read_conn()
            rows = conn.execute(
                f"SELECT series_id, season FROM {settings.bronze_schema}.espn_series"
            ).fetchall()
            for series_id, season in rows:
                self._season_cache[str(season)] = int(series_id)
            conn.close()
            logger.info("series_cache_loaded", count=len(rows))
        except duckdb.CatalogException:
            logger.info("no_series_table_yet")
        except Exception:
            logger.exception("failed_loading_series_cache")

    def get(self, match_id: str) -> int | None:
        """Look up series_id from match cache."""
        return self._match_cache.get(str(match_id))

    def get_by_season(self, season: str) -> int | None:
        """Look up series_id from season cache."""
        return self._season_cache.get(str(season))

    def resolve(self, match_id: str, season: str | None = None) -> int | None:
        """Resolve series_id for a single match (synchronous).

        Tries caches first. If not found, probes ESPN directly.
        """
        # Check match-level cache
        cached = self.get(match_id)
        if cached is not None:
            return cached

        # Check season-level cache
        if season:
            season_cached = self.get_by_season(season)
            if season_cached is not None:
                self._match_cache[str(match_id)] = season_cached
                return season_cached

        # Dynamic discovery
        series_info = run_async(self._discover_single(match_id))
        if series_info is not None:
            self._store_series(series_info)
            sid = series_info["series_id"]
            self._match_cache[str(match_id)] = sid
            return sid
        return None

    async def _discover_single(self, match_id: str) -> dict[str, Any] | None:
        """Launch a browser and discover series info for a single match."""
        async with async_playwright() as pw:
            browser = await pw.webkit.launch(headless=True)
            result = await _discover_series_from_match(match_id, browser)
            await browser.close()
        return result

    async def resolve_batch_async(
        self,
        matches: list[dict[str, str]],
        browser: Any,
        delay_seconds: float = 4.0,
    ) -> dict[str, int]:
        """Resolve series_ids for a batch of matches using a shared browser.

        Groups matches by season. For each season without a known series_id,
        probes ONE match on ESPN to discover the series. That single probe
        resolves the entire season.

        Args:
            matches: List of dicts with 'match_id', 'match_date', 'season'.
            browser: Playwright browser instance (caller manages lifecycle).
            delay_seconds: Delay between ESPN discovery requests.

        Returns:
            Dict of match_id → series_id for all resolved matches.
        """
        # Populate match cache from season cache for known seasons
        for m in matches:
            mid = str(m["match_id"])
            season = str(m.get("season", ""))
            if mid not in self._match_cache and season in self._season_cache:
                self._match_cache[mid] = self._season_cache[season]

        # Find seasons that still need discovery
        unknown_seasons: dict[str, list[dict[str, str]]] = {}
        for m in matches:
            mid = str(m["match_id"])
            season = str(m.get("season", ""))
            if mid not in self._match_cache:
                unknown_seasons.setdefault(season, []).append(m)

        if not unknown_seasons:
            logger.info("all_series_ids_cached", total=len(matches))
            return {str(m["match_id"]): self._match_cache[str(m["match_id"])] for m in matches}

        logger.info(
            "discovering_series",
            unknown_seasons=len(unknown_seasons),
            total_unresolved=sum(len(v) for v in unknown_seasons.values()),
        )

        # Probe one match per unknown season
        for i, (season, season_matches) in enumerate(sorted(unknown_seasons.items())):
            probe = season_matches[0]
            probe_id = str(probe["match_id"])

            logger.info(
                "probing_series",
                season=season,
                probe_match_id=probe_id,
                progress=f"{i + 1}/{len(unknown_seasons)}",
            )

            try:
                series_info = await _discover_series_from_match(probe_id, browser)
            except Exception:
                logger.exception("discovery_failed", match_id=probe_id, season=season)
                series_info = None

            if series_info is not None:
                self._store_series(series_info)
                sid = series_info["series_id"]

                # Apply to all matches in this season
                for m in season_matches:
                    self._match_cache[str(m["match_id"])] = sid

                logger.info(
                    "season_resolved",
                    season=season,
                    series_id=sid,
                    series_name=series_info["series_name"],
                    matches_mapped=len(season_matches),
                )
            else:
                logger.warning("season_discovery_failed", season=season)

            # Rate limit between probes
            if i < len(unknown_seasons) - 1:
                await asyncio.sleep(delay_seconds)

        # Build result
        result: dict[str, int] = {}
        for m in matches:
            mid = str(m["match_id"])
            sid = self._match_cache.get(mid)
            if sid is not None:
                result[mid] = sid

        still_missing = len(matches) - len(result)
        if still_missing > 0:
            logger.warning("some_series_ids_not_found", missing=still_missing)

        return result

    def _store_series(self, series_info: dict[str, Any]) -> None:
        """Persist a discovered series to bronze.espn_series and update caches."""
        sid = series_info["series_id"]
        season = str(series_info.get("season", ""))

        # Update in-memory caches
        self._season_cache[season] = sid

        # Persist to DuckDB
        try:
            conn = get_write_conn()
            _ensure_series_table(conn)

            # Upsert — don't fail on duplicate series_id
            existing = conn.execute(
                f"SELECT 1 FROM {settings.bronze_schema}.espn_series WHERE series_id = ?",
                [sid],
            ).fetchone()

            if existing is None:
                conn.execute(
                    f"""INSERT INTO {settings.bronze_schema}.espn_series
                        (series_id, series_name, season, series_slug, discovered_from)
                        VALUES (?, ?, ?, ?, ?)""",
                    [
                        sid,
                        series_info.get("series_name", ""),
                        season,
                        series_info.get("series_slug", ""),
                        series_info.get("discovered_from", ""),
                    ],
                )
                logger.info(
                    "series_persisted",
                    series_id=sid,
                    series_name=series_info.get("series_name"),
                    season=season,
                )

            conn.close()
        except Exception:
            logger.exception("failed_persisting_series")

    @property
    def cache_size(self) -> int:
        """Number of seasons with known series_ids."""
        return len(self._season_cache)
