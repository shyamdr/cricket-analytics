"""ESPN ball-by-ball spatial data scraper.

Scrapes complete ball-level data (wagon wheel, pitch map, shot type, win probability)
from ESPN Cricinfo's commentary pages using Playwright route interception.

Architecture:
    1. Load the ball-by-ball commentary page in headless WebKit
    2. Intercept ESPN's hs-consumer-api commentary responses via page.route()
    3. Scroll to trigger the page's IntersectionObserver (loads ~12 balls per scroll)
    4. Switch innings via the dropdown UI to capture both innings
    5. Deduplicate and return all balls sorted by over/ball number

Key constraint: ESPN's WAF blocks all programmatic API calls. Only requests
initiated by the page's own JavaScript succeed. We MUST use scroll-triggered
requests intercepted via route.fetch().

Usage:
    from src.enrichment.ball_data_scraper import scrape_ball_data

    results = scrape_ball_data(
        matches=[{"match_id": "1422133", "match_date": "2024-03-22", "season": "2024"}],
        on_batch=persist_fn,
    )
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import structlog
from playwright.async_api import Response, Route, async_playwright

from src.config import settings
from src.enrichment.series_resolver import SeriesResolver
from src.utils import async_retry, run_async

logger = structlog.get_logger(__name__)


def _extract_balls(comments: list[dict]) -> list[dict[str, Any]]:
    """Extract fields from ESPN commentary ball objects."""
    balls = []
    for c in comments:
        preds = c.get("predictions") or {}
        balls.append(
            {
                "espn_ball_id": c.get("id"),
                "inning_number": c.get("inningNumber"),
                "over_number": c.get("overNumber"),
                "ball_number": c.get("ballNumber"),
                "overs_actual": c.get("oversActual"),
                "overs_unique": c.get("oversUnique"),
                "batsman_player_id": c.get("batsmanPlayerId"),
                "bowler_player_id": c.get("bowlerPlayerId"),
                "non_striker_player_id": c.get("nonStrikerPlayerId"),
                "batsman_runs": c.get("batsmanRuns"),
                "total_runs": c.get("totalRuns"),
                "total_inning_runs": c.get("totalInningRuns"),
                "total_inning_wickets": c.get("totalInningWickets"),
                "is_four": c.get("isFour"),
                "is_six": c.get("isSix"),
                "is_wicket": c.get("isWicket"),
                "dismissal_type": c.get("dismissalType"),
                "out_player_id": c.get("outPlayerId"),
                "wides": c.get("wides", 0),
                "noballs": c.get("noballs", 0),
                "byes": c.get("byes", 0),
                "legbyes": c.get("legbyes", 0),
                "penalties": c.get("penalties", 0),
                "wagon_x": c.get("wagonX"),
                "wagon_y": c.get("wagonY"),
                "wagon_zone": c.get("wagonZone"),
                "pitch_line": c.get("pitchLine"),
                "pitch_length": c.get("pitchLength"),
                "shot_type": c.get("shotType"),
                "shot_control": c.get("shotControl"),
                "timestamp": c.get("timestamp"),
                "predicted_score": preds.get("score"),
                "win_probability": preds.get("winProbability"),
            }
        )
    return balls


async def _bounce_scroll(page: Any) -> None:
    """Bounce scroll to trigger ESPN's IntersectionObserver for commentary loading."""
    height = await page.evaluate("document.body.scrollHeight")
    await page.evaluate(f"window.scrollTo(0, {height})")
    await asyncio.sleep(0.4)
    await page.evaluate(f"window.scrollTo(0, {height - 500})")
    await asyncio.sleep(0.2)
    await page.evaluate(f"window.scrollTo(0, {height + 1000})")
    await asyncio.sleep(1.2)


