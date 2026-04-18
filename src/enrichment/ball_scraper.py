"""ESPN ball-by-ball spatial data scraper.

Scrapes complete ball-level data (wagon wheel, pitch map, shot type, win
probability) from ESPN Cricinfo's commentary pages using Playwright route
interception.

Architecture:
    1. Load the ball-by-ball commentary page in headless WebKit
    2. Intercept ESPN's hs-consumer-api commentary responses via page.route()
    3. Scroll to trigger the page's IntersectionObserver (~12 balls per scroll)
    4. Use two separate page loads per match — one per innings
    5. Deduplicate and return all balls sorted by over/ball number

Two-load approach:
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

Key constraint: ESPN's WAF blocks all programmatic API calls. Only requests
initiated by the page's own JavaScript succeed. We MUST use scroll-triggered
requests intercepted via route.fetch().

Usage:
    from src.enrichment.ball_scraper import scrape_ball_data

    results = scrape_ball_data(
        matches=[{"match_id": "1422133", "match_date": "2024-03-22", "season": "2024"}],
        on_batch=persist_fn,
    )

CLI:
    python -m src.enrichment.run_ball_scraper --season 2025
    python -m src.enrichment.run_ball_scraper --season 2024 --limit 5
    python -m src.enrichment.run_ball_scraper --matches 1473469,1473443
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

import structlog
from playwright.async_api import Response, Route, async_playwright

from src.enrichment.series_resolver import SeriesResolver
from src.utils import NoRetryError, async_retry, run_async

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Field extraction & helpers
# ---------------------------------------------------------------------------


def _extract_commentary_text(comment: dict) -> str | None:
    """Extract human-readable commentary text from a comment's textItems."""
    items = comment.get("commentTextItems") or []
    if not items:
        return None
    parts = []
    for item in items:
        text = item.get("html") or item.get("text") or ""
        if text:
            parts.append(text)
    return " ".join(parts).strip() or None


def _extract_balls(comments: list[dict]) -> list[dict[str, Any]]:
    """Extract structured numeric/spatial fields from ESPN commentary ball objects."""
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


def _extract_ball_commentary(comments: list[dict]) -> list[dict[str, Any]]:
    """Extract per-ball commentary text into separate records for the commentary table.

    Captures ALL text/editorial streams per ball that ESPN returns:
    - commentTextItems: main ball description
    - commentPreTextItems: editorial text before the ball (over summaries, analysis)
    - commentPostTextItems: editorial text after the ball (post-match, innings break)
    - smartStats: contextual stats (ESPN only populates this for live matches / not in archive)
    - batsmanStatText: batter stat summary (not populated in archived matches)
    - bowlerStatText: bowler stat summary (not populated in archived matches)
    - dismissalText: human-readable dismissal description (wickets only)
    - events: structured event data (replacements, milestones, reviews)
    - commentImages: photo attachments (key moments)
    - over: end-of-over summary dict with team stats

    Note: smartStats/batsmanStatText/bowlerStatText columns exist in the DDL
    for forward compatibility but are empirically NULL across archived matches
    (verified via probe on 2023 and 2026 IPL matches). Keeping them captured
    in case ESPN populates them during live matches or adds them retroactively.
    """
    entries = []
    for c in comments:
        if c.get("overNumber") is None or c.get("ballNumber") is None:
            continue

        main_text = _extract_commentary_text(c)
        title = c.get("title")

        # Pre-ball editorial
        pre_items = c.get("commentPreTextItems") or []
        pre_text = (
            " ".join(item.get("html") or item.get("text") or "" for item in pre_items).strip()
            or None
        )

        # Post-ball editorial
        post_items = c.get("commentPostTextItems") or []
        post_text = (
            " ".join(item.get("html") or item.get("text") or "" for item in post_items).strip()
            or None
        )

        # Smart stats (contextual stats ESPN shows — typically empty in archive)
        smart_stats_raw = c.get("smartStats") or []
        smart_stats = json.dumps(smart_stats_raw) if smart_stats_raw else None

        # Batter/bowler stat text (typically NULL in archived matches)
        batsman_stat_text = c.get("batsmanStatText")
        bowler_stat_text = c.get("bowlerStatText")

        # Dismissal text (dict with short/long/commentary/fielder/bowler)
        dismissal_raw = c.get("dismissalText")
        dismissal_text = json.dumps(dismissal_raw) if dismissal_raw else None

        # Events (milestones, reviews, replacements, etc.)
        events_raw = c.get("events") or []
        events = json.dumps(events_raw) if events_raw else None

        # Photo attachments (key moments)
        comment_images_raw = c.get("commentImages") or []
        comment_images = json.dumps(comment_images_raw) if comment_images_raw else None

        # End-of-over summary (present only on the last ball of each over)
        over_raw = c.get("over")
        over_summary = json.dumps(over_raw) if over_raw else None

        if not any(
            [
                main_text,
                title,
                pre_text,
                post_text,
                smart_stats,
                batsman_stat_text,
                bowler_stat_text,
                dismissal_text,
                events,
                comment_images,
                over_summary,
            ]
        ):
            continue

        entries.append(
            {
                "espn_ball_id": c.get("id"),
                "inning_number": c.get("inningNumber"),
                "over_number": c.get("overNumber"),
                "ball_number": c.get("ballNumber"),
                "title": title,
                "commentary_text": main_text,
                "pre_text": pre_text,
                "post_text": post_text,
                "smart_stats": smart_stats,
                "batsman_stat_text": batsman_stat_text,
                "bowler_stat_text": bowler_stat_text,
                "dismissal_text": dismissal_text,
                "events": events,
                "comment_images": comment_images,
                "over_summary": over_summary,
            }
        )
    return entries


