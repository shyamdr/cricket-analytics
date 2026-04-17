"""Image serving endpoints for player headshots, team logos, and venue photos."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/v1/images", tags=["images"])

IMAGES_DIR = Path("data/images")

_VALID_CATEGORIES = {"players", "teams", "grounds", "venues"}


@router.get("/{category}/{image_id}.png")
def get_image(category: str, image_id: str):
    """Serve an image by category and ESPN ID.

    Categories: players, teams, grounds, venues.
    """
    if category not in _VALID_CATEGORIES:
        raise HTTPException(status_code=404, detail="Invalid image category")

    # Sanitize: only allow numeric IDs to prevent path traversal
    if not image_id.isdigit():
        raise HTTPException(status_code=400, detail="Invalid image ID")

    path = IMAGES_DIR / category / f"{image_id}.png"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(
        path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400, immutable"},
    )
