"""Venue geocoding via Google Maps Geocoding API.

Resolves venue names from dim_venues to lat/lng coordinates.
One API call per unique (venue, city) combo.

Search strategy (two patterns):
    1. Strip "cricket" and "ground" from venue name, append "Cricket Ground",
       then append city.  e.g. "Chinnaswamy Stadium" → "Chinnaswamy Stadium Cricket Ground, Bengaluru"
    2. Fallback: raw "{venue}, {city}" if pattern 1 returns no results.

Alias detection (bounding box):
    When a new (venue, city) is geocoded, its coordinates are compared against
    all existing venues in bronze.venue_coordinates. If the new coordinates fall
    within a ~400m bounding box of an existing venue, it's the same ground with
    a different name/city label → stored in venue_name_mappings seed CSV.
    If outside the box → genuinely new venue, stored normally.

Usage:
    from src.enrichment.geocoder import geocode_venues, detect_alias
"""

from __future__ import annotations

import math
import os
import re
import time
from typing import Any

import requests
import structlog

from src.utils import retry

logger = structlog.get_logger(__name__)

GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Words to strip from venue name before building search pattern 1
_STRIP_WORDS = re.compile(r"\b(cricket|ground)\b", re.IGNORECASE)

# ~400m in degrees latitude (roughly constant everywhere)
_BBOX_LAT_DELTA = 400 / 111_320  # ~0.00359°


def _bbox_lng_delta(lat: float) -> float:
    """~400m in degrees longitude at a given latitude."""
    return 400 / (111_320 * math.cos(math.radians(lat)))


def _get_api_key() -> str:
    """Load Google Maps API key from environment.

    Attempts to load from .env file first (via python-dotenv),
    then falls back to the environment variable.
    """
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY not set. Add it to .env or export it.")
    return key


def _build_search_pattern_1(venue: str, city: str | None) -> str:
    """Build search pattern 1: strip 'cricket'/'ground', append 'Cricket Ground', add city.

    Examples:
        ("Chinnaswamy Stadium", "Bengaluru") → "Chinnaswamy Stadium Cricket Ground, Bengaluru"
        ("The Oval", "London") → "The Oval Cricket Ground, London"
        ("Melbourne Cricket Ground", "Melbourne") → "Melbourne Cricket Ground, Melbourne"
        ("Eden Gardens", "Kolkata") → "Eden Gardens Cricket Ground, Kolkata"
    """
    cleaned = _STRIP_WORDS.sub("", venue)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().rstrip(",-.")
    if not cleaned:
        cleaned = venue
    query = f"{cleaned} Cricket Ground"
    if city:
        query = f"{query}, {city}"
    return query


def _build_search_pattern_2(venue: str, city: str | None) -> str:
    """Fallback search pattern: raw venue + city."""
    return f"{venue}, {city}" if city else venue