async def _bounce_scroll(page: Any) -> None:
    """Bounce scroll to trigger ESPN's IntersectionObserver for commentary loading."""
    height = await page.evaluate("document.body.scrollHeight")
    await page.evaluate(f"window.scrollTo(0, {height})")
    await asyncio.sleep(0.4)
    await page.evaluate(f"window.scrollTo(0, {height - 500})")
    await asyncio.sleep(0.2)
    await page.evaluate(f"window.scrollTo(0, {height + 1000})")
    await asyncio.sleep(1.2)


def _flatten_match_balls(
    cricsheet_match_id: str,
    espn_match_id: int,
    innings: dict[int, list[dict]],
) -> list[dict[str, Any]]:
    """Flatten innings dict into a flat list of ball records with match IDs attached."""
    rows = []
    for _inn_num, balls in innings.items():
        for ball in balls:
            rows.append(
                {
                    "cricsheet_match_id": cricsheet_match_id,
                    "espn_match_id": espn_match_id,
                    **ball,
                }
            )
    return rows


def _flatten_commentary(
    cricsheet_match_id: str,
    espn_match_id: int,
    commentary: list[dict],
) -> list[dict[str, Any]]:
    """Flatten commentary entries with match IDs attached."""
    return [
        {
            "cricsheet_match_id": cricsheet_match_id,
            "espn_match_id": espn_match_id,
            **entry,
        }
        for entry in commentary
    ]


# ---------------------------------------------------------------------------
# Scrolling & innings switching (two-load approach)
# ---------------------------------------------------------------------------


async def _scroll_until_complete(
    page: Any,
    captured_responses: list[dict],
    balls: list[dict],
    seen_ids: set[int],
    target_inning: int,
    ball_commentary: list[dict] | None = None,
    max_scrolls: int = 30,
) -> bool:
    """Scroll until all balls for target_inning are loaded."""
    stale_rounds = 0

    for _scroll in range(max_scrolls):
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

            # Collect per-ball commentary text
            if ball_commentary is not None:
                ball_commentary.extend(_extract_ball_commentary(comments))

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