async def _scroll_until_complete(
    page: Any,
    captured_responses: list[dict],
    all_balls: dict[int, list[dict]],
    seen_ids: set[int],
    target_inning: int,
    max_scrolls: int = 30,
) -> bool:
    """Scroll the page until all balls for target_inning are loaded.

    Returns True if we reached the end (nextInningOver=None).
    """
    scroll_count = 0
    stale_rounds = 0
    reached_end = False

    while scroll_count < max_scrolls and not reached_end:
        prev_count = len(seen_ids)
        await _bounce_scroll(page)
        scroll_count += 1

        # Process captured API responses
        while captured_responses:
            api_data = captured_responses.pop(0)
            comments = api_data.get("comments", [])
            api_next = api_data.get("nextInningOver")

            new_count = 0
            api_inning = None
            for ball in _extract_balls(comments):
                bid = ball["espn_ball_id"]
                inn = ball["inning_number"]
                # Skip super over balls (inning 3+)
                if bid and bid not in seen_ids and inn is not None and inn <= 2:
                    seen_ids.add(bid)
                    if inn in all_balls:
                        all_balls[inn].append(ball)
                    new_count += 1
                    api_inning = inn

            if new_count > 0:
                logger.debug(
                    "scroll_progress",
                    scroll=scroll_count,
                    new_balls=new_count,
                    inning=api_inning,
                    next_over=api_next,
                )

            if api_next is None and comments:
                logger.debug("inning_complete", inning=api_inning)
                reached_end = True
                break

        # Stale detection: no new balls after a scroll
        if len(seen_ids) == prev_count:
            stale_rounds += 1
            if stale_rounds >= 4:
                logger.debug("scroll_stale", stale_rounds=stale_rounds)
                break
        else:
            stale_rounds = 0

    return reached_end


async def _switch_innings(page: Any, target_team_abbr: str, current_team_abbr: str) -> bool:
    """Switch innings by clicking the dropdown and selecting the other team.

    Returns True if switch was successful.
    """
    # Scroll to top so the dropdown is visible
    await page.evaluate("window.scrollTo(0, 0)")
    await asyncio.sleep(0.5)

    # Click the dropdown button (shows current team abbreviation)
    try:
        dropdown_btn = page.locator(f'button:has-text("{current_team_abbr}")').first
        if not await dropdown_btn.is_visible(timeout=3000):
            logger.warning("dropdown_not_visible", team=current_team_abbr)
            return False
        await dropdown_btn.click()
        await asyncio.sleep(1.0)
    except Exception as e:
        logger.warning("dropdown_click_failed", error=str(e))
        return False

    # Click the target team option in the dropdown
    try:
        option = page.locator(f'div.ds-cursor-pointer:has-text("{target_team_abbr}")').first
        if not await option.is_visible(timeout=3000):
            logger.warning("dropdown_option_not_visible", team=target_team_abbr)
            return False
        await option.click()
        logger.debug("innings_switched", from_team=current_team_abbr, to_team=target_team_abbr)
        await asyncio.sleep(2.0)
        return True
    except Exception as e:
        logger.warning("innings_switch_failed", error=str(e))
        return False