@retry(max_attempts=3, base_delay=2.0, exceptions=(requests.RequestException,))
def _geocode_api_call(query: str, api_key: str) -> dict[str, Any]:
    """Make a single geocoding API call. Returns the raw API response dict."""
    resp = requests.get(
        GEOCODING_URL,
        params={"address": query, "key": api_key},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def _geocode_single(venue: str, city: str | None, api_key: str) -> dict[str, Any]:
    """Geocode a single venue using two search patterns.

    Pattern 1: normalized (strip cricket/ground, append Cricket Ground, add city)
    Pattern 2: fallback raw "{venue}, {city}"
    """
    # Try pattern 1
    query1 = _build_search_pattern_1(venue, city)
    data = _geocode_api_call(query1, api_key)

    if data.get("status") == "OK" and data.get("results"):
        loc = data["results"][0]["geometry"]["location"]
        return {
            "venue": venue,
            "city": city,
            "latitude": loc["lat"],
            "longitude": loc["lng"],
            "formatted_address": data["results"][0].get("formatted_address"),
            "place_id": data["results"][0].get("place_id"),
            "geocode_status": "ok",
            "search_pattern": query1,
        }

    # Pattern 1 failed — try pattern 2 (raw)
    logger.info("pattern1_no_result", venue=venue, query=query1, fallback="pattern2")
    query2 = _build_search_pattern_2(venue, city)
    data = _geocode_api_call(query2, api_key)

    if data.get("status") == "OK" and data.get("results"):
        loc = data["results"][0]["geometry"]["location"]
        return {
            "venue": venue,
            "city": city,
            "latitude": loc["lat"],
            "longitude": loc["lng"],
            "formatted_address": data["results"][0].get("formatted_address"),
            "place_id": data["results"][0].get("place_id"),
            "geocode_status": "ok",
            "search_pattern": query2,
        }

    # Both patterns failed
    return {
        "venue": venue,
        "city": city,
        "latitude": None,
        "longitude": None,
        "formatted_address": None,
        "place_id": None,
        "geocode_status": data.get("status") or "unknown",
        "search_pattern": query2,
    }


def is_within_bounding_box(lat1: float, lng1: float, lat2: float, lng2: float) -> bool:
    """Check if (lat2, lng2) falls within a ~400m bounding box around (lat1, lng1)."""
    if abs(lat2 - lat1) > _BBOX_LAT_DELTA:
        return False
    lng_delta = _bbox_lng_delta(lat1)
    return abs(lng2 - lng1) <= lng_delta


def detect_alias(
    new_venue: str,
    new_city: str | None,
    new_lat: float,
    new_lng: float,
    existing_venues: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Check if a newly geocoded venue is an alias of an existing one.

    Compares the new coordinates against all existing venues. If the new
    point falls within a ~400m bounding box of any existing venue, returns
    the matching existing venue dict. Otherwise returns None (genuinely new).

    Args:
        new_venue: The new venue name.
        new_city: The new city name.
        new_lat: Latitude of the new venue.
        new_lng: Longitude of the new venue.
        existing_venues: List of dicts with venue, city, latitude, longitude.

    Returns:
        The matching existing venue dict if alias detected, else None.
    """
    for existing in existing_venues:
        ex_lat = existing.get("latitude")
        ex_lng = existing.get("longitude")
        if ex_lat is None or ex_lng is None:
            continue
        if is_within_bounding_box(ex_lat, ex_lng, new_lat, new_lng):
            logger.info(
                "alias_detected",
                new_venue=new_venue,
                new_city=new_city,
                existing_venue=existing["venue"],
                existing_city=existing["city"],
                distance_lat=abs(new_lat - ex_lat),
                distance_lng=abs(new_lng - ex_lng),
            )
            return existing
    return None


def geocode_venues(
    venues: list[dict[str, str | None]],
    delay_seconds: float = 0.1,
) -> list[dict[str, Any]]:
    """Geocode a list of venues.

    Args:
        venues: List of dicts with 'venue' and 'city' keys.
        delay_seconds: Delay between API calls (Google allows 50 QPS,
            but we're conservative).

    Returns:
        List of result dicts with lat/lng and metadata.
    """
    api_key = _get_api_key()
    results: list[dict[str, Any]] = []

    for i, v in enumerate(venues):
        venue = v["venue"]
        city = v.get("city")

        try:
            result = _geocode_single(venue, city, api_key)
            results.append(result)

            if result["geocode_status"] == "ok":
                logger.info(
                    "geocoded",
                    venue=venue,
                    city=city,
                    lat=result["latitude"],
                    lng=result["longitude"],
                    pattern=result["search_pattern"],
                    progress=f"{i + 1}/{len(venues)}",
                )
            else:
                logger.warning(
                    "geocode_failed",
                    venue=venue,
                    city=city,
                    status=result["geocode_status"],
                    progress=f"{i + 1}/{len(venues)}",
                )
        except Exception:
            logger.exception("geocode_error", venue=venue)
            results.append(
                {
                    "venue": venue,
                    "city": city,
                    "latitude": None,
                    "longitude": None,
                    "formatted_address": None,
                    "place_id": None,
                    "geocode_status": "error",
                    "search_pattern": None,
                }
            )

        if i < len(venues) - 1:
            time.sleep(delay_seconds)

    ok_count = sum(1 for r in results if r["geocode_status"] == "ok")
    logger.info(
        "geocoding_complete", total=len(results), ok=ok_count, failed=len(results) - ok_count
    )
    return results