async def _switch_innings(page: Any, target_team_abbr: str, current_team_abbr: str) -> bool:
    """Switch innings via the dropdown — scoped selector to avoid mis-clicks.

    Scopes the option search to the elevated dropdown panel that appears
    after clicking the innings button. ESPN renders the dropdown options in
    a portal (``ds-bg-color-bg-elevated`` container), NOT inside the
    popper-wrapper that holds the button.

    On super over matches the dropdown button text is "Super Over 1" instead
    of the current team abbreviation. We try the team abbreviation first,
    then fall back to detecting the "Super Over" button.

    Returns True if switch was successful.
    """
    await page.evaluate("window.scrollTo(0, 0)")
    await asyncio.sleep(0.5)

    try:
        dropdown_btn = page.locator(
            f'.ds-popper-wrapper button:has-text("{current_team_abbr}")'
        ).first

        if not await dropdown_btn.is_visible(timeout=2000):
            # Super over match — button text is not the team abbreviation.
            dropdown_btn = page.locator('.ds-popper-wrapper button:has-text("Super Over")').first

            if not await dropdown_btn.is_visible(timeout=2000):
                logger.warning("dropdown not visible", team=current_team_abbr)
                return False

        await dropdown_btn.click()
        await asyncio.sleep(1.0)

        # The dropdown options render in an elevated panel.
        panel = page.locator(
            f'div.ds-bg-color-bg-elevated:has(div.ds-cursor-pointer:has-text("{target_team_abbr}"))'
        ).first

        if not await panel.is_visible(timeout=3000):
            logger.warning("dropdown panel not visible")
            return False

        option = panel.locator(f'div.ds-cursor-pointer:has-text("{target_team_abbr}")').first
        if not await option.is_visible(timeout=3000):
            logger.warning("dropdown option not visible", team=target_team_abbr)
            return False

        await option.click()
        await asyncio.sleep(2.0)
        return True
    except Exception as e:
        logger.warning("innings_switch_failed", error=str(e))
        return False


# ---------------------------------------------------------------------------
# Per-innings page load
# ---------------------------------------------------------------------------


async def _load_and_scrape_innings(
    url: str,
    browser: Any,
    target_inning: int,
    team_abbrs: dict[int, str],
    default_inning: int,
    is_super_over_match: bool = False,
    extract_metadata: bool = False,
) -> tuple[list[dict], set[int], dict | None, list[dict]]:
    """Load a fresh page and scrape a single innings.

    Returns:
        Tuple of (ball list, seen ball IDs, metadata dict or None, ball commentary).
    """
    captured: list[dict] = []
    balls: list[dict] = []
    seen_ids: set[int] = set()
    ball_comm: list[dict] = []
    metadata: dict | None = None

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

        resp = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        if resp and resp.status == 404:
            raise NoRetryError(f"ESPN returned 404 for {url}")

        needs_switch = is_super_over_match or target_inning != default_inning

        if needs_switch:
            # If we also need metadata, grab __NEXT_DATA__ before switching
            if extract_metadata:
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
                    metadata = data.get("content", {})

            current_abbr = team_abbrs.get(default_inning, "")
            target_abbr = team_abbrs.get(target_inning, "")

            if not target_abbr:
                logger.warning("missing_team_abbreviation", inning=target_inning)
                return balls, seen_ids, metadata, ball_comm

            switched = await _switch_innings(page, target_abbr, current_abbr)
            if not switched:
                logger.warning("innings_switch_failed", inning=target_inning)
                return balls, seen_ids, metadata, ball_comm

            # Collect any balls from the switch response
            while captured:
                api_data = captured.pop(0)
                switch_comments = api_data.get("comments", [])
                for ball in _extract_balls(switch_comments):
                    bid = ball["espn_ball_id"]
                    if bid and bid not in seen_ids and ball["inning_number"] == target_inning:
                        seen_ids.add(bid)
                        balls.append(ball)
                ball_comm.extend(_extract_ball_commentary(switch_comments))
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
                content = data.get("content", {})

                if extract_metadata:
                    metadata = content

                initial_comments = content.get("comments", [])
                for ball in _extract_balls(initial_comments):
                    bid = ball["espn_ball_id"]
                    if bid and bid not in seen_ids and ball["inning_number"] == target_inning:
                        seen_ids.add(bid)
                        balls.append(ball)
                ball_comm.extend(_extract_ball_commentary(initial_comments))

        # Scroll to load remaining balls
        await _scroll_until_complete(page, captured, balls, seen_ids, target_inning, ball_comm)
    finally:
        await context.close()

    balls.sort(key=lambda b: (b["over_number"] or 0, b["ball_number"] or 0))
    return balls, seen_ids, metadata, ball_comm


# ---------------------------------------------------------------------------
# Single-match scraper
# ---------------------------------------------------------------------------