@async_retry(max_attempts=2, base_delay=5.0, exceptions=(Exception,))
async def _scrape_single_match(
    espn_match_id: int,
    espn_series_id: int,
    browser: Any,
) -> dict[str, Any]:
    """Scrape complete ball-by-ball data for a single match.

    Opens a single page, captures both innings via scroll + dropdown switch.

    Args:
        espn_match_id: ESPN's match object ID.
        espn_series_id: ESPN's series object ID.
        browser: An open Playwright browser instance.

    Returns:
        Dict with espn_match_id, innings (dict of inning_number -> ball list),
        and total_balls count.
    """
    url = (
        f"https://www.espncricinfo.com/series/x-{espn_series_id}"
        f"/x-{espn_match_id}/ball-by-ball-commentary"
    )

    all_balls: dict[int, list[dict]] = {}
    captured_responses: list[dict] = []
    seen_ids: set[int] = set()

    async def handle_route(route: Route) -> None:
        """Intercept commentary API calls and capture response data."""
        try:
            response: Response = await route.fetch()
            body = await response.body()
            data = json.loads(body)
            captured_responses.append(data)
            await route.fulfill(response=response)
        except Exception:
            await route.continue_()

    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/16.0 Safari/605.1.15"
        ),
        viewport={"width": 1280, "height": 2000},
    )
    page = await context.new_page()

    try:
        await page.route("**/hs-consumer-api**/comments**", handle_route)

        resp = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        if resp and resp.status == 404:
            raise ValueError(f"ESPN returned 404 for match {espn_match_id}")

        # Extract __NEXT_DATA__
        html = await page.content()
        m = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        if not m:
            raise ValueError(f"No __NEXT_DATA__ found for match {espn_match_id}")

        next_data = json.loads(m.group(1))
        app_data = next_data["props"]["appPageProps"]["data"]
        data = app_data.get("data", app_data)
        match_content = data.get("content", {})

        # Determine innings count from the page data
        # Only track regular innings (1 and 2), not super overs (3+)
        innings_info = match_content.get("innings", [])
        for inn_info in innings_info:
            inn_num = inn_info.get("inningNumber")
            if inn_num is not None and inn_num <= 2:
                all_balls[inn_num] = []

        # Fallback: if no innings info, assume 2 innings
        if not all_balls:
            all_balls = {1: [], 2: []}

        # Get team abbreviations for innings switching (regular innings only)
        team_abbrs: dict[int, str] = {}
        for inn_info in innings_info:
            inn_num = inn_info.get("inningNumber")
            abbr = inn_info.get("team", {}).get("abbreviation")
            if inn_num and inn_num <= 2 and abbr:
                team_abbrs[inn_num] = abbr

        # Initial balls from __NEXT_DATA__ (last ~12 balls of most recent innings)
        initial_comments = match_content.get("comments", [])
        initial_inning = match_content.get("currentInningNumber", max(all_balls.keys()))

        # If the page defaults to a super over innings (3+), override to inning 2
        if initial_inning > 2:
            initial_inning = 2

        for ball in _extract_balls(initial_comments):
            bid = ball["espn_ball_id"]
            inn = ball["inning_number"]
            # Skip super over balls (inning 3+)
            if bid and bid not in seen_ids and inn is not None and inn <= 2:
                seen_ids.add(bid)
                if inn in all_balls:
                    all_balls[inn].append(ball)

        # Phase 1: Scroll to load all current innings balls
        current_abbr = team_abbrs.get(initial_inning, "")
        if not current_abbr:
            # No team abbreviation found — likely a super over match with
            # a different UI layout (no dropdown switcher). Log and return
            # whatever we got from __NEXT_DATA__.
            logger.warning(
                "no_team_abbr_for_innings_switch",
                espn_match_id=espn_match_id,
                initial_inning=initial_inning,
                team_abbrs=team_abbrs,
            )
        await _scroll_until_complete(page, captured_responses, all_balls, seen_ids, initial_inning)

        # Phase 2: Switch to each other innings and scroll
        other_innings = sorted(inn for inn in all_balls if inn != initial_inning)
        for other_inning in other_innings:
            target_abbr = team_abbrs.get(other_inning, "?")
            switched = await _switch_innings(page, target_abbr, current_abbr)

            if switched:
                # Process any API response from the switch
                while captured_responses:
                    api_data = captured_responses.pop(0)
                    comments = api_data.get("comments", [])
                    for ball in _extract_balls(comments):
                        bid = ball["espn_ball_id"]
                        inn = ball["inning_number"]
                        if bid and bid not in seen_ids and inn is not None and inn <= 2:
                            seen_ids.add(bid)
                            if inn in all_balls:
                                all_balls[inn].append(ball)

                # Scroll to load remaining balls
                await _scroll_until_complete(
                    page, captured_responses, all_balls, seen_ids, other_inning
                )
                current_abbr = target_abbr
            else:
                logger.warning(
                    "innings_switch_failed_skipping",
                    match_id=espn_match_id,
                    inning=other_inning,
                )
    finally:
        await context.close()

    # Sort balls within each innings
    for inn_num in all_balls:
        all_balls[inn_num].sort(key=lambda b: (b["over_number"] or 0, b["ball_number"] or 0))

    total = sum(len(v) for v in all_balls.values())

    # Detect partial data — a completed T20 innings should have ~60-130 balls.
    # If we got fewer than 50 balls total for a 2-innings match, something went wrong.
    min_expected = 50
    if total < min_expected and len(all_balls) >= 2:
        logger.warning(
            "partial_ball_data",
            espn_match_id=espn_match_id,
            total_balls=total,
            innings={inn: len(balls) for inn, balls in all_balls.items()},
            min_expected=min_expected,
        )

    return {
        "espn_match_id": espn_match_id,
        "innings": all_balls,
        "total_balls": total,
    }


