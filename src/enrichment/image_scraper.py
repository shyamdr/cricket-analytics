"""Standalone ESPN image enrichment scraper.

Scrapes player profile pages, team pages, and venue data from ESPN Cricinfo
to extract image URLs (headshots, logos, venue photos). Writes to
bronze.espn_images — a single lookup table keyed by (entity_type, entity_id).

Player images come from individual player profile pages (__NEXT_DATA__).
Team logos and venue images come from series/match pages (__NEXT_DATA__).

Usage:
    python -m src.enrichment.image_scraper --players
    python -m src.enrichment.image_scraper --teams
    python -m src.enrichment.image_scraper --all
    python -m src.enrichment.image_scraper --all --limit 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from typing import Any

import pyarrow as pa
import structlog
from playwright.async_api import async_playwright

from src.config import settings
from src.database import append_to_bronze, get_read_conn
from src.utils import run_async

logger = structlog.get_logger(__name__)

# ESPN Cricinfo CDN base — prepend to CMS paths at display time
ESPN_CDN_BASE = "https://img1.hscicdn.com/image/upload/f_auto"

# ---------------------------------------------------------------------------
# Bronze table DDL
# ---------------------------------------------------------------------------

_ESPN_IMAGES_DDL = """
CREATE TABLE IF NOT EXISTS {schema}.espn_images (
    entity_type     VARCHAR NOT NULL,
    entity_id       VARCHAR NOT NULL,
    entity_name     VARCHAR,
    image_url       VARCHAR,
    headshot_url    VARCHAR
)
"""


def _ensure_images_table(conn: Any) -> None:
    """Create bronze.espn_images if it doesn't exist."""
    conn.execute(_ESPN_IMAGES_DDL.format(schema=settings.bronze_schema))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _fetch_next_data(url: str, browser: Any) -> dict[str, Any] | None:
    """Fetch a page and extract __NEXT_DATA__ JSON."""
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/16.0 Safari/605.1.15"
        ),
    )
    page = await context.new_page()
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        if response and response.status == 404:
            return None
        await page.wait_for_timeout(2000)
        content = await page.content()
    finally:
        await context.close()

    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        content,
        re.DOTALL,
    )
    if not match:
        return None
    return json.loads(match.group(1))


def _get_already_scraped(entity_type: str) -> set[str]:
    """Get entity IDs already in bronze.espn_images for a given type."""
    conn = get_read_conn()
    try:
        rows = conn.execute(
            f"SELECT entity_id FROM {settings.bronze_schema}.espn_images WHERE entity_type = ?",
            [entity_type],
        ).fetchall()
        return {r[0] for r in rows}
    except Exception:
        return set()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Player image scraping
# ---------------------------------------------------------------------------


