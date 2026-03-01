"""Download raw data from Cricsheet.

Supports multiple datasets (IPL, T20I, ODI, Tests, BBL, PSL, etc.)
and delta downloads via Cricsheet's 'recently_added' zips.
"""

import zipfile
from pathlib import Path

import httpx
import structlog

from src.config import CRICSHEET_DATASETS, settings
from src.utils import retry

logger = structlog.get_logger(__name__)


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

    download_file(url, zip_path)

    logger.info("extracting", zip_path=str(zip_path), extract_dir=str(extract_dir))
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    json_count = len(list(extract_dir.glob("*.json")))
    logger.info("extraction_complete", dataset=dataset_key, json_files=json_count)
    return extract_dir


def download_matches() -> Path:
    """Download IPL matches (backward compatible with existing pipeline)."""
    return download_dataset("ipl")
