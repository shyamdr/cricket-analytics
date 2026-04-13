"""ESPN match-level scorecard scraper.

Scrapes match metadata, player bios, and innings summaries from ESPN
Cricinfo's full-scorecard pages via __NEXT_DATA__ JSON extraction.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import structlog
from playwright.async_api import async_playwright

from src.config import settings
from src.enrichment.series_resolver import SeriesResolver
from src.utils import NoRetryError, async_retry, run_async

logger = structlog.get_logger(__name__)

# Player role codes from ESPN teamPlayers data
ROLE_MAP: dict[str, str] = {
    "C": "captain",
    "WK": "wicketkeeper",
    "CWK": "captain_wicketkeeper",
    "P": "player",
}


@async_retry(max_attempts=3, base_delay=5.0, exceptions=(Exception,))
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
            raise NoRetryError(f"ESPN returned 404 for {url}")

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


def _extract_player_bio(player: dict[str, Any]) -> dict[str, Any]:
    """Extract biographical fields from an ESPN player object."""
    dob = player.get("dateOfBirth") or {}
    dod = player.get("dateOfDeath") or {}
    return {
        "date_of_birth_year": dob.get("year"),
        "date_of_birth_month": dob.get("month"),
        "date_of_birth_day": dob.get("date"),
        "date_of_death_year": dod.get("year") if isinstance(dod, dict) else None,
        "date_of_death_month": dod.get("month") if isinstance(dod, dict) else None,
        "date_of_death_day": dod.get("date") if isinstance(dod, dict) else None,
        "gender": player.get("gender"),
        "batting_styles": json.dumps(player.get("battingStyles") or []),
        "bowling_styles": json.dumps(player.get("bowlingStyles") or []),
        "long_batting_styles": json.dumps(player.get("longBattingStyles") or []),
        "long_bowling_styles": json.dumps(player.get("longBowlingStyles") or []),
        "country_team_id": player.get("countryTeamId"),
        "playing_roles": json.dumps(player.get("playingRoles") or []),
        "player_role_type_ids": json.dumps(player.get("playerRoleTypeIds") or []),
        "mobile_name": player.get("mobileName"),
        "index_name": player.get("indexName"),
        "batting_name": player.get("battingName"),
        "fielding_name": player.get("fieldingName"),
        "slug": player.get("slug"),
        "image_url": player.get("imageUrl"),
        "headshot_image_url": player.get("headshotImageUrl"),
    }


def _extract_match_data(next_data: dict[str, Any]) -> dict[str, Any]:
    """Extract all enrichment data from ESPN __NEXT_DATA__.

    Returns a dict with three keys:
      - match: match-level enrichment record (for bronze.espn_matches)
      - players: list of player bio records (for bronze.espn_players)
      - innings: list of innings-level records (for bronze.espn_innings)
    """
    app_data = next_data["props"]["appPageProps"]["data"]
    data = app_data.get("data", app_data)
    match_info = data["match"]
    content = data.get("content", {})
    match_players = content.get("matchPlayers", {})
    team_players_list = match_players.get("teamPlayers", [])
    espn_match_id = match_info.get("objectId")

    # --- Player extraction (biographical + match role) ---
    teams_enrichment: list[dict[str, Any]] = []
    player_records: list[dict[str, Any]] = []
    seen_player_ids: set[int] = set()

    for tp in team_players_list:
        team = tp.get("team", {})
        team_name = team.get("longName")
        players: list[dict[str, Any]] = []
        for p in tp.get("players", []):
            player = p.get("player", {})
            pid = player.get("objectId")
            role_code = p.get("playerRoleType", "P")
            players.append(
                {
                    "espn_player_id": pid,
                    "player_name": player.get("name"),
                    "player_long_name": player.get("longName"),
                    "role_code": role_code,
                    "role": ROLE_MAP.get(role_code, "player"),
                    "is_captain": role_code in ("C", "CWK"),
                    "is_keeper": role_code in ("WK", "CWK"),
                }
            )
            # Collect player bio (deduplicate across teams)
            if pid and pid not in seen_player_ids:
                seen_player_ids.add(pid)
                bio = _extract_player_bio(player)
                bio.update(
                    {
                        "espn_player_id": pid,
                        "player_name": player.get("name"),
                        "player_long_name": player.get("longName"),
                        "is_overseas": p.get("isOverseas"),
                    }
                )
                player_records.append(bio)

        teams_enrichment.append(
            {
                "team_name": team.get("name"),
                "team_long_name": team_name,
                "espn_team_id": team.get("objectId"),
                "players": players,
            }
        )

    # --- Captain / keeper extraction ---
    team1_captain = team1_keeper = team2_captain = team2_keeper = None
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

    # --- Venue / ground ---
    ground = match_info.get("ground") or {}
    town = ground.get("town") or {}
    ground_country = ground.get("country") or {}
    ground_image = ground.get("image") or {}

    # --- Ground dimension record ---
    ground_record = None
    ground_id = ground.get("objectId")
    if ground_id:
        ground_record = {
            "espn_ground_id": ground_id,
            "ground_name": ground.get("name"),
            "ground_long_name": ground.get("longName"),
            "ground_small_name": ground.get("smallName"),
            "ground_slug": ground.get("slug"),
            "town_name": town.get("name"),
            "town_area": town.get("area"),
            "timezone": town.get("timezone"),
            "country_name": ground_country.get("name"),
            "country_abbreviation": ground_country.get("abbreviation"),
            "capacity": ground.get("capacity"),
            "image_url": ground_image.get("url"),
        }

    # --- Teams match-level ---
    teams = match_info.get("teams") or []
    team1_data = teams[0] if len(teams) > 0 else {}
    team2_data = teams[1] if len(teams) > 1 else {}

    # --- Team dimension records ---
    team_records: list[dict[str, Any]] = []
    seen_team_ids: set[int] = set()
    for td in teams:
        t = td.get("team") or {}
        tid = t.get("objectId")
        if tid and tid not in seen_team_ids:
            seen_team_ids.add(tid)
            t_image = t.get("image") or {}
            t_country = t.get("country") or {}
            team_records.append(
                {
                    "espn_team_id": tid,
                    "team_name": t.get("name"),
                    "team_long_name": t.get("longName"),
                    "team_abbreviation": t.get("abbreviation"),
                    "team_unofficial_name": t.get("unofficialName"),
                    "team_slug": t.get("slug"),
                    "is_country": t.get("isCountry"),
                    "primary_color": t.get("primaryColor"),
                    "image_url": t_image.get("url"),
                    "country_name": t_country.get("name"),
                    "country_abbreviation": t_country.get("abbreviation"),
                }
            )

    # --- Replacement players ---
    replacements = match_info.get("replacementPlayers") or []
    replacement_records = []
    for rp in replacements:
        rp_player = rp.get("player") or {}
        rp_replacing = rp.get("replacingPlayer") or {}
        rp_team = rp.get("team") or {}
        replacement_records.append(
            {
                "player_in_id": rp_player.get("objectId"),
                "player_in_name": rp_player.get("name"),
                "player_out_id": rp_replacing.get("objectId"),
                "player_out_name": rp_replacing.get("name"),
                "team": rp_team.get("name"),
                "over": rp.get("over"),
                "inning": rp.get("inning"),
                "replacement_type": rp.get("playerReplacementType"),
            }
        )

    # --- Innings-level data ---
    innings_list = content.get("innings") or []
    innings_records: list[dict[str, Any]] = []
    for inn in innings_list:
        inn_num = inn.get("inningNumber")
        inn_team = (inn.get("team") or {}).get("longName")

        # Batting details (minutes at crease, battedType, dismissalText)
        batsmen_details = []
        for b in inn.get("inningBatsmen") or []:
            bp = b.get("player") or {}
            dismissal_text = b.get("dismissalText") or {}
            batsmen_details.append(
                {
                    "espn_player_id": bp.get("objectId"),
                    "player_name": bp.get("name"),
                    "batted_type": b.get("battedType"),
                    "minutes": b.get("minutes"),
                    "dismissal_text_short": dismissal_text.get("short"),
                    "dismissal_text_long": dismissal_text.get("long"),
                    "dismissal_text_commentary": dismissal_text.get("commentary"),
                }
            )

        # Partnerships
        partnerships = []
        for pt in inn.get("inningPartnerships") or []:
            p1 = pt.get("player1") or {}
            p2 = pt.get("player2") or {}
            partnerships.append(
                {
                    "player1_id": p1.get("objectId"),
                    "player1_name": p1.get("name"),
                    "player1_runs": pt.get("player1Runs"),
                    "player1_balls": pt.get("player1Balls"),
                    "player2_id": p2.get("objectId"),
                    "player2_name": p2.get("name"),
                    "player2_runs": pt.get("player2Runs"),
                    "player2_balls": pt.get("player2Balls"),
                    "total_runs": pt.get("runs"),
                    "total_balls": pt.get("balls"),
                    "out_player_id": pt.get("outPlayerId"),
                }
            )

        # DRS reviews
        drs_reviews = []
        for dr in inn.get("inningDRSReviews") or []:
            drs_reviews.append(
                {
                    "review_side": dr.get("reviewSide"),
                    "is_umpire_call": dr.get("isUmpireCall"),
                    "remaining_count": dr.get("remainingCount"),
                    "original_decision": dr.get("originalDecision"),
                    "drs_decision": dr.get("drsDecision"),
                    "overs_actual": dr.get("oversActual"),
                }
            )

        # Over group phases (powerplay/middle/death)
        over_groups = []
        for og in inn.get("inningOverGroups") or []:
            over_groups.append(
                {
                    "phase_type": og.get("type"),
                    "start_over": og.get("startOverNumber"),
                    "end_over": og.get("endOverNumber"),
                    "runs": og.get("oversRuns"),
                    "wickets": og.get("oversWickets"),
                }
            )

        innings_records.append(
            {
                "espn_match_id": espn_match_id,
                "inning_number": inn_num,
                "batting_team": inn_team,
                "runs_saved": inn.get("runsSaved"),
                "catches_dropped": inn.get("catchesDropped"),
                "batsmen_details_json": json.dumps(batsmen_details),
                "partnerships_json": json.dumps(partnerships),
                "drs_reviews_json": json.dumps(drs_reviews),
                "over_groups_json": json.dumps(over_groups),
            }
        )

    # --- Per-ball data from scorecard (inningOvers) ---
    ball_records: list[dict[str, Any]] = []
    for inn in innings_list:
        inn_num = inn.get("inningNumber")
        for over_obj in inn.get("inningOvers") or []:
            over_num = over_obj.get("overNumber")
            for ball in over_obj.get("balls") or []:
                preds = ball.get("predictions") or {}
                ball_records.append(
                    {
                        "espn_ball_id": ball.get("id"),
                        "espn_match_id": espn_match_id,
                        "inning_number": inn_num,
                        "over_number": over_num,
                        "ball_number": ball.get("ballNumber"),
                        "overs_actual": ball.get("oversActual"),
                        "batsman_player_id": ball.get("batsmanPlayerId"),
                        "bowler_player_id": ball.get("bowlerPlayerId"),
                        "non_striker_player_id": ball.get("nonStrikerPlayerId"),
                        "batsman_runs": ball.get("batsmanRuns"),
                        "total_runs": ball.get("totalRuns"),
                        "total_inning_runs": ball.get("totalInningRuns"),
                        "total_inning_wickets": ball.get("totalInningWickets"),
                        "is_four": ball.get("isFour"),
                        "is_six": ball.get("isSix"),
                        "is_wicket": ball.get("isWicket"),
                        "dismissal_type": ball.get("dismissalType"),
                        "out_player_id": ball.get("outPlayerId"),
                        "wides": ball.get("wides", 0),
                        "noballs": ball.get("noballs", 0),
                        "byes": ball.get("byes", 0),
                        "legbyes": ball.get("legbyes", 0),
                        "penalties": ball.get("penalties", 0),
                        "wagon_x": ball.get("wagonX"),
                        "wagon_y": ball.get("wagonY"),
                        "wagon_zone": ball.get("wagonZone"),
                        "pitch_line": ball.get("pitchLine"),
                        "pitch_length": ball.get("pitchLength"),
                        "shot_type": ball.get("shotType"),
                        "shot_control": ball.get("shotControl"),
                        "predicted_score": preds.get("score"),
                        "win_probability": preds.get("winProbability"),
                    }
                )

    # --- Match record ---
    match_record = {
        "espn_match_id": espn_match_id,
        "espn_series_id": match_info.get("series", {}).get("objectId"),
        "floodlit": match_info.get("floodlit"),
        "start_date": match_info.get("startDate"),
        "start_time": match_info.get("startTime"),
        "end_time": match_info.get("endTime"),
        "hours_info": match_info.get("hoursInfo"),
        "season": match_info.get("season"),
        "title": match_info.get("title"),
        "slug": match_info.get("slug"),
        "status_text": match_info.get("statusText"),
        # Classification
        "international_class_id": match_info.get("internationalClassId"),
        "sub_class_id": match_info.get("subClassId"),
        # Venue
        "espn_ground_id": ground.get("objectId"),
        "ground_name": ground.get("name"),
        "ground_long_name": ground.get("longName"),
        "ground_capacity": ground.get("capacity"),
        "ground_country_name": ((ground.get("country") or {}).get("name")),
        "ground_country_abbreviation": ((ground.get("country") or {}).get("abbreviation")),
        "venue_timezone": town.get("timezone"),
        "ground_image_url": (ground.get("image") or {}).get("url"),
        # Team 1
        "team1_name": teams_enrichment[0]["team_name"] if teams_enrichment else None,
        "team1_espn_id": teams_enrichment[0]["espn_team_id"] if teams_enrichment else None,
        "team1_abbreviation": ((team1_data.get("team") or {}).get("abbreviation")),
        "team1_captain": team1_captain,
        "team1_keeper": team1_keeper,
        "team1_is_home": team1_data.get("isHome"),
        "team1_points": team1_data.get("points"),
        "team1_primary_color": (team1_data.get("team") or {}).get("primaryColor"),
        "team1_logo_url": ((team1_data.get("team") or {}).get("image") or {}).get("url"),
        # Team 2
        "team2_name": teams_enrichment[1]["team_name"] if len(teams_enrichment) > 1 else None,
        "team2_espn_id": teams_enrichment[1]["espn_team_id"] if len(teams_enrichment) > 1 else None,
        "team2_abbreviation": ((team2_data.get("team") or {}).get("abbreviation")),
        "team2_captain": team2_captain,
        "team2_keeper": team2_keeper,
        "team2_is_home": team2_data.get("isHome"),
        "team2_points": team2_data.get("points"),
        "team2_primary_color": (team2_data.get("team") or {}).get("primaryColor"),
        "team2_logo_url": ((team2_data.get("team") or {}).get("image") or {}).get("url"),
        # Replacements & debut
        "replacement_players_json": json.dumps(replacement_records)
        if replacement_records
        else None,
        "debut_players_json": json.dumps(match_info.get("debutPlayers")),
        # Legacy (kept for backward compat)
        "teams_enrichment_json": json.dumps(teams_enrichment),
    }

    return {
        "match": match_record,
        "players": player_records,
        "teams": team_records,
        "ground": ground_record,
        "innings": innings_records,
        "balls": ball_records,
    }


async def scrape_matches_async(
    matches: list[dict[str, str]],
    resolver: SeriesResolver | None = None,
    delay_seconds: float = 4.0,
    on_batch: callable | None = None,
    batch_size: int | None = None,
) -> list[dict[str, Any]]:
    """Scrape ESPN scorecard data for a list of matches.

    Extracts match metadata, player bios, innings stats from the scorecard
    page's __NEXT_DATA__. Fast (~4s/match) and reliable.

    Ball-by-ball spatial data (wagon wheel, pitch map) is handled separately
    by the dedicated ball scraper (``src.enrichment.ball_scraper``) which uses
    commentary page scroll interception with two page loads per match (one per
    innings). Run it via::

        python -m src.enrichment.run_ball_scraper --season 2024
        python -m src.enrichment.run_ball_scraper --matches 1473469,1473443

    Args:
        matches: List of dicts with 'match_id', 'match_date', and 'season' keys.
        resolver: SeriesResolver instance (created if not provided).
        delay_seconds: Seconds to wait between requests (default 4).
        on_batch: Optional callback called with a list of results every batch_size
                  matches. Used to persist intermediate results so progress isn't
                  lost on failure.
        batch_size: Number of matches per batch for on_batch callback.
                  Defaults to settings.enrichment_batch_size.

    Returns:
        List of enrichment dicts, one per successfully scraped match.
    """
    if resolver is None:
        resolver = SeriesResolver()

    if batch_size is None:
        batch_size = settings.enrichment_batch_size

    results: list[dict[str, Any]] = []
    batch_buffer: list[dict[str, Any]] = []

    async with async_playwright() as pw:
        browser = await pw.webkit.launch(headless=True)

        # Step 1: Resolve all series_ids (batch — may trigger discovery)
        series_map = await resolver.resolve_batch_async(
            matches, browser, delay_seconds=delay_seconds
        )

        # Step 2: Scrape each match — scorecard only
        scrape_count = 0
        for i, m in enumerate(matches):
            match_id = str(m["match_id"])
            series_id = series_map.get(match_id)

            if series_id is None:
                logger.warning("skipping_no_series_id", match_id=match_id)
                continue

            url = f"https://www.espncricinfo.com/series/x-{series_id}/x-{match_id}/full-scorecard"
            try:
                logger.info(
                    "scraping_match",
                    match_id=match_id,
                    series_id=series_id,
                    progress=f"{scrape_count + 1}/{len(matches)}",
                )

                next_data = await _fetch_next_data(url, browser)
                extracted = _extract_match_data(next_data)
                match_record = extracted["match"]
                match_record["cricsheet_match_id"] = match_id

                # Drop the scorecard's ~12 ball sample — it's incomplete and
                # the dedicated ball scraper will capture full data separately
                extracted["balls"] = []

                results.append(extracted)
                batch_buffer.append(extracted)
                scrape_count += 1
                logger.info(
                    "match_scraped",
                    match_id=match_id,
                    captain1=match_record["team1_captain"],
                    captain2=match_record["team2_captain"],
                    players=len(extracted["players"]),
                )
            except NoRetryError as exc:
                logger.warning("match_skipped", match_id=match_id, reason=str(exc))
            except Exception:
                logger.exception("scrape_failed", match_id=match_id, url=url)

            # Persist batch to avoid losing progress on failure
            if on_batch and len(batch_buffer) >= batch_size:
                on_batch(batch_buffer)
                batch_buffer = []

            # Rate limit — be respectful to ESPN
            if i < len(matches) - 1:
                await asyncio.sleep(delay_seconds)

        # Flush remaining
        if on_batch and batch_buffer:
            on_batch(batch_buffer)

        await browser.close()

    return results


def scrape_matches(
    matches: list[dict[str, str]],
    resolver: SeriesResolver | None = None,
    delay_seconds: float = 4.0,
    on_batch: callable | None = None,
    batch_size: int | None = None,
) -> list[dict[str, Any]]:
    """Synchronous wrapper around scrape_matches_async."""
    return run_async(
        scrape_matches_async(
            matches,
            resolver=resolver,
            delay_seconds=delay_seconds,
            on_batch=on_batch,
            batch_size=batch_size,
        )
    )
