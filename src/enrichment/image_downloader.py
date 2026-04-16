"""Download player/team/venue images from ESPN Cloudinary CDN.

Reads image URLs from bronze dimension tables (espn_players, espn_teams,
espn_grounds). Downloads PNGs to data/images/. Marks downloaded_at in DB.
Skips files already on disk.

Usage:
    python -m src.enrichment.image_downloader
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import httpx
import structlog

from src.config import settings
from src.database import get_read_conn, write_conn

logger = structlog.get_logger(__name__)

ESPN_CDN = "https://img1.hscicdn.com/image/upload"
PLAYER_TRANSFORM = "f_png,e_background_removal,q_auto"
TEAM_TRANSFORM = "f_png,e_background_removal,q_auto"

IMAGES_DIR = Path("data/images")
PLAYERS_DIR = IMAGES_DIR / "players"
TEAMS_DIR = IMAGES_DIR / "teams"
GROUNDS_DIR = IMAGES_DIR / "grounds"


def _get_all_pending() -> list[dict[str, Any]]:
    """Get everything that has a URL but no file on disk."""
    for d in (PLAYERS_DIR, TEAMS_DIR, GROUNDS_DIR):
        d.mkdir(parents=True, exist_ok=True)

    conn = get_read_conn()
    pending: list[dict[str, Any]] = []

    try:
        # Players
        rows = conn.execute(
            f"""
            SELECT CAST(espn_player_id AS VARCHAR), player_long_name,
                   headshot_image_url, image_url
            FROM {settings.bronze_schema}.espn_players
            WHERE headshot_image_url IS NOT NULL OR image_url IS NOT NULL
            """
        ).fetchall()
        for r in rows:
            espn_id, name = r[0], r[1]
            if not (PLAYERS_DIR / f"{espn_id}.png").exists():
                pending.append(
                    {
                        "entity_type": "player",
                        "id": espn_id,
                        "name": name,
                        "cms_path": r[2] or r[3],
                        "transform": PLAYER_TRANSFORM,
                        "dir": PLAYERS_DIR,
                        "table": f"{settings.bronze_schema}.espn_players",
                        "id_col": "espn_player_id",
                    }
                )

        # Teams
        rows = conn.execute(
            f"""
            SELECT CAST(espn_team_id AS VARCHAR), team_long_name, image_url
            FROM {settings.bronze_schema}.espn_teams
            WHERE image_url IS NOT NULL
            """
        ).fetchall()
        for r in rows:
            espn_id, name = r[0], r[1]
            if not (TEAMS_DIR / f"{espn_id}.png").exists():
                pending.append(
                    {
                        "entity_type": "team",
                        "id": espn_id,
                        "name": name,
                        "cms_path": r[2],
                        "transform": TEAM_TRANSFORM,
                        "dir": TEAMS_DIR,
                        "table": f"{settings.bronze_schema}.espn_teams",
                        "id_col": "espn_team_id",
                    }
                )

        # Grounds — skipped for now (URLs stored but not downloaded)
        # rows = conn.execute(
        #     f"""
        #     SELECT CAST(espn_ground_id AS VARCHAR), ground_long_name, image_url
        #     FROM {settings.bronze_schema}.espn_grounds
        #     WHERE image_url IS NOT NULL
        #     """
        # ).fetchall()
        # for r in rows:
        #     espn_id, name = r[0], r[1]
        #     if not (GROUNDS_DIR / f"{espn_id}.png").exists():
        #         pending.append({
        #             "entity_type": "ground",
        #             "id": espn_id,
        #             "name": name,
        #             "cms_path": r[2],
        #             "transform": "f_png,q_auto",
        #             "dir": GROUNDS_DIR,
        #             "table": f"{settings.bronze_schema}.espn_grounds",
        #             "id_col": "espn_ground_id",
        #         })
    finally:
        conn.close()

    return pending


def download_images() -> dict[str, int]:
    """Download all pending images and mark them in DB."""
    pending = _get_all_pending()
    total = len(pending)
    logger.info("image_download_start", pending=total)

    if not pending:
        logger.info("image_download_complete", downloaded=0, failed=0)
        return {"downloaded": 0, "failed": 0}

    downloaded = 0
    failed = 0
    successful: list[dict[str, Any]] = []

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for i, rec in enumerate(pending):
            target = rec["dir"] / f"{rec['id']}.png"
            url = f"{ESPN_CDN}/{rec['transform']}{rec['cms_path']}"

            try:
                resp = client.get(url)
                if resp.status_code == 200 and len(resp.content) > 100:
                    target.write_bytes(resp.content)
                    downloaded += 1
                    successful.append(rec)
                    logger.info(
                        "image_downloaded",
                        entity_type=rec["entity_type"],
                        name=rec["name"],
                        espn_id=rec["id"],
                        size_kb=round(len(resp.content) / 1024, 1),
                        progress=f"{i + 1}/{total}",
                    )
                else:
                    failed += 1
                    logger.warning(
                        "image_download_failed",
                        entity_type=rec["entity_type"],
                        name=rec["name"],
                        espn_id=rec["id"],
                        status=resp.status_code,
                        progress=f"{i + 1}/{total}",
                    )
            except Exception as e:
                failed += 1
                logger.error(
                    "image_download_error",
                    entity_type=rec["entity_type"],
                    name=rec["name"],
                    espn_id=rec["id"],
                    error=str(e),
                    progress=f"{i + 1}/{total}",
                )

            time.sleep(0.3)

    # Mark only what we just downloaded
    _mark_downloaded(successful)

    logger.info("image_download_complete", downloaded=downloaded, failed=failed)
    return {"downloaded": downloaded, "failed": failed}


def _mark_downloaded(records: list[dict[str, Any]]) -> None:
    """Mark downloaded_at for the records we just downloaded."""
    if not records:
        return
    try:
        with write_conn() as conn:
            for rec in records:
                target = rec["dir"] / f"{rec['id']}.png"
                if target.exists():
                    conn.execute(
                        f"UPDATE {rec['table']} SET downloaded_at = CURRENT_TIMESTAMP "
                        f"WHERE {rec['id_col']} = ?",
                        [int(rec["id"])],
                    )
            logger.info("marked_downloaded", count=len(records))
    except Exception as e:
        logger.warning("mark_downloaded_failed", error=str(e))


if __name__ == "__main__":
    download_images()