@async_retry(max_attempts=2, base_delay=5.0, exceptions=(Exception,))
async def _scrape_single_match(
    espn_match_id: int,
    espn_series_id: int,
    browser: Any,
) -> dict[str, Any]:
    """Scrape complete ball-by-ball data using two page loads (optimized).

    Previous approach used 3 loads: metadata + innings 2 + innings 1.
    Optimized approach folds metadata extraction into the first innings
    load, saving ~3-5s per match.

    Normal matches (2 loads):
      Load 1: page defaults to inning 2 → extract metadata from
              __NEXT_DATA__ + scroll to completion.
      Load 2: fresh page → switch to inning 1 → scroll.

    Super over matches (2 loads):
      Load 1: fresh page → extract metadata from __NEXT_DATA__ →
              switch to inning 2 → scroll.
      Load 2: fresh page → switch to inning 1 → scroll.
    """
    url = (
        f"https://www.espncricinfo.com/series/x-{espn_series_id}"
        f"/x-{espn_match_id}/ball-by-ball-commentary"
    )

    # --- Load 1: default innings + metadata extraction ---
    # We don't know yet if it's a super over match, so we load with
    # default_inning=2 (the normal default) and extract_metadata=True.
    # The metadata tells us the actual default inning and super over status.
    # For normal matches this load also scrapes inning 2 (the default).
    # For super over matches, we'll need to switch — but we still get
    # metadata from __NEXT_DATA__ before the switch happens.

    # First pass: load page, extract metadata, scrape default innings
    first_balls, first_seen, metadata, first_ball_comm = await _load_and_scrape_innings(
        url,
        browser,
        target_inning=2,  # assume default; corrected below if needed
        team_abbrs={},  # empty — no switch on first load for normal matches
        default_inning=2,
        is_super_over_match=False,
        extract_metadata=True,
    )

    if not metadata:
        raise ValueError(f"No __NEXT_DATA__ found for match {espn_match_id}")

    # Parse metadata from the content dict
    support_info = metadata.get("supportInfo", {})
    is_super_over_match = support_info.get("superOver") is True

    innings_info = metadata.get("innings", [])
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

    default_inning = metadata.get("currentInningNumber", 2)
    if default_inning > 2:
        default_inning = 2

    if is_super_over_match:
        pass  # handled below — both innings need dropdown switch

    all_balls: dict[int, list[dict]] = {}
    global_seen: set[int] = set()

    # Check if Load 1 actually scraped the default innings successfully.
    # For normal matches where default_inning == 2, Load 1 scraped inning 2.
    # For super over matches, Load 1 tried to scrape inning 2 without
    # switching (since we didn't know it was a super over yet), so it got
    # zero balls. We need to re-scrape inning 2 with the switch.
    load1_valid = len(first_balls) > 0 and not is_super_over_match

    if load1_valid:
        all_balls[default_inning] = first_balls
        global_seen.update(first_seen)

    # Determine which innings still need scraping
    remaining = [i for i in regular_innings if i not in all_balls]
    # Sort: default innings first (no switch needed) if not yet scraped
    remaining.sort(key=lambda i: (i != default_inning, i))

    all_ball_comm: list[dict] = list(first_ball_comm)

    for inn_num in remaining:
        balls, seen, _, inn_ball_comm = await _load_and_scrape_innings(
            url,
            browser,
            inn_num,
            team_abbrs,
            default_inning,
            is_super_over_match=is_super_over_match,
        )
        all_balls[inn_num] = balls
        global_seen.update(seen)
        all_ball_comm.extend(inn_ball_comm)

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
        "ball_commentary": all_ball_comm,
        "total_balls": total,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def scrape_ball_data_async(
    matches: list[dict[str, str]],
    resolver: SeriesResolver | None = None,
    delay_seconds: float = 4.0,
    on_batch: Callable | None = None,
    on_commentary_batch: Callable | None = None,
    on_status: Callable | None = None,
    batch_size: int = 10,
) -> list[dict[str, Any]]:
    """Scrape ball-by-ball data for a list of matches.

    Args:
        matches: List of dicts with 'match_id', 'match_date', and 'season' keys.
        resolver: SeriesResolver instance (created if not provided).
        delay_seconds: Seconds to wait between matches (default 4).
        on_batch: Callback with list of flat ball records every batch_size matches.
        on_commentary_batch: Callback with list of non-ball commentary records.
        on_status: Callback(match_id, series_id, status) for tracking outcomes.
        batch_size: Number of matches between DB writes (default 10).

    Returns:
        List of flat ball record dicts (one per ball across all matches).
    """
    if resolver is None:
        resolver = SeriesResolver()

    total_matches = len(matches)
    all_results: list[dict[str, Any]] = []
    batch_buffer: list[dict[str, Any]] = []
    ball_comm_buffer: list[dict[str, Any]] = []

    batch_match_count = 0
    failed_matches: list[str] = []

    async with async_playwright() as pw:
        browser = await pw.webkit.launch(headless=True)

        series_map = await resolver.resolve_batch_async(
            matches, browser, delay_seconds=delay_seconds
        )

        scrape_count = 0
        for i, m in enumerate(matches):
            match_id = str(m["match_id"])
            match_date = m.get("match_date", "?")
            series_id = series_map.get(match_id)

            if series_id is None:
                logger.warning(
                    "skip_no_series_id",
                    progress=f"{scrape_count + 1}/{total_matches}",
                    match_id=match_id,
                    date=match_date,
                )
                failed_matches.append(match_id)
                continue

            try:
                result = await _scrape_single_match(int(match_id), int(series_id), browser)
                flat_balls = _flatten_match_balls(
                    match_id, result["espn_match_id"], result["innings"]
                )
                flat_ball_comm = _flatten_commentary(
                    match_id, result["espn_match_id"], result.get("ball_commentary", [])
                )
                all_results.extend(flat_balls)
                batch_buffer.extend(flat_balls)
                ball_comm_buffer.extend(flat_ball_comm)
                batch_match_count += 1
                scrape_count += 1

                inn_details = " + ".join(
                    f"inn{inn}={len(balls)}" for inn, balls in sorted(result["innings"].items())
                )
                logger.info(
                    "ball_scrape_success",
                    progress=f"{scrape_count}/{total_matches}",
                    match_id=match_id,
                    date=match_date,
                    total_balls=result["total_balls"],
                    innings=inn_details,
                )
                if on_status:
                    on_status(
                        match_id,
                        int(series_id),
                        "success",
                        {
                            "total_balls": result["total_balls"],
                            "date": match_date,
                            "innings": {
                                str(inn): len(balls)
                                for inn, balls in sorted(result["innings"].items())
                            },
                        },
                    )
            except (NoRetryError, ValueError) as e:
                scrape_count += 1
                if "404" in str(e):
                    logger.info(
                        "no_commentary",
                        progress=f"{scrape_count}/{total_matches}",
                        match_id=match_id,
                        date=match_date,
                    )
                    if on_status:
                        on_status(match_id, int(series_id), "no_commentary", {"date": match_date})
                else:
                    logger.error(
                        "ball_scrape_failed",
                        progress=f"{scrape_count}/{total_matches}",
                        match_id=match_id,
                        date=match_date,
                        error=str(e),
                    )
                    failed_matches.append(match_id)
                    if on_status:
                        on_status(
                            match_id,
                            int(series_id),
                            "failed",
                            {"date": match_date, "error": str(e)},
                        )
            except Exception as e:
                scrape_count += 1
                logger.error(
                    "ball_scrape_failed",
                    progress=f"{scrape_count}/{total_matches}",
                    match_id=match_id,
                    date=match_date,
                    error=str(e),
                )
                failed_matches.append(match_id)
                if on_status:
                    on_status(
                        match_id, int(series_id), "failed", {"date": match_date, "error": str(e)}
                    )

            # Persist every batch_size matches
            if on_batch and batch_match_count >= batch_size:
                on_batch(batch_buffer)
                if on_commentary_batch:
                    on_commentary_batch(ball_comm_buffer)
                batch_buffer = []
                ball_comm_buffer = []
                batch_match_count = 0

            if i < total_matches - 1:
                await asyncio.sleep(delay_seconds)

        # Flush remaining
        if on_batch and batch_buffer:
            on_batch(batch_buffer)
        if on_commentary_batch and ball_comm_buffer:
            on_commentary_batch(ball_comm_buffer)

        await browser.close()

    if failed_matches:
        logger.warning(
            "ball_scrape_failures", count=len(failed_matches), match_ids=", ".join(failed_matches)
        )

    return all_results


def scrape_ball_data(
    matches: list[dict[str, str]],
    resolver: SeriesResolver | None = None,
    delay_seconds: float = 4.0,
    on_batch: Callable | None = None,
    on_commentary_batch: Callable | None = None,
    on_status: Callable | None = None,
    batch_size: int = 10,
) -> list[dict[str, Any]]:
    """Synchronous wrapper around scrape_ball_data_async."""
    return run_async(
        scrape_ball_data_async(
            matches,
            resolver=resolver,
            delay_seconds=delay_seconds,
            on_batch=on_batch,
            on_commentary_batch=on_commentary_batch,
            on_status=on_status,
            batch_size=batch_size,
        )
    )
