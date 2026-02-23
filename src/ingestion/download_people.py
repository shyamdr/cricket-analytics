"""Download people registry CSV from Cricsheet."""

from pathlib import Path

import structlog

from src.config import settings
from src.ingestion.downloader import download_file

logger = structlog.get_logger(__name__)


def download_people() -> Path:
    """Download the Cricsheet people registry CSV."""
    dest = settings.raw_dir / "people.csv"
    download_file(settings.cricsheet_people_url, dest)
    return dest
