"""Download raw data from Cricsheet."""

import zipfile
from pathlib import Path

import httpx
import structlog

from src.config import settings

logger = structlog.get_logger(__name__)


def download_file(url: str, dest: Path) -> Path:
    """Download a file from a URL to a local path."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("downloading", url=url, dest=str(dest))

    with httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as response:
        response.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)

    logger.info("download_complete", dest=str(dest), size_mb=round(dest.stat().st_size / 1e6, 2))
    return dest


def download_matches() -> Path:
    """Download IPL match JSON zip and extract to raw directory."""
    zip_path = settings.raw_dir / "ipl_json.zip"
    extract_dir = settings.raw_dir / "matches"

    download_file(settings.cricsheet_matches_url, zip_path)

    logger.info("extracting", zip_path=str(zip_path), extract_dir=str(extract_dir))
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    json_count = len(list(extract_dir.glob("*.json")))
    logger.info("extraction_complete", json_files=json_count)
    return extract_dir
