from __future__ import annotations

import io
import math
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_BYTES = 20 * 1024 * 1024
MAX_SIDE = 2048

ASPECT_RATIOS = {
    "1:1": 1.0,
    "2:3": 2 / 3,
    "3:2": 3 / 2,
    "3:4": 3 / 4,
    "4:3": 4 / 3,
    "4:5": 4 / 5,
    "5:4": 5 / 4,
    "9:16": 9 / 16,
    "16:9": 16 / 9,
    "21:9": 21 / 9,
}

class ImageError(ValueError):
    pass

def nearest_aspect_ratio(width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        raise ImageError("Image dimensions must be positive")
    r = width / height
    return min(ASPECT_RATIOS, key=lambda k: abs(math.log(r / ASPECT_RATIOS[k])))
def load_image(path: str | Path, max_side: int = MAX_SIDE) -> Image.Image:
    p = Path(path)
    if not p.is_file():
        raise ImageError(f"File not found: {p}")
    if p.suffix.lower() not in SUPPORTED_EXT:
        raise ImageError(f"Unsupported format {p.suffix!r}. Use one of {sorted(SUPPORTED_EXT)}")
    if p.stat().st_size > MAX_BYTES:
        raise ImageError(f"Image larger than {MAX_BYTES // (1024 * 1024)} MB: {p}")
    try:
        img = Image.open(p)
        img.load()
    except (UnidentifiedImageError, OSError) as e:
        raise ImageError(f"Could not read image {p}: {e}") from e
    img = ImageOps.exif_transpose(img).convert("RGB")
    return img