def _get_players_to_scrape() -> list[dict[str, str]]:
    """Get players needing image scraping — all from people.csv with key_cricinfo."""
    already = _get_already_scraped("player")
    conn = get_read_conn()
    try:
        rows = conn.execute(
            f"SELECT identifier, name, key_cricinfo FROM {settings.bronze_schema}.people "
            "WHERE key_cricinfo IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()

    pending = []
    for identifier, name, key_cricinfo in rows:
        if str(key_cricinfo) not in already:
            pending.append(
                {
                    "player_id": identifier,
                    "player_name": name,
                    "key_cricinfo": str(key_cricinfo),
                }
            )
    return pending


async def _scrape_player_images(
    players: list[dict[str, str]],
    delay_seconds: float = 2.0,
    on_batch: Any = None,
    batch_size: int = 50,
) -> list[dict[str, str]]:
    """Scrape player profile pages for image URLs."""
    results: list[dict[str, str]] = []
    batch: list[dict[str, str]] = []

    async with async_playwright() as p:
        browser = await p.webkit.launch(headless=True)

        for i, player in enumerate(players):
            key = player["key_cricinfo"]
            name = player["player_name"]
            url = f"https://www.espncricinfo.com/cricketers/player-{key}"

            try:
                nd = await _fetch_next_data(url, browser)
                if not nd:
                    logger.warning("no_next_data", player=name, url=url)
                    continue

                player_data = (
                    nd.get("props", {}).get("appPageProps", {}).get("data", {}).get("player", {})
                )

                image_url = player_data.get("imageUrl")
                headshot_url = player_data.get("headshotImageUrl")

                if image_url or headshot_url:
                    record = {
                        "entity_type": "player",
                        "entity_id": key,
                        "entity_name": name,
                        "image_url": image_url,
                        "headshot_url": headshot_url,
                    }
                    results.append(record)
                    batch.append(record)
                    logger.info(
                        "player_image_found",
                        player=name,
                        has_headshot=headshot_url is not None,
                        progress=f"{i + 1}/{len(players)}",
                    )
                else:
                    logger.info("player_no_image", player=name, progress=f"{i + 1}/{len(players)}")

            except Exception as e:
                logger.error("player_scrape_error", player=name, error=str(e))

            # Persist batch
            if len(batch) >= batch_size and on_batch:
                on_batch(batch)
                batch = []

            # Rate limit
            if i < len(players) - 1:
                await asyncio.sleep(delay_seconds)

        await browser.close()

    # Final batch
    if batch and on_batch:
        on_batch(batch)

    return results


# ---------------------------------------------------------------------------
# Team + venue image scraping (from a single series page)
# ---------------------------------------------------------------------------


async def _scrape_team_and_venue_images(browser: Any) -> list[dict[str, str]]:
    """Extract team logos and venue images from an IPL series page.

    One page gives us all current team logos + venue images for matches
    in that series. We also grab the globalDetails for international teams.
    """
    results: list[dict[str, str]] = []
    seen: set[str] = set()

    # Scrape a recent IPL series page for franchise logos + venue images
    series_url = "https://www.espncricinfo.com/series/indian-premier-league-2025-1449924"
    nd = await _fetch_next_data(series_url, browser)

    if nd:
        app = nd.get("props", {}).get("appPageProps", {}).get("data", {})

        # Extract team and venue images from match fixtures
        def extract_entities(obj: Any, depth: int = 0) -> None:
            if depth > 5:
                return
            if isinstance(obj, dict):
                has_image = isinstance(obj.get("image"), dict) and obj["image"].get("url")
                has_name = obj.get("longName") or obj.get("name")
                has_id = obj.get("objectId")

                if has_image and has_name and has_id:
                    name = obj.get("longName") or obj.get("name")
                    oid = str(obj["objectId"])
                    img_url = obj["image"]["url"]
                    key = f"{oid}|{img_url}"

                    if key not in seen:
                        seen.add(key)
                        # Determine entity type from context
                        is_venue = obj.get("capacity") is not None or obj.get("town") is not None
                        entity_type = "venue" if is_venue else "team"
                        results.append(
                            {
                                "entity_type": entity_type,
                                "entity_id": oid,
                                "entity_name": name,
                                "image_url": img_url,
                                "headshot_url": None,
                            }
                        )
                    return

                for v in obj.values():
                    extract_entities(v, depth + 1)
            elif isinstance(obj, list):
                for item in obj[:50]:
                    extract_entities(item, depth + 1)

        extract_entities(app)

        # Also grab international team logos from globalDetails
        gd = nd.get("props", {}).get("globalDetails", {})
        for category in ["testTeams", "odiTeams", "otherTeams", "t20Teams"]:
            for team in gd.get(category, []):
                img = team.get("image")
                if img and img.get("url") and team.get("objectId"):
                    oid = str(team["objectId"])
                    key = f"{oid}|{img['url']}"
                    if key not in seen:
                        seen.add(key)
                        results.append(
                            {
                                "entity_type": "team",
                                "entity_id": oid,
                                "entity_name": team.get("longName") or team.get("name"),
                                "image_url": img["url"],
                                "headshot_url": None,
                            }
                        )

    logger.info(
        "team_venue_images_extracted",
        teams=sum(1 for r in results if r["entity_type"] == "team"),
        venues=sum(1 for r in results if r["entity_type"] == "venue"),
    )
    return results


# ---------------------------------------------------------------------------
# Bronze persistence
# ---------------------------------------------------------------------------


def _persist_to_bronze(records: list[dict[str, str]]) -> int:
    """Write image records to bronze.espn_images with dedup."""
    if not records:
        return 0
    import contextlib

    from src.database import write_conn

    with write_conn() as conn:
        _ensure_images_table(conn)
        # Dedup on composite key: entity_type + entity_id
        for rec in records:
            rec["_dedup_key"] = f"{rec['entity_type']}_{rec['entity_id']}"
        table = pa.Table.from_pylist(records)
        count = append_to_bronze(conn, f"{settings.bronze_schema}.espn_images", table, "_dedup_key")
        with contextlib.suppress(Exception):
            conn.execute(
                f"ALTER TABLE {settings.bronze_schema}.espn_images DROP COLUMN IF EXISTS _dedup_key"
            )
        return count


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scrape_images(
    players: bool = True,
    teams: bool = True,
    limit: int = 0,
    delay: float = 2.0,
) -> dict[str, int]:
    """Run the image enrichment scraper.

    Args:
        players: Scrape player profile pages for headshots.
        teams: Scrape series page for team logos + venue images.
        limit: Max players to scrape (0 = all pending).
        delay: Seconds between player page requests.

    Returns:
        Dict with counts per entity type.
    """
    counts: dict[str, int] = {"players": 0, "teams": 0, "venues": 0}

    async def _run() -> None:
        # Teams + venues first (single page, fast)
        if teams:
            async with async_playwright() as p:
                browser = await p.webkit.launch(headless=True)
                tv_records = await _scrape_team_and_venue_images(browser)
                await browser.close()

            # Filter out already-scraped
            already_teams = _get_already_scraped("team")
            already_venues = _get_already_scraped("venue")
            new_records = [
                r
                for r in tv_records
                if (r["entity_type"] == "team" and r["entity_id"] not in already_teams)
                or (r["entity_type"] == "venue" and r["entity_id"] not in already_venues)
            ]
            if new_records:
                n = _persist_to_bronze(new_records)
                counts["teams"] = sum(1 for r in new_records if r["entity_type"] == "team")
                counts["venues"] = sum(1 for r in new_records if r["entity_type"] == "venue")
                logger.info("team_venue_images_persisted", new=n)

        # Players (many pages, slow)
        if players:
            pending = _get_players_to_scrape()
            if limit > 0:
                pending = pending[:limit]
            logger.info("player_images_pending", count=len(pending))

            if pending:
                results = await _scrape_player_images(
                    pending,
                    delay_seconds=delay,
                    on_batch=lambda batch: _persist_to_bronze(batch),
                )
                counts["players"] = len(results)

    run_async(_run())
    logger.info("image_enrichment_complete", **counts)
    return counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="ESPN image enrichment scraper")
    parser.add_argument("--players", action="store_true", help="Scrape player headshots")
    parser.add_argument("--teams", action="store_true", help="Scrape team logos + venue images")
    parser.add_argument("--all", action="store_true", help="Scrape everything")
    parser.add_argument("--limit", type=int, default=0, help="Max players to scrape (0 = all)")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between requests")
    args = parser.parse_args()

    if not args.players and not args.teams and not args.all:
        parser.error("Specify --players, --teams, or --all")

    do_players = args.all or args.players
    do_teams = args.all or args.teams

    scrape_images(
        players=do_players,
        teams=do_teams,
        limit=args.limit,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()