def _flatten_match_balls(
    cricsheet_match_id: str,
    espn_match_id: int,
    innings: dict[int, list[dict]],
) -> list[dict[str, Any]]:
    """Flatten innings dict into a flat list of ball records with match IDs attached."""
    rows = []
    for _inn_num, balls in innings.items():
        for ball in balls:
            row = {
                "cricsheet_match_id": cricsheet_match_id,
                "espn_match_id": espn_match_id,
                **ball,
            }
            rows.append(row)
    return rows


async def scrape_ball_data_async(
    matches: list[dict[str, str]],
    resolver: SeriesResolver | None = None,
    delay_seconds: float = 4.0,
    on_batch: callable | None = None,
    batch_size: int | None = None,
) -> list[dict[str, Any]]:
    """Scrape ball-by-ball data for a list of matches.

    Uses a single browser instance for all matches. Includes rate limiting
    and batch persistence to avoid losing progress on failure.

    Args:
        matches: List of dicts with 'match_id', 'match_date', and 'season' keys.
        resolver: SeriesResolver instance (created if not provided).
        delay_seconds: Seconds to wait between matches (default 4).
        on_batch: Optional callback with a list of flat ball records every batch_size
                  matches. Used to persist intermediate results.
        batch_size: Number of matches per batch for on_batch callback.
                  Defaults to settings.enrichment_batch_size.

    Returns:
        List of flat ball record dicts (one per ball across all matches).
    """
    if resolver is None:
        resolver = SeriesResolver()

    if batch_size is None:
        batch_size = settings.enrichment_batch_size

    all_results: list[dict[str, Any]] = []
    batch_buffer: list[dict[str, Any]] = []

    async with async_playwright() as pw:
        browser = await pw.webkit.launch(headless=True)

        # Resolve series IDs for all matches
        series_map = await resolver.resolve_batch_async(
            matches, browser, delay_seconds=delay_seconds
        )

        scrape_count = 0
        for i, m in enumerate(matches):
            match_id = str(m["match_id"])
            series_id = series_map.get(match_id)

            if series_id is None:
                logger.warning("skipping_no_series_id", match_id=match_id)
                continue

            try:
                logger.info(
                    "scraping_ball_data",
                    match_id=match_id,
                    series_id=series_id,
                    progress=f"{scrape_count + 1}/{len(matches)}",
                )
                result = await _scrape_single_match(int(match_id), int(series_id), browser)
                flat_balls = _flatten_match_balls(
                    match_id, result["espn_match_id"], result["innings"]
                )
                all_results.extend(flat_balls)
                batch_buffer.extend(flat_balls)
                scrape_count += 1

                # Log per-innings stats
                inn_counts = {inn: len(balls) for inn, balls in result["innings"].items()}
                logger.info(
                    "match_ball_data_scraped",
                    match_id=match_id,
                    total_balls=result["total_balls"],
                    innings=inn_counts,
                )
            except Exception:
                logger.exception("ball_scrape_failed", match_id=match_id)

            # Persist batch
            if on_batch and len(batch_buffer) >= batch_size:
                on_batch(batch_buffer)
                batch_buffer = []

            # Rate limit
            if i < len(matches) - 1:
                await asyncio.sleep(delay_seconds)

        # Flush remaining
        if on_batch and batch_buffer:
            on_batch(batch_buffer)

        await browser.close()

    return all_results


def scrape_ball_data(
    matches: list[dict[str, str]],
    resolver: SeriesResolver | None = None,
    delay_seconds: float = 4.0,
    on_batch: callable | None = None,
    batch_size: int | None = None,
) -> list[dict[str, Any]]:
    """Synchronous wrapper around scrape_ball_data_async."""
    return run_async(
        scrape_ball_data_async(
            matches,
            resolver=resolver,
            delay_seconds=delay_seconds,
            on_batch=on_batch,
            batch_size=batch_size,
        )
    )
