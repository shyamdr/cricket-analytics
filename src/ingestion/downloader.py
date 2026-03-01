"""Download raw data from Cricsheet.

Supports multiple datasets (IPL, T20I, ODI, Tests, BBL, PSL, etc.)
and delta downloads via Cricsheet's 'recently_added' zips.
Skips re-download when the remote file hasn't changed (HTTP Last-Modified).
"""

import email.utils
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
import structlog

from src.config import CRICSHEET_DATASETS, settings
from src.utils import retry

logger = structlog.get_logger(__name__)


def _is_download_needed(url: str, local_path: Path) -> bool:
    """Check if the remote file is newer than the local copy.

    Uses HTTP HEAD + Last-Modified header. Returns True (download needed)
    if the local file doesn't exist, the server doesn't provide
    Last-Modified, or the remote file is newer.
    """
    if not local_path.exists():
        return True

    try:
        resp = httpx.head(url, follow_redirects=True, timeout=30.0)
        resp.raise_for_status()
    except httpx.HTTPError:
        # Can't check — download to be safe
        return True

    last_modified = resp.headers.get("last-modified")
    if not last_modified:
        return True

    remote_time = email.utils.parsedate_to_datetime(last_modified)
    local_time = datetime.fromtimestamp(local_path.stat().st_mtime, tz=UTC)

    return remote_time > local_time


@retry(max_attempts=3, base_delay=5.0, exceptions=(httpx.HTTPError, OSError))
def download_file(url: str, dest: Path) -> Path:
    """Download a file from a URL to a local path."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("downloading", url=url, dest=str(dest))

    with httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as response:
        response.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)

    size_mb = round(dest.stat().st_size / 1e6, 2)
    logger.info("download_complete", dest=str(dest), size_mb=size_mb)
    return dest


def download_dataset(dataset_key: str) -> Path:
    """Download a Cricsheet dataset and extract JSON files.

    Skips download if the remote file hasn't changed since the last
    download (HTTP Last-Modified check). Always extracts if downloaded.

    Args:
        dataset_key: Key from CRICSHEET_DATASETS (e.g. 'ipl', 't20i', 'bbl').

    Returns:
        Path to the directory containing extracted JSON files.
    """
    if dataset_key not in CRICSHEET_DATASETS:
        available = ", ".join(sorted(CRICSHEET_DATASETS.keys()))
        raise ValueError(f"Unknown dataset '{dataset_key}'. Available: {available}")

    ds = CRICSHEET_DATASETS[dataset_key]
    url = ds["url"]

    zip_path = settings.raw_dir / f"{dataset_key}_json.zip"
    extract_dir = settings.raw_dir / dataset_key

    if _is_download_needed(url, zip_path):
        download_file(url, zip_path)
    else:
        logger.info("download_skipped", dataset=dataset_key, reason="remote unchanged")

    logger.info("extracting", zip_path=str(zip_path), extract_dir=str(extract_dir))
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    json_count = len(list(extract_dir.glob("*.json")))
    logger.info("extraction_complete", dataset=dataset_key, json_files=json_count)
    return extract_dir
