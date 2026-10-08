from __future__ import annotations

import io
import math
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_BYTES = 20 * 1024 * 1024
MAX_SIDE = 2048

class ImageError(ValueError):
    pass
