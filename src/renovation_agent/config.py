from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

VALID_IMAGE_SIZES = ("1K", "2K", "4K")

@dataclass(frozen=True)
class Settings:
    api_key: str
    image_model: str = "gemini-3-pro-image-preview"
    planner_model: str = "gemini-3-flash-preview"
    image_size: str = "2K"
    output_dir: Path = Path("outputs")
