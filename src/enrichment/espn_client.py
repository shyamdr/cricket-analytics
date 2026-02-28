"""Thin wrapper around python-espncricinfo for ESPN data extraction.

Handles Playwright browser reuse, rate limiting, and data extraction
from the __NEXT_DATA__ JSON embedded in ESPN match pages.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import structlog
from playwright.async_api import async_playwright

from src.enrichment.series_resolver import SeriesResolver

logger = structlog.get_logger(__name__)

# Player role codes from ESPN teamPlayers data
ROLE_MAP: dict[str, str] = {
    "C": "captain",
    "WK": "wicketkeeper",
    "CWK": "captain_wicketkeeper",
    "P": "player",
}


async def _fetch_next_data(url: str, browser: Any) -> dict[str, Any]:
    """Fetch a page and extract __NEXT_DATA__ JSON using an existing browser instance."""
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
            raise ValueError(f"ESPN returned 404 for {url}")

        content = await page.content()
    finally:
        await context.close()

    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        content,
        re.DOTALL,
    )
    if not match:
        raise ValueError(f"No __NEXT_DATA__ found in {url}")

    return json.loads(match.group(1))


def _extract_match_data(next_data: dict[str, Any]) -> dict[str, Any]:
    """Extract enrichment fields from ESPN __NEXT_DATA__."""
    app_data = next_data["props"]["appPageProps"]["data"]
    data = app_data.get("data", app_data)
    match_info = data["match"]
    content = data.get("content", {})
    match_players = content.get("matchPlayers", {})
    team_players_list = match_players.get("teamPlayers", [])

    # Extract team-level player roles
    teams_enrichment: list[dict[str, Any]] = []
    for tp in team_players_list:
        team = tp.get("team", {})
        players: list[dict[str, Any]] = []
        for p in tp.get("players", []):
            player = p.get("player", {})
            role_code = p.get("playerRoleType", "P")
            players.append(
                {
                    "espn_player_id": player.get("objectId"),
                    "player_name": player.get("name"),
                    "player_long_name": player.get("longName"),
                    "role_code": role_code,
                    "role": ROLE_MAP.get(role_code, "player"),
                    "is_captain": role_code in ("C", "CWK"),
                    "is_keeper": role_code in ("WK", "CWK"),
                }
            )
        teams_enrichment.append(
            {
                "team_name": team.get("name"),
                "team_long_name": team.get("longName"),
                "espn_team_id": team.get("objectId"),
                "players": players,
            }
        )

    # Find captains and keepers per team
    team1_captain = None
    team1_keeper = None
    team2_captain = None
    team2_keeper = None

    for i, te in enumerate(teams_enrichment):
        for p in te["players"]:
            if p["is_captain"]:
                if i == 0:
                    team1_captain = p["player_name"]
                else:
                    team2_captain = p["player_name"]
            if p["is_keeper"]:
                if i == 0:
                    team1_keeper = p["player_name"]
                else:
                    team2_keeper = p["player_name"]

    return {
        "espn_match_id": match_info.get("objectId"),
        "espn_series_id": match_info.get("series", {}).get("objectId"),
        "floodlit": match_info.get("floodlit"),
        "start_date": match_info.get("startDate"),
        "start_time": match_info.get("startTime"),
        "season": match_info.get("season"),
        "title": match_info.get("title"),
        "slug": match_info.get("slug"),
        "status_text": match_info.get("statusText"),
        "team1_name": teams_enrichment[0]["team_name"] if teams_enrichment else None,
        "team1_espn_id": teams_enrichment[0]["espn_team_id"] if teams_enrichment else None,
        "team1_captain": team1_captain,
        "team1_keeper": team1_keeper,
        "team2_name": teams_enrichment[1]["team_name"] if len(teams_enrichment) > 1 else None,
        "team2_espn_id": teams_enrichment[1]["espn_team_id"] if len(teams_enrichment) > 1 else None,
        "team2_captain": team2_captain,
        "team2_keeper": team2_keeper,
        "teams_enrichment_json": json.dumps(teams_enrichment),
    }


async def scrape_matches_async(
    matches: list[dict[str, str]],
    resolver: SeriesResolver | None = None,
    delay_seconds: float = 4.0,
) -> list[dict[str, Any]]:
    """Scrape ESPN data for a list of matches.

    Uses a single browser instance for all matches to avoid repeated
    Playwright startup overhead. Includes rate limiting between requests.

    The series_id for each match is resolved dynamically via the
    SeriesResolver (cache → seed → ESPN results page discovery).

    Args:
        matches: List of dicts with 'match_id', 'match_date', and 'season' keys.
        resolver: SeriesResolver instance (created if not provided).
        delay_seconds: Seconds to wait between requests (default 4).

    Returns:
        List of enrichment dicts, one per successfully scraped match.
    """
    if resolver is None:
        resolver = SeriesResolver()

    results: list[dict[str, Any]] = []

    async with async_playwright() as pw:
        browser = await pw.webkit.launch(headless=True)

        # Step 1: Resolve all series_ids (batch — may trigger discovery)
        series_map = await resolver.resolve_batch_async(
            matches, browser, delay_seconds=delay_seconds
        )

        # Step 2: Scrape each match using its resolved series_id
        scrape_count = 0
        for i, m in enumerate(matches):
            match_id = str(m["match_id"])
            series_id = series_map.get(match_id)

            if series_id is None:
                logger.warning("skipping_no_series_id", match_id=match_id)
                continue

            url = (
                f"https://www.espncricinfo.com/series/" f"x-{series_id}/x-{match_id}/full-scorecard"
            )
            try:
                logger.info(
                    "scraping_match",
                    match_id=match_id,
                    series_id=series_id,
                    progress=f"{scrape_count + 1}/{len(matches)}",
                )
                next_data = await _fetch_next_data(url, browser)
                enrichment = _extract_match_data(next_data)
                enrichment["cricsheet_match_id"] = match_id
                results.append(enrichment)
                scrape_count += 1
                logger.info(
                    "match_scraped",
                    match_id=match_id,
                    captain1=enrichment["team1_captain"],
                    captain2=enrichment["team2_captain"],
                )
            except Exception:
                logger.exception("scrape_failed", match_id=match_id, url=url)

            # Rate limit — be respectful to ESPN
            if i < len(matches) - 1:
                await asyncio.sleep(delay_seconds)

        await browser.close()

    return results


def scrape_matches(
    matches: list[dict[str, str]],
    resolver: SeriesResolver | None = None,
    delay_seconds: float = 4.0,
) -> list[dict[str, Any]]:
    """Synchronous wrapper around scrape_matches_async."""
    return asyncio.run(
        scrape_matches_async(matches, resolver=resolver, delay_seconds=delay_seconds)
    )
