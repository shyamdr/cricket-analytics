"""ESPN ball-by-ball spatial data scraper — v2 (two-load approach).

Key difference from v1: instead of scraping both innings in a single page
session (scroll inning 2, then switch dropdown to inning 1), v2 uses two
separate page loads — one per innings.

Why: ESPN's React/Next.js app corrupts its internal state when the innings
dropdown is clicked AFTER scrolling has loaded commentary data. The error
page JS chunk loads and the page becomes unresponsive. Switching BEFORE
scrolling works reliably, so v2 does:

  Normal matches:
    Load 1: page defaults to inning 2 → scroll to completion
    Load 2: fresh page → switch to inning 1 immediately → scroll

  Super over matches:
    The page defaults to the "Super Over" view, not regular innings
    commentary. The IntersectionObserver for loading balls isn't active
    in this view, so scrolling produces zero API calls. Both innings
    require a dropdown switch before scrolling:
    Load 1: fresh page → switch to inning 2 via dropdown → scroll
    Load 2: fresh page → switch to inning 1 via dropdown → scroll

    Detection: ``content.supportInfo.superOver == True`` in __NEXT_DATA__.
    The dropdown button shows "Super Over 1" instead of a team abbreviation.
    The dropdown panel still contains both team options (e.g. "DC", "RR",
    "Super Over 1"), so switching to regular innings works normally.

This adds ~5s per match (one extra page load) but achieves 100% innings
capture vs v1's ~95% (v1 silently loses inning 1 on ~5% of matches).

Usage:
    python -m src.enrichment.run_ball_scraper_v2 --season 2025
    python -m src.enrichment.run_ball_scraper_v2 --season 2024 --limit 5
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import structlog
from playwright.async_api import Response, Route, async_playwright

from src.config import settings
from src.enrichment.ball_data_scraper import (
    _bounce_scroll,
    _extract_balls,
    _flatten_match_balls,
)
from src.enrichment.series_resolver import SeriesResolver
from src.utils import async_retry, run_async

logger = structlog.get_logger(__name__)


async def _scroll_until_complete_v2(
    page: Any,
    captured_responses: list[dict],
    balls: list[dict],
    seen_ids: set[int],
    target_inning: int,
    max_scrolls: int = 30,
) -> bool:
    """Scroll until all balls for target_inning are loaded.

    Simpler than v1 — only tracks a single innings' ball list.
    Returns True if we reached the end (nextInningOver=None).
    """
    stale_rounds = 0

    for scroll in range(max_scrolls):
        prev_count = len(seen_ids)
        await _bounce_scroll(page)

        reached_end = False
        while captured_responses:
            api_data = captured_responses.pop(0)
            comments = api_data.get("comments", [])
            api_next = api_data.get("nextInningOver")

            for ball in _extract_balls(comments):
                bid = ball["espn_ball_id"]
                inn = ball["inning_number"]
                if bid and bid not in seen_ids and inn == target_inning:
                    seen_ids.add(bid)
                    balls.append(ball)

            if api_next is None and comments:
                reached_end = True
                break

        if reached_end:
            return True

        if len(seen_ids) == prev_count:
            stale_rounds += 1
            if stale_rounds >= 4:
                return False
        else:
            stale_rounds = 0

    return False



async def _switch_innings_v2(page: Any, target_team_abbr: str, current_team_abbr: str) -> bool:
    """Switch innings via the dropdown — scoped selector to avoid mis-clicks.

    The v1 selector `div.ds-cursor-pointer:has-text("MI")` matches elements
    outside the dropdown (match cards, team listings elsewhere on the page).
    This version scopes the option search to the elevated dropdown panel
    that appears after clicking the innings button.

    ESPN renders the dropdown options in a portal — a separate
    `ds-bg-color-bg-elevated` container, NOT inside the popper-wrapper
    that holds the button. So we find the panel, then search within it.

    On super over matches, the dropdown button text is "Super Over 1"
    instead of the current team abbreviation. We detect the actual button
    text dynamically rather than assuming it matches the team abbreviation.

    Returns True if switch was successful.
    """
    await page.evaluate("window.scrollTo(0, 0)")
    await asyncio.sleep(0.5)

    try:
        # Find the innings dropdown button. On normal matches it shows the
        # current team abbreviation (e.g. "RR"). On super over matches it
        # shows "Super Over 1". We try the team abbreviation first, then
        # fall back to detecting the button dynamically.
        dropdown_btn = page.locator(
            f'.ds-popper-wrapper button:has-text("{current_team_abbr}")'
        ).first

        if not await dropdown_btn.is_visible(timeout=2000):
            # Super over match — button text is not the team abbreviation.
            # Find the popper-wrapper button whose text contains "Super Over"
            # or any short text near the commentary area.
            dropdown_btn = page.locator(
                '.ds-popper-wrapper button:has-text("Super Over")'
            ).first

            if not await dropdown_btn.is_visible(timeout=2000):
                logger.warning("dropdown_not_visible", team=current_team_abbr)
                return False

            logger.debug("using_super_over_dropdown_button")

        await dropdown_btn.click()
        await asyncio.sleep(1.0)

        # The dropdown options render in an elevated panel.
        # Find the panel that contains the target team abbreviation.
        # On normal matches: panel has both team abbreviations.
        # On super over matches: panel has both teams + "Super Over 1".
        panel = page.locator(
            f'div.ds-bg-color-bg-elevated:has(div.ds-cursor-pointer:has-text("{target_team_abbr}"))'
        ).first

        if not await panel.is_visible(timeout=3000):
            logger.warning("dropdown_panel_not_visible")
            return False

        option = panel.locator(
            f'div.ds-cursor-pointer:has-text("{target_team_abbr}")'
        ).first
        if not await option.is_visible(timeout=3000):
            logger.warning("dropdown_option_not_visible", team=target_team_abbr)
            return False

        await option.click()
        logger.debug("innings_switched_v2", from_team=current_team_abbr, to_team=target_team_abbr)
        await asyncio.sleep(2.0)
        return True
    except Exception as e:
        logger.warning("innings_switch_failed", error=str(e))
        return False







async def _load_and_scrape_innings(
    url: str,
    browser: Any,
    target_inning: int,
    team_abbrs: dict[int, str],
    default_inning: int,
    is_super_over_match: bool = False,
) -> tuple[list[dict], set[int]]:
    """Load a fresh page and scrape a single innings.

    If target_inning != default_inning (or is_super_over_match), switches
    via dropdown BEFORE scrolling.

    On super over matches the page defaults to the "Super Over" view, not
    regular innings commentary. The IntersectionObserver for loading more
    balls isn't active, so scrolling produces zero API calls. We must
    switch to a regular innings via the dropdown first.

    Returns:
        Tuple of (ball list, seen ball IDs).
    """
    captured: list[dict] = []
    balls: list[dict] = []
    seen_ids: set[int] = set()

    async def handle_route(route: Route) -> None:
        try:
            response: Response = await route.fetch()
            body = await response.body()
            data = json.loads(body)
            captured.append(data)
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
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)

        needs_switch = is_super_over_match or target_inning != default_inning

        if needs_switch:
            # Switch IMMEDIATELY — before any scrolling.
            # On super over matches the dropdown button says "Super Over ..."
            # instead of a team abbreviation. _switch_innings_v2 handles this
            # by falling back to the "Super Over" button text.
            current_abbr = team_abbrs.get(default_inning, "")
            target_abbr = team_abbrs.get(target_inning, "")

            if not target_abbr:
                logger.warning(
                    "missing_team_abbr",
                    target_inning=target_inning,
                    team_abbrs=team_abbrs,
                )
                return balls, seen_ids

            switched = await _switch_innings_v2(page, target_abbr, current_abbr)
            if not switched:
                logger.warning("innings_switch_failed", target_inning=target_inning)
                return balls, seen_ids

            # Collect any balls from the switch response
            while captured:
                api_data = captured.pop(0)
                for ball in _extract_balls(api_data.get("comments", [])):
                    bid = ball["espn_ball_id"]
                    if bid and bid not in seen_ids and ball["inning_number"] == target_inning:
                        seen_ids.add(bid)
                        balls.append(ball)
        else:
            # Collect initial balls from __NEXT_DATA__
            html = await page.content()
            m = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                html,
                re.DOTALL,
            )
            if m:
                nd = json.loads(m.group(1))
                app_data = nd["props"]["appPageProps"]["data"]
                data = app_data.get("data", app_data)
                for ball in _extract_balls(data.get("content", {}).get("comments", [])):
                    bid = ball["espn_ball_id"]
                    if bid and bid not in seen_ids and ball["inning_number"] == target_inning:
                        seen_ids.add(bid)
                        balls.append(ball)

        # Scroll to load remaining balls
        await _scroll_until_complete_v2(page, captured, balls, seen_ids, target_inning)
    finally:
        await context.close()

    balls.sort(key=lambda b: (b["over_number"] or 0, b["ball_number"] or 0))
    return balls, seen_ids




@async_retry(max_attempts=2, base_delay=5.0, exceptions=(Exception,))
async def _scrape_single_match_v2(
    espn_match_id: int,
    espn_series_id: int,
    browser: Any,
) -> dict[str, Any]:
    """Scrape complete ball-by-ball data using two separate page loads.

    Normal matches:
      Load 1: inning 2 (page default) — scroll to completion.
      Load 2: fresh page → switch to inning 1 immediately → scroll.

    Super over matches:
      The page defaults to the "Super Over" view, not regular innings
      commentary. Scrolling in this view produces zero commentary API
      calls. Both innings require a dropdown switch before scrolling.
      Load 1: fresh page → switch to inning 2 → scroll.
      Load 2: fresh page → switch to inning 1 → scroll.
    """
    url = (
        f"https://www.espncricinfo.com/series/x-{espn_series_id}"
        f"/x-{espn_match_id}/ball-by-ball-commentary"
    )

    # Quick metadata load to get innings info and team abbreviations
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/16.0 Safari/605.1.15"
        ),
    )
    page = await context.new_page()
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        if resp and resp.status == 404:
            raise ValueError(f"ESPN returned 404 for match {espn_match_id}")

        html = await page.content()
    finally:
        await context.close()

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
    content = data.get("content", {})

    # Detect super over match — page defaults to "Super Over" view
    support_info = content.get("supportInfo", {})
    is_super_over_match = support_info.get("superOver") is True

    # Determine regular innings (skip super overs)
    innings_info = content.get("innings", [])
    regular_innings: list[int] = []
    team_abbrs: dict[int, str] = {}
    for inn_info in innings_info:
        inn_num = inn_info.get("inningNumber")
        abbr = inn_info.get("team", {}).get("abbreviation")
        if inn_num is not None and inn_num <= 2:
            regular_innings.append(inn_num)
            if abbr:
                team_abbrs[inn_num] = abbr

    if not regular_innings:
        regular_innings = [1, 2]

    default_inning = content.get("currentInningNumber", 2)
    if default_inning > 2:
        default_inning = 2

    if is_super_over_match:
        logger.info(
            "super_over_match_detected",
            espn_match_id=espn_match_id,
            team_abbrs=team_abbrs,
        )

    # Scrape each innings in a separate page load
    # For normal matches: default innings first (no switch), then the other
    # For super over matches: both need a switch, order doesn't matter
    all_balls: dict[int, list[dict]] = {}
    global_seen: set[int] = set()

    ordered = sorted(regular_innings, key=lambda i: (i != default_inning, i))

    for inn_num in ordered:
        logger.debug("scraping_innings", espn_match_id=espn_match_id, inning=inn_num)
        balls, seen = await _load_and_scrape_innings(
            url,
            browser,
            inn_num,
            team_abbrs,
            default_inning,
            is_super_over_match=is_super_over_match,
        )
        all_balls[inn_num] = balls
        global_seen.update(seen)

    total = sum(len(v) for v in all_balls.values())

    if total < 50 and len(regular_innings) >= 2:
        logger.warning(
            "partial_ball_data",
            espn_match_id=espn_match_id,
            total_balls=total,
            innings={inn: len(balls) for inn, balls in all_balls.items()},
        )

    return {
        "espn_match_id": espn_match_id,
        "innings": all_balls,
        "total_balls": total,
    }



async def scrape_ball_data_v2_async(
    matches: list[dict[str, str]],
    resolver: SeriesResolver | None = None,
    delay_seconds: float = 4.0,
    on_batch: callable | None = None,
    batch_size: int | None = None,
) -> list[dict[str, Any]]:
    """Scrape ball-by-ball data for a list of matches (v2 two-load approach)."""
    if resolver is None:
        resolver = SeriesResolver()

    if batch_size is None:
        batch_size = settings.enrichment_batch_size

    all_results: list[dict[str, Any]] = []
    batch_buffer: list[dict[str, Any]] = []

    async with async_playwright() as pw:
        browser = await pw.webkit.launch(headless=True)

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
                    "scraping_ball_data_v2",
                    match_id=match_id,
                    series_id=series_id,
                    progress=f"{scrape_count + 1}/{len(matches)}",
                )
                result = await _scrape_single_match_v2(
                    int(match_id), int(series_id), browser
                )
                flat_balls = _flatten_match_balls(
                    match_id, result["espn_match_id"], result["innings"]
                )
                all_results.extend(flat_balls)
                batch_buffer.extend(flat_balls)
                scrape_count += 1

                inn_counts = {inn: len(balls) for inn, balls in result["innings"].items()}
                logger.info(
                    "match_ball_data_scraped",
                    match_id=match_id,
                    total_balls=result["total_balls"],
                    innings=inn_counts,
                )
            except Exception:
                logger.exception("ball_scrape_failed", match_id=match_id)

            if on_batch and len(batch_buffer) >= batch_size:
                on_batch(batch_buffer)
                batch_buffer = []

            if i < len(matches) - 1:
                await asyncio.sleep(delay_seconds)

        if on_batch and batch_buffer:
            on_batch(batch_buffer)

        await browser.close()

    return all_results


def scrape_ball_data_v2(
    matches: list[dict[str, str]],
    resolver: SeriesResolver | None = None,
    delay_seconds: float = 4.0,
    on_batch: callable | None = None,
    batch_size: int | None = None,
) -> list[dict[str, Any]]:
    """Synchronous wrapper around scrape_ball_data_v2_async."""
    return run_async(
        scrape_ball_data_v2_async(
            matches,
            resolver=resolver,
            delay_seconds=delay_seconds,
            on_batch=on_batch,
            batch_size=batch_size,
        )
    )
