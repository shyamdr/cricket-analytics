"""News feed endpoint — proxies ESPN Cricinfo RSS feed."""

from __future__ import annotations

from xml.etree import ElementTree

import httpx
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/v1/news", tags=["news"])

_RSS_URL = "https://www.espncricinfo.com/rss/content/story/feeds/0.xml"
_TIMEOUT = 10.0


@router.get("")
def get_news(limit: int = Query(10, ge=1, le=30)):
    """Fetch latest cricket news from ESPN Cricinfo RSS feed.

    Returns title, description, image URL, link, and publication date.
    """
    try:
        resp = httpx.get(_RSS_URL, timeout=_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError:
        return []

    try:
        root = ElementTree.fromstring(resp.text)
    except ElementTree.ParseError:
        return []

    items = root.findall(".//item")
    results = []

    for item in items[:limit]:
        title = item.findtext("title", "").strip()
        description = item.findtext("description", "").strip()
        link = item.findtext("url") or item.findtext("link", "").strip()
        pub_date = item.findtext("pubDate", "").strip()
        image = item.findtext("coverImages", "").strip()

        if not title:
            continue

        results.append({
            "title": title,
            "description": description,
            "link": link,
            "image": image or None,
            "pub_date": pub_date or None,
        })

    return results
